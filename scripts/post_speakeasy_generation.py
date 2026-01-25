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
    "basesdk.py",
    "httpclient.py",
    "types/__init__.py",
    "types/basemodel.py",
    "utils/__init__.py",
    "utils/annotations.py",
    "utils/datetimes.py",
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
ALL_PACKAGES = ["pa", "coordinate"]

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
    for dir_name in ["types", "utils"]:
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


def process_package(package_name: str, dry_run: bool = False) -> tuple[int, int]:
    """Process a single API package. Returns (deleted_count, modified_count)."""
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

    return len(deleted), len(modified)


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
    """
    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]\n")

    total_deleted = 0
    total_modified = 0

    if all_packages:
        # Process all known API packages
        for pkg in ALL_PACKAGES:
            deleted, modified = process_package(pkg, dry_run)
            total_deleted += deleted
            total_modified += modified
    else:
        deleted, modified = process_package(package, dry_run)
        total_deleted = deleted
        total_modified = modified

    # Summary
    console.print("\n" + "=" * 50)
    console.print("[bold green]Post-generation processing complete![/bold green]")
    console.print(f"\n  Files deleted:  {total_deleted}")
    console.print(f"  Files modified: {total_modified}")

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
