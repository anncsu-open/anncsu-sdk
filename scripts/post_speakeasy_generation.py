#!/usr/bin/env python3
"""Post-Speakeasy generation script.

This script updates the generated SDK code to use the shared infrastructure
in anncsu.common.sdk instead of duplicated code in each API package.

Run this script after each Speakeasy regeneration:
    uv run python scripts/post_speakeasy_generation.py

Or run for a specific API package:
    uv run python scripts/post_speakeasy_generation.py --package pa
"""

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(
    name="post-speakeasy",
    help="Post-Speakeasy generation script for ANNCSU SDK",
    no_args_is_help=False,
)
console = Console()

# Root of the SDK source
SDK_ROOT = Path(__file__).parent.parent / "src" / "anncsu"

# Files to delete from each API package (they exist in common/sdk/)
FILES_TO_DELETE = [
    "_hooks/__init__.py",
    "_hooks/sdkhooks.py",
    "_hooks/types.py",
    "basesdk.py",
    "httpclient.py",
    "types/__init__.py",
    "types/basemodel.py",
    "utils/__init__.py",
    "utils/annotations.py",
    "utils/datetimes.py",
    "utils/dynamic_imports.py",
    "utils/enums.py",
    "utils/eventstreaming.py",
    "utils/forms.py",
    "utils/headers.py",
    "utils/logger.py",
    "utils/metadata.py",
    "utils/queryparams.py",
    "utils/requestbodies.py",
    "utils/retries.py",
    "utils/security.py",
    "utils/serializers.py",
    "utils/unmarshal_json_response.py",
    "utils/url.py",
    "utils/values.py",
]

# Import replacements to apply (order matters - more specific patterns first)
IMPORT_REPLACEMENTS = [
    # Replace relative imports of basesdk
    (r"from \.basesdk import BaseSDK", "from anncsu.common.sdk import BaseSDK"),
    # Replace relative imports of httpclient
    (
        r"from \.httpclient import (.*)",
        r"from anncsu.common.sdk.httpclient import \1",
    ),
    # Replace relative imports of types
    (r"from \.types import (.*)", r"from anncsu.common.sdk.types import \1"),
    (
        r"from \.types\.basemodel import (.*)",
        r"from anncsu.common.sdk.types import \1",
    ),
    # Replace relative imports of utils (both patterns: .utils and .utils.module)
    (r"from \.utils import (.*)", r"from anncsu.common.sdk.utils import \1"),
    (
        r"from \.utils\.(\w+) import (.*)",
        r"from anncsu.common.sdk.utils import \2",
    ),
    # Replace anncsu.pa.utils with anncsu.common.sdk.utils
    (
        r"from anncsu\.pa\.utils import (.*)",
        r"from anncsu.common.sdk.utils import \1",
    ),
    (
        r"from anncsu\.pa\.utils\.(\w+) import (.*)",
        r"from anncsu.common.sdk.utils import \2",
    ),
    (r"from anncsu\.pa import utils", "from anncsu.common.sdk import utils"),
    # Replace anncsu.pa.types with anncsu.common.sdk.types
    (
        r"from anncsu\.pa\.types import (.*)",
        r"from anncsu.common.sdk.types import \1",
    ),
    (r"from anncsu\.pa import types", "from anncsu.common.sdk import types"),
    # Replace anncsu.common.utils with anncsu.common.sdk.utils
    (
        r"from anncsu\.common\.utils import (.*)",
        r"from anncsu.common.sdk.utils import \1",
    ),
    (
        r"from anncsu\.common import utils",
        "from anncsu.common.sdk import utils",
    ),
    # Replace anncsu.common.types with anncsu.common.sdk.types
    (
        r"from anncsu\.common\.types import (.*)",
        r"from anncsu.common.sdk.types import \1",
    ),
    # Replace bare anncsu.types with anncsu.common.sdk.types (for new packages)
    (
        r"from anncsu\.types import (.*)",
        r"from anncsu.common.sdk.types import \1",
    ),
    # Replace bare anncsu.utils with anncsu.common.sdk.utils (for new packages)
    (
        r"from anncsu\.utils import (.*)",
        r"from anncsu.common.sdk.utils import \1",
    ),
    (
        r"from anncsu\.utils\.(\w+) import (.*)",
        r"from anncsu.common.sdk.utils import \2",
    ),
    # Replace anncsu.errors with anncsu.common.errors (for new packages)
    (
        r"from anncsu\.errors import (.*)",
        r"from anncsu.common.errors import \1",
    ),
    # Replace anncsu._hooks with anncsu.common.hooks (for new packages)
    (
        r"from anncsu\._hooks import (.*)",
        r"from anncsu.common.hooks import \1",
    ),
    # Replace "from anncsu import models, utils" with relative imports
    (
        r"from anncsu import models, utils",
        r"from . import models\nfrom anncsu.common.sdk import utils",
    ),
    (
        r"from anncsu import errors, models, utils",
        r"from . import errors, models\nfrom anncsu.common.sdk import utils",
    ),
    # Replace "from anncsu import models" with relative import
    (r"from anncsu import models", r"from . import models"),
    # Replace "from anncsu import errors" with relative import
    (r"from anncsu import errors", r"from . import errors"),
    # Replace internal module imports (e.g., from anncsu.status import Status)
    # These need to become relative imports within the package
    (r"from anncsu\.status import (.*)", r"from .status import \1"),
    (r"from anncsu\.anncsu_2 import (.*)", r"from .anncsu_2 import \1"),
]

# All known API packages
ALL_PACKAGES = ["pa", "coordinate", "accessi", "odonimi"]

# Files that should NOT have their imports modified (except specific patterns)
EXCLUDE_FILES = [
    "_version.py",
]


def delete_duplicated_files(package_path: Path, dry_run: bool = False) -> list[str]:
    """Delete files that are duplicated in common/sdk/."""
    deleted = []
    for file_rel in FILES_TO_DELETE:
        file_path = package_path / file_rel
        if file_path.exists():
            if not dry_run:
                file_path.unlink()
            deleted.append(str(file_rel))
            console.print(f"  [red]Deleted:[/red] {file_rel}")

    # Clean up empty directories
    for dir_name in ["_hooks", "types", "utils"]:
        dir_path = package_path / dir_name
        if dir_path.exists():
            try:
                if not dry_run:
                    # Only remove if empty
                    remaining = list(dir_path.iterdir())
                    if not remaining:
                        dir_path.rmdir()
                        console.print(
                            f"  [red]Removed empty directory:[/red] {dir_name}/"
                        )
            except OSError:
                pass  # Directory not empty

    return deleted


def update_imports_in_file(file_path: Path, dry_run: bool = False) -> bool:
    """Update imports in a single file. Returns True if file was modified."""
    if file_path.name in EXCLUDE_FILES:
        return False

    content = file_path.read_text()
    original_content = content

    for pattern, replacement in IMPORT_REPLACEMENTS:
        content = re.sub(pattern, replacement, content)

    if content != original_content:
        if not dry_run:
            file_path.write_text(content)
        return True

    return False


def update_imports_in_package(package_path: Path, dry_run: bool = False) -> list[str]:
    """Update imports in all Python files in a package."""
    modified = []

    for py_file in package_path.rglob("*.py"):
        # Skip __pycache__ and other non-source directories
        if "__pycache__" in str(py_file):
            continue

        if update_imports_in_file(py_file, dry_run):
            rel_path = py_file.relative_to(package_path)
            modified.append(str(rel_path))
            console.print(f"  [green]Updated imports:[/green] {rel_path}")

    return modified


def fix_model_field_aliases(package_path: Path, dry_run: bool = False) -> list[str]:
    """Fix OAS-vs-real-API field name mismatches in model files.

    The OAS specs define ``denomuff`` but the real API returns ``duf``.
    Additionally, ``cododocomunale`` and ``codacccomunale`` are returned
    by the API but missing from OAS specs.

    This function adds Pydantic aliases and missing fields to survive
    Speakeasy regeneration.  See https://github.com/geobeyond/anncsu-sdk/issues/12
    """
    models_path = package_path / "models"
    if not models_path.exists():
        return []

    fixed: list[str] = []

    for py_file in sorted(models_path.glob("*.py")):
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text()
        original_content = content

        # Skip files that don't contain the denomuff field
        if "denomuff" not in content:
            continue

        # 1. Ensure ``import pydantic`` is present
        if "import pydantic" not in content:
            content = re.sub(
                r"(from typing_extensions import .*)",
                r"\1\nimport pydantic",
                content,
                count=1,
            )

        # 2. Ensure ``Annotated`` is in typing_extensions imports
        if re.search(r"from typing_extensions import (?!.*Annotated)", content):
            content = re.sub(
                r"from typing_extensions import (.*)",
                r"from typing_extensions import Annotated, \1",
                content,
                count=1,
            )

        # 3. Replace ``denomuff: Optional[str] = None`` with aliased version
        content = re.sub(
            r"    denomuff: Optional\[str\] = None",
            '    denomuff: Annotated[Optional[str], pydantic.Field(alias="duf")] = None',
            content,
        )

        # 4. Add ``cododocomunale`` field after ``prognaz`` or before ``dug``
        if "cododocomunale" not in content:
            # TypedDict entry
            if "    prognaz: NotRequired[str]\n    dug:" in content:
                content = content.replace(
                    "    prognaz: NotRequired[str]\n    dug:",
                    "    prognaz: NotRequired[str]\n"
                    "    cododocomunale: NotRequired[str]\n    dug:",
                )
            elif "    dug: NotRequired[str]\n    denomuff:" in content:
                content = content.replace(
                    "    dug: NotRequired[str]\n    denomuff:",
                    "    cododocomunale: NotRequired[str]\n"
                    "    dug: NotRequired[str]\n    denomuff:",
                )

            # BaseModel field
            if "    prognaz: Optional[str] = None\n\n    " in content:
                content = re.sub(
                    r"(    prognaz: Optional\[str\] = None\n)"
                    r"\n(    (?:cododocomunale|dug):)",
                    r"\1\n    cododocomunale: Optional[str] = None\n\n\2",
                    content,
                    count=1,
                )
            else:
                content = re.sub(
                    r"(class \w+Data\(BaseModel\):\n)(    dug:)",
                    r"\1    cododocomunale: Optional[str] = None\n\n\2",
                    content,
                    count=1,
                )

        # 5. Add ``codacccomunale`` after ``prognazacc`` (only prognazacc* files)
        if "codacccomunale" not in content and "prognazacc" in py_file.name:
            # TypedDict
            content = re.sub(
                r"(    prognazacc: NotRequired\[str\]\n)(    civico:)",
                r"\1    codacccomunale: NotRequired[str]\n\2",
                content,
            )
            # BaseModel
            content = re.sub(
                r"(    prognazacc: Optional\[str\] = None\n)"
                r"\n(    civico:)",
                r"\1\n    codacccomunale: Optional[str] = None\n\n\2",
                content,
            )

        if content != original_content:
            if not dry_run:
                py_file.write_text(content)
            rel_path = py_file.relative_to(package_path)
            fixed.append(str(rel_path))
            console.print(f"  [green]Fixed field aliases:[/green] {rel_path}")

    return fixed


# Speakeasy 1.7+ emits ``is_error_status_code=lambda c: utils.match_status_codes(LIST, c)``
# but ``BaseSDK.do_request`` accepts ``error_status_codes=LIST``. See issue #26.
DO_REQUEST_KWARG_PATTERN = re.compile(
    r"is_error_status_code=lambda \w+: utils\.match_status_codes\((\[[^\]]+\]), \w+\)"
)


def fix_do_request_kwarg(package_path: Path, dry_run: bool = False) -> list[str]:
    """Rewrite Speakeasy 1.7+ ``is_error_status_code`` lambda to the
    ``error_status_codes`` list form expected by ``BaseSDK.do_request``."""
    fixed: list[str] = []

    for py_file in package_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text()
        new_content, count = DO_REQUEST_KWARG_PATTERN.subn(
            r"error_status_codes=\1", content
        )

        if count > 0:
            if not dry_run:
                py_file.write_text(new_content)
            rel_path = py_file.relative_to(package_path)
            fixed.append(str(rel_path))
            console.print(
                f"  [green]Fixed do_request kwarg ({count}x):[/green] {rel_path}"
            )

    return fixed


# Speakeasy 1.7+ emits ``from anncsu.common.sdk.utils import unmarshal_json_response``
# but ``unmarshal_json_response`` is a sub-module whose name collides with the
# inner function. Python resolves the import to the module, breaking the call
# with ``TypeError: 'module' object is not callable``. See issue #28.
UNMARSHAL_IMPORT_PATTERN = re.compile(
    r"^from anncsu\.common\.sdk\.utils import unmarshal_json_response$",
    flags=re.MULTILINE,
)
UNMARSHAL_IMPORT_REPLACEMENT = (
    "from anncsu.common.sdk.utils.unmarshal_json_response import "
    "unmarshal_json_response"
)


def fix_unmarshal_import(package_path: Path, dry_run: bool = False) -> list[str]:
    """Rewrite the ambiguous package-level ``unmarshal_json_response`` import
    to the explicit sub-module form used by the pa/coordinate packages."""
    fixed: list[str] = []

    for py_file in package_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        content = py_file.read_text()
        new_content, count = UNMARSHAL_IMPORT_PATTERN.subn(
            UNMARSHAL_IMPORT_REPLACEMENT, content
        )

        if count > 0:
            if not dry_run:
                py_file.write_text(new_content)
            rel_path = py_file.relative_to(package_path)
            fixed.append(str(rel_path))
            console.print(
                f"  [green]Fixed unmarshal_json_response import ({count}x):[/green] {rel_path}"
            )

    return fixed


# Speakeasy 1.7+ omits the ``hooks`` Dependency Injection parameter from the
# generated SDK ``__init__``. Without it, the CLI cannot inject ``ModIHook``
# / ``HooksProvider`` and crashes with ``TypeError: __init__() got an
# unexpected keyword argument 'hooks'``. The accessi/coordinate packages
# were manually patched in their first CLI commit; this transformation
# automates the same fix for every package on every regeneration.
#
# Transformations applied (5 in total, all idempotent):
#   1. import: ``SDKHooks`` → ``HooksProvider, SDKHooks``
#   2. ``__init__`` signature: append ``hooks: Optional[HooksProvider] = None,``
#   3. ``BaseSDK.__init__(..., parent_ref=self,)`` → drop ``parent_ref=self,``
#   4. ``hooks = SDKHooks()`` block → DI pattern (``sdk_hooks``)
#   5. ``klass(self.sdk_configuration, parent_ref=self)`` → drop the kwarg

_HOOKS_IMPORT_BAD = "from anncsu.common.hooks import SDKHooks"
_HOOKS_IMPORT_GOOD = "from anncsu.common.hooks import HooksProvider, SDKHooks"

_HOOKS_INIT_PARAM_PATTERN = re.compile(
    r"(        debug_logger: Optional\[Logger\] = None,\n)(    \) -> None:)"
)
_HOOKS_INIT_PARAM_REPL = r"\1        hooks: Optional[HooksProvider] = None,\n\2"

_BASE_SDK_PARENT_REF_PATTERN = re.compile(
    r"(            \),\n)            parent_ref=self,\n(        \))"
)
_BASE_SDK_PARENT_REF_REPL = r"\1\2"

_HOOKS_BLOCK_BAD = (
    "        hooks = SDKHooks()\n"
    "\n"
    "        # pylint: disable=protected-access\n"
    '        self.sdk_configuration.__dict__["_hooks"] = hooks\n'
    "\n"
    "        self.sdk_configuration = hooks.sdk_init(self.sdk_configuration)"
)
_HOOKS_BLOCK_GOOD = (
    "        # Use injected hooks or create new ones (dependency injection pattern).\n"
    "        sdk_hooks = hooks if hooks is not None else SDKHooks()\n"
    "\n"
    "        # pylint: disable=protected-access\n"
    '        self.sdk_configuration.__dict__["_hooks"] = sdk_hooks\n'
    "\n"
    "        self.sdk_configuration = sdk_hooks.sdk_init(self.sdk_configuration)"
)

_GETATTR_PARENT_REF_BAD = "klass(self.sdk_configuration, parent_ref=self)"
_GETATTR_PARENT_REF_GOOD = "klass(self.sdk_configuration)"


def fix_hooks_di(package_path: Path, dry_run: bool = False) -> list[str]:
    """Rewrite Speakeasy 1.7+ ``__init__`` to support ``hooks`` DI parameter.

    Applies five idempotent transformations to ``sdk.py`` files. A file
    is considered "fixed" if any of the five produced a change. Re-running
    on an already-patched file yields zero changes.
    """
    fixed: list[str] = []

    for py_file in package_path.rglob("sdk.py"):
        if "__pycache__" in str(py_file):
            continue

        original = py_file.read_text()
        content = original
        changes = 0

        # 1. Import HooksProvider alongside SDKHooks (skip if already present)
        if "HooksProvider" not in content and _HOOKS_IMPORT_BAD in content:
            content = content.replace(_HOOKS_IMPORT_BAD, _HOOKS_IMPORT_GOOD, 1)
            changes += 1

        # 2. Append ``hooks`` param to __init__ signature
        if "hooks: Optional[HooksProvider]" not in content:
            new_content, n = _HOOKS_INIT_PARAM_PATTERN.subn(
                _HOOKS_INIT_PARAM_REPL, content
            )
            if n:
                content = new_content
                changes += n

        # 3. Drop ``parent_ref=self,`` from BaseSDK.__init__
        new_content, n = _BASE_SDK_PARENT_REF_PATTERN.subn(
            _BASE_SDK_PARENT_REF_REPL, content
        )
        if n:
            content = new_content
            changes += n

        # 4. Rewrite the unconditional ``hooks = SDKHooks()`` block to the DI pattern
        if (
            _HOOKS_BLOCK_BAD in content
            and "sdk_hooks = hooks if hooks is not None" not in content
        ):
            content = content.replace(_HOOKS_BLOCK_BAD, _HOOKS_BLOCK_GOOD, 1)
            changes += 1

        # 5. Drop ``parent_ref=self`` from __getattr__'s klass(...) call
        if _GETATTR_PARENT_REF_BAD in content:
            content = content.replace(_GETATTR_PARENT_REF_BAD, _GETATTR_PARENT_REF_GOOD)
            changes += 1

        if changes > 0 and content != original:
            if not dry_run:
                py_file.write_text(content)
            rel_path = py_file.relative_to(package_path)
            fixed.append(str(rel_path))
            console.print(
                f"  [green]Fixed hooks DI ({changes} edits):[/green] {rel_path}"
            )

    return fixed


def process_package(
    package_name: str, dry_run: bool = False
) -> tuple[int, int, int, int, int, int]:
    """Process a single API package.

    Returns (deleted, modified, fixed, do_request_fixed, unmarshal_fixed,
    hooks_di_fixed).
    """
    package_path = SDK_ROOT / package_name

    if not package_path.exists():
        console.print(f"[red]Package not found:[/red] {package_path}")
        raise typer.Exit(code=1)

    console.print(f"\n[bold blue]Processing package:[/bold blue] {package_name}")
    console.print("-" * 40)

    # Step 1: Delete duplicated files
    console.print("\n[bold]1. Deleting duplicated files...[/bold]")
    deleted = delete_duplicated_files(package_path, dry_run)
    if not deleted:
        console.print("  [dim]No files to delete[/dim]")

    # Step 2: Update imports in remaining files
    console.print("\n[bold]2. Updating imports...[/bold]")
    modified = update_imports_in_package(package_path, dry_run)
    if not modified:
        console.print("  [dim]No imports to update[/dim]")

    # Step 3: Fix model field aliases (Issue #12)
    console.print("\n[bold]3. Fixing model field aliases (Issue #12)...[/bold]")
    fixed = fix_model_field_aliases(package_path, dry_run)
    if not fixed:
        console.print("  [dim]No field aliases to fix[/dim]")

    # Step 4: Fix do_request kwarg (Issue #26)
    console.print("\n[bold]4. Fixing do_request kwarg (Issue #26)...[/bold]")
    do_request_fixed = fix_do_request_kwarg(package_path, dry_run)
    if not do_request_fixed:
        console.print("  [dim]No do_request kwargs to fix[/dim]")

    # Step 5: Fix unmarshal_json_response import (Issue #28)
    console.print(
        "\n[bold]5. Fixing unmarshal_json_response import (Issue #28)...[/bold]"
    )
    unmarshal_fixed = fix_unmarshal_import(package_path, dry_run)
    if not unmarshal_fixed:
        console.print("  [dim]No unmarshal_json_response imports to fix[/dim]")

    # Step 6: Fix hooks DI parameter in sdk.py (Speakeasy 1.7+ regression)
    console.print("\n[bold]6. Fixing hooks DI parameter in sdk.py...[/bold]")
    hooks_di_fixed = fix_hooks_di(package_path, dry_run)
    if not hooks_di_fixed:
        console.print("  [dim]No hooks DI fixes needed[/dim]")

    return (
        len(deleted),
        len(modified),
        len(fixed),
        len(do_request_fixed),
        len(unmarshal_fixed),
        len(hooks_di_fixed),
    )


@app.command()
def main(
    package: Annotated[
        str,
        typer.Option(
            "--package",
            "-p",
            help="API package to process",
        ),
    ] = "pa",
    all_packages: Annotated[
        bool,
        typer.Option(
            "--all",
            "-a",
            help="Process all API packages",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "-n",
            help="Show what would be done without making changes",
        ),
    ] = False,
) -> None:
    """Update generated SDK code to use shared infrastructure in common/sdk/.

    Run this script after each Speakeasy regeneration to:

    1. Delete duplicated files (basesdk.py, httpclient.py, utils/, types/)

    2. Update imports to use anncsu.common.sdk instead of local copies

    3. Fix model field aliases (denomuff -> duf, add cododocomunale/codacccomunale)
    """
    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")

    total_deleted = 0
    total_modified = 0
    total_fixed = 0
    total_do_request_fixed = 0
    total_unmarshal_fixed = 0
    total_hooks_di_fixed = 0

    if all_packages:
        # Process all known API packages
        for pkg in ALL_PACKAGES:
            (
                deleted,
                modified,
                fixed,
                do_request_fixed,
                unmarshal_fixed,
                hooks_di_fixed,
            ) = process_package(pkg, dry_run)
            total_deleted += deleted
            total_modified += modified
            total_fixed += fixed
            total_do_request_fixed += do_request_fixed
            total_unmarshal_fixed += unmarshal_fixed
            total_hooks_di_fixed += hooks_di_fixed
    else:
        (
            deleted,
            modified,
            fixed,
            do_request_fixed,
            unmarshal_fixed,
            hooks_di_fixed,
        ) = process_package(package, dry_run)
        total_deleted = deleted
        total_modified = modified
        total_fixed = fixed
        total_do_request_fixed = do_request_fixed
        total_unmarshal_fixed = unmarshal_fixed
        total_hooks_di_fixed = hooks_di_fixed

    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold green]Post-generation processing complete![/bold green]")
    console.print(f"\n  Files deleted:       {total_deleted}")
    console.print(f"  Files modified:      {total_modified}")
    console.print(f"  Fields fixed:        {total_fixed}")
    console.print(f"  do_request fixed:    {total_do_request_fixed}")
    console.print(f"  unmarshal fixed:     {total_unmarshal_fixed}")
    console.print(f"  hooks DI fixed:      {total_hooks_di_fixed}")

    if dry_run:
        console.print(
            "\n[yellow]This was a dry run. Run without --dry-run to apply changes.[/yellow]"
        )
    else:
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run tests: [cyan]uv run pytest tests/[/cyan]")
        console.print("  2. If tests pass, commit the changes")


if __name__ == "__main__":
    app()
