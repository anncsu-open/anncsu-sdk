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
