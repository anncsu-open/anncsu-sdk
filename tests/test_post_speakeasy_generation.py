"""Tests for scripts/post_speakeasy_generation.py.

Targeted coverage for transformations that fix Speakeasy 1.7+ output
discrepancies. Currently exercises ``fix_do_request_kwarg`` (issue #26):
the generator emits ``is_error_status_code=lambda c: utils.match_status_codes(
LIST, c)`` but the base SDK expects ``error_status_codes=LIST``. This
test guarantees the post-generation script rewrites the call so the fix
survives every regeneration.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "post_speakeasy_generation.py"


@pytest.fixture(scope="module")
def post_gen_module():
    spec = importlib.util.spec_from_file_location(
        "post_speakeasy_generation", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["post_speakeasy_generation"] = module
    spec.loader.exec_module(module)
    return module


SPEAKEASY_17_BAD_CALL = """\
        http_res = self.do_request(
            hook_ctx=HookContext(
                config=self.sdk_configuration,
                base_url=base_url or "",
                operation_id="example",
                oauth2_scopes=None,
                security_source=None,
            ),
            request=req,
            is_error_status_code=lambda c: utils.match_status_codes(["4XX", "5XX"], c),
            retry_config=retry_config,
        )
"""

EXPECTED_FIXED_CALL = """\
        http_res = self.do_request(
            hook_ctx=HookContext(
                config=self.sdk_configuration,
                base_url=base_url or "",
                operation_id="example",
                oauth2_scopes=None,
                security_source=None,
            ),
            request=req,
            error_status_codes=["4XX", "5XX"],
            retry_config=retry_config,
        )
"""


class TestFixDoRequestKwarg:
    """Issue #26: ``is_error_status_code=lambda ...`` must be rewritten
    to ``error_status_codes=LIST`` so generated calls match the real
    ``BaseSDK.do_request`` signature."""

    def test_rewrites_4xx_5xx_pattern(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "accessi.py"
        target.write_text(SPEAKEASY_17_BAD_CALL)

        fixed = post_gen_module.fix_do_request_kwarg(pkg_dir, dry_run=False)

        assert "accessi.py" in fixed
        assert target.read_text() == EXPECTED_FIXED_CALL

    def test_rewrites_multiple_occurrences_in_same_file(
        self, post_gen_module, tmp_path
    ):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "accessi.py"
        target.write_text(SPEAKEASY_17_BAD_CALL + "\n\n" + SPEAKEASY_17_BAD_CALL)

        post_gen_module.fix_do_request_kwarg(pkg_dir, dry_run=False)

        content = target.read_text()
        assert "is_error_status_code" not in content
        assert content.count('error_status_codes=["4XX", "5XX"]') == 2

    def test_dry_run_does_not_modify_file(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "accessi.py"
        target.write_text(SPEAKEASY_17_BAD_CALL)

        post_gen_module.fix_do_request_kwarg(pkg_dir, dry_run=True)

        assert target.read_text() == SPEAKEASY_17_BAD_CALL

    def test_no_match_returns_empty_list(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "models.py"
        target.write_text("class Foo:\n    pass\n")

        fixed = post_gen_module.fix_do_request_kwarg(pkg_dir, dry_run=False)

        assert fixed == []

    def test_preserves_other_status_code_lists(self, post_gen_module, tmp_path):
        """Speakeasy may emit different code lists (e.g. ["400", "5XX"]).
        The regex must capture the full list verbatim."""
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "endpoint.py"
        target.write_text(
            '            is_error_status_code=lambda c: utils.match_status_codes(["400", "5XX"], c),\n'
        )

        post_gen_module.fix_do_request_kwarg(pkg_dir, dry_run=False)

        assert target.read_text() == '            error_status_codes=["400", "5XX"],\n'


BAD_UNMARSHAL_IMPORT = "from anncsu.common.sdk.utils import unmarshal_json_response\n"
GOOD_UNMARSHAL_IMPORT = (
    "from anncsu.common.sdk.utils.unmarshal_json_response import "
    "unmarshal_json_response\n"
)


class TestFixUnmarshalImport:
    """Issue #28: ``from anncsu.common.sdk.utils import unmarshal_json_response``
    resolves to the sub-module, not the function. The post-gen script must
    rewrite it to the explicit ``from utils.unmarshal_json_response import
    unmarshal_json_response`` form used by the pa/coordinate packages."""

    def test_rewrites_unmarshal_import(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "endpoint.py"
        target.write_text(BAD_UNMARSHAL_IMPORT)

        fixed = post_gen_module.fix_unmarshal_import(pkg_dir, dry_run=False)

        assert "endpoint.py" in fixed
        assert target.read_text() == GOOD_UNMARSHAL_IMPORT

    def test_leaves_already_correct_import_unchanged(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "endpoint.py"
        target.write_text(GOOD_UNMARSHAL_IMPORT)

        fixed = post_gen_module.fix_unmarshal_import(pkg_dir, dry_run=False)

        assert fixed == []
        assert target.read_text() == GOOD_UNMARSHAL_IMPORT

    def test_dry_run_does_not_modify_file(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "endpoint.py"
        target.write_text(BAD_UNMARSHAL_IMPORT)

        post_gen_module.fix_unmarshal_import(pkg_dir, dry_run=True)

        assert target.read_text() == BAD_UNMARSHAL_IMPORT

    def test_no_match_returns_empty_list(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "models.py"
        target.write_text("class Foo:\n    pass\n")

        fixed = post_gen_module.fix_unmarshal_import(pkg_dir, dry_run=False)

        assert fixed == []


class TestUnmarshalImportResolvesToFunction:
    """Integration check: after the fix is applied to the accessi package,
    the imported ``unmarshal_json_response`` must be a callable (function),
    not a module. This catches the runtime symptom directly."""

    def test_accessi_unmarshal_is_callable(self):
        import importlib

        mod = importlib.import_module("anncsu.accessi.accessi")
        assert callable(mod.unmarshal_json_response), (
            "anncsu.accessi.accessi.unmarshal_json_response must be a "
            "function, not a module — see issue #28."
        )

    def test_status_unmarshal_is_callable(self):
        import importlib

        mod = importlib.import_module("anncsu.accessi.status")
        assert callable(mod.unmarshal_json_response), (
            "anncsu.accessi.status.unmarshal_json_response must be a "
            "function, not a module — see issue #28."
        )


# Speakeasy 1.7+ omits the ``hooks`` Dependency Injection parameter from the
# generated SDK ``__init__``. This blocks users from injecting custom hooks
# (e.g. ModI signing) — the CLI ends up doing ``AnncsuOdonimi(hooks=...)``
# and crashes with ``TypeError: unexpected keyword argument 'hooks'``.
#
# The accessi/coordinate packages were fixed manually in their first commit;
# odonimi was missed and only surfaced at runtime (status command). The fix
# in the post-gen script automates the transformation so it survives every
# regeneration.

_SPEAKEASY_17_HOOKS_BAD = """\
from anncsu.common.sdk import BaseSDK
from anncsu.common.hooks import SDKHooks
from typing import Callable, Dict, Optional, TYPE_CHECKING, Union, cast


class AnncsuExample(BaseSDK):
    def __init__(
        self,
        security: Optional[str] = None,
        debug_logger: Optional[Logger] = None,
    ) -> None:
        BaseSDK.__init__(
            self,
            SDKConfiguration(
                client=client,
                debug_logger=debug_logger,
            ),
            parent_ref=self,
        )

        hooks = SDKHooks()

        # pylint: disable=protected-access
        self.sdk_configuration.__dict__["_hooks"] = hooks

        self.sdk_configuration = hooks.sdk_init(self.sdk_configuration)

    def __getattr__(self, name: str):
        if name in self._sub_sdk_map:
            module_path, class_name = self._sub_sdk_map[name]
            module = self.dynamic_import(module_path)
            klass = getattr(module, class_name)
            instance = klass(self.sdk_configuration, parent_ref=self)
            return instance
"""


class TestFixHooksDi:
    """Speakeasy 1.7+ regression: ``__init__`` omits the ``hooks`` DI param.

    The post-gen script must rewrite the file so users can pass a custom
    ``HooksProvider`` (e.g. one with ``ModIPreRequestHook`` registered).
    """

    def test_adds_hooks_provider_import(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        fixed = post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)

        assert "sdk.py" in fixed
        content = target.read_text()
        assert "from anncsu.common.hooks import HooksProvider, SDKHooks" in content

    def test_adds_hooks_init_param(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)

        content = target.read_text()
        assert "hooks: Optional[HooksProvider] = None," in content

    def test_removes_parent_ref_from_base_sdk_init(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)

        content = target.read_text()
        # The parent_ref=self,\n        ) pattern at end of BaseSDK.__init__
        # must be removed (the closing `)` becomes the line after debug_logger).
        assert "parent_ref=self,\n        )" not in content

    def test_rewrites_hooks_block_to_di_pattern(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)

        content = target.read_text()
        # New DI line replaces the unconditional ``hooks = SDKHooks()``.
        assert "sdk_hooks = hooks if hooks is not None else SDKHooks()" in content
        # And the dict assignment uses the new name.
        assert 'self.sdk_configuration.__dict__["_hooks"] = sdk_hooks' in content
        assert (
            "self.sdk_configuration = sdk_hooks.sdk_init(self.sdk_configuration)"
            in content
        )

    def test_removes_parent_ref_from_getattr(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)

        content = target.read_text()
        assert "klass(self.sdk_configuration, parent_ref=self)" not in content
        assert "klass(self.sdk_configuration)" in content

    def test_idempotent_on_already_fixed_file(self, post_gen_module, tmp_path):
        """Running on a file that already matches the target produces no changes."""
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        # First pass: fixes the file.
        first = post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)
        assert "sdk.py" in first
        fixed_content = target.read_text()

        # Second pass: no changes.
        second = post_gen_module.fix_hooks_di(pkg_dir, dry_run=False)
        assert second == []
        assert target.read_text() == fixed_content

    def test_dry_run_does_not_modify_file(self, post_gen_module, tmp_path):
        pkg_dir = tmp_path / "fake_pkg"
        pkg_dir.mkdir()
        target = pkg_dir / "sdk.py"
        target.write_text(_SPEAKEASY_17_HOOKS_BAD)

        post_gen_module.fix_hooks_di(pkg_dir, dry_run=True)

        assert target.read_text() == _SPEAKEASY_17_HOOKS_BAD


class TestAnncsuOdonimiAcceptsHooksParam:
    """Integration check: the generated ``AnncsuOdonimi.__init__`` must accept
    a ``hooks`` keyword argument so the CLI dependency-injection pattern
    works. Mirrors the issue surfaced by ``anncsu odonimo status``."""

    def test_anncsu_odonimi_accepts_hooks_kwarg(self):
        import inspect

        from anncsu.odonimi import AnncsuOdonimi

        sig = inspect.signature(AnncsuOdonimi.__init__)
        assert "hooks" in sig.parameters, (
            "AnncsuOdonimi.__init__ must accept a ``hooks`` parameter for "
            "dependency injection of HooksProvider (e.g. ModIPreRequestHook)."
        )

    def test_anncsu_accessi_accepts_hooks_kwarg(self):
        """Regression: ensure the existing fix in Accessi stays in place."""
        import inspect

        from anncsu.accessi import AnncsuAccessi

        sig = inspect.signature(AnncsuAccessi.__init__)
        assert "hooks" in sig.parameters
