# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""ANNCSU Command Line Interface.

This module provides the CLI entry point for managing PDND authentication
and interacting with ANNCSU APIs.

Usage:
    anncsu --help
    anncsu auth login
    anncsu config show
    anncsu assertion create
"""

from anncsu.cli.app import app

__all__ = ["app"]
