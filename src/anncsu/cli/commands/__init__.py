# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""CLI command groups."""

from anncsu.cli.commands.assertion import assertion_app
from anncsu.cli.commands.auth import auth_app
from anncsu.cli.commands.config import config_app
from anncsu.cli.commands.coordinate import coordinate_app
from anncsu.cli.commands.pa import pa_app

__all__ = ["auth_app", "config_app", "assertion_app", "coordinate_app", "pa_app"]
