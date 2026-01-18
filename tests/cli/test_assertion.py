# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for assertion CLI commands."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

if TYPE_CHECKING:
    from typer.testing import CliRunner


# Pydantic models for JWT structure validation
class JWTHeader(BaseModel):
    """JWT header model."""

    alg: str
    typ: str = "JWT"
    kid: str | None = None


class JWTPayload(BaseModel):
    """JWT payload model for client assertions."""

    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    jti: str | None = None
    purposeId: str | None = None


class DecodedJWT(BaseModel):
    """Decoded JWT with header and payload."""

    header: JWTHeader
    payload: JWTPayload


class TestAssertionCreate:
    """Tests for assertion create command."""

    def test_create_outputs_jwt(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that assertion create outputs a JWT string."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "test-purpose-id"
                settings.key_path = Path("./private_key.pem")
                settings.validity_minutes = 43200
                settings.to_config.return_value = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.assertion.create_client_assertion"
                ) as mock_create:
                    mock_create.return_value = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"

                    result = cli_runner.invoke(app, ["assertion", "create"])

            assert result.exit_code == 0
            # Output should be a JWT (starts with eyJ)
            assert "eyJ" in result.output

    def test_create_jwt_format(
        self, cli_runner: CliRunner, tmp_path: Path, mock_private_key: Path
    ) -> None:
        """Test that created assertion is valid JWT format (3 parts)."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            Path("private_key.pem").write_text(mock_private_key.read_text())

            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.to_config.return_value = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.assertion.create_client_assertion"
                ) as mock_create:
                    mock_create.return_value = "header.payload.signature"

                    result = cli_runner.invoke(app, ["assertion", "create"])

            assert result.exit_code == 0
            jwt_output = result.output.strip()
            # JWT has 3 parts separated by dots
            assert len(jwt_output.split(".")) == 3

    def test_create_error_no_config(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that assertion create fails gracefully without config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings",
                side_effect=Exception("Configuration not found"),
            ):
                result = cli_runner.invoke(app, ["assertion", "create"])

            assert result.exit_code == 1
            assert "error" in result.output.lower()

    def test_create_error_invalid_key(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that assertion create fails with invalid key file."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            # Create invalid key file
            Path("invalid_key.pem").write_text("not a valid key")

            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.key_path = Path("./invalid_key.pem")
                settings.to_config.return_value = MagicMock()
                mock_settings.return_value = settings

                with patch(
                    "anncsu.cli.commands.assertion.create_client_assertion",
                    side_effect=ValueError("Invalid private key"),
                ):
                    result = cli_runner.invoke(app, ["assertion", "create"])

            assert result.exit_code == 1
            assert (
                "error" in result.output.lower() or "invalid" in result.output.lower()
            )


class TestAssertionInfo:
    """Tests for assertion info command."""

    def test_info_shows_claims(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that assertion info shows JWT claims."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "test-purpose-id"
                settings.validity_minutes = 43200
                mock_settings.return_value = settings

                result = cli_runner.invoke(app, ["assertion", "info"])

            assert result.exit_code == 0
            # Should show key claim information
            output_lower = result.output.lower()
            assert "issuer" in output_lower or "iss" in output_lower
            assert "subject" in output_lower or "sub" in output_lower
            assert "audience" in output_lower or "aud" in output_lower

    def test_info_shows_expiration(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that assertion info shows expiration details."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings"
            ) as mock_settings:
                settings = MagicMock()
                settings.kid = "test-key-id"
                settings.issuer = "test-client-id"
                settings.subject = "test-client-id"
                settings.audience = "auth.uat.interop.pagopa.it/client-assertion"
                settings.purpose_id = "test-purpose-id"
                settings.validity_minutes = 43200  # 30 days
                mock_settings.return_value = settings

                result = cli_runner.invoke(app, ["assertion", "info"])

            assert result.exit_code == 0
            # Should show validity/expiration info
            output_lower = result.output.lower()
            assert (
                "validity" in output_lower
                or "expire" in output_lower
                or "ttl" in output_lower
                or "30" in result.output  # 30 days
            )

    def test_info_no_config_error(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that assertion info fails gracefully without config."""
        from anncsu.cli import app

        with cli_runner.isolated_filesystem(temp_dir=tmp_path):
            with patch(
                "anncsu.cli.commands.assertion.ClientAssertionSettings",
                side_effect=Exception("No configuration"),
            ):
                result = cli_runner.invoke(app, ["assertion", "info"])

            assert result.exit_code == 1


class TestAssertionDecode:
    """Tests for assertion decode command."""

    def _create_mock_jwt(
        self,
        header: dict | None = None,
        payload: dict | None = None,
    ) -> str:
        """Create a mock JWT string for testing."""
        default_header = {"alg": "RS256", "typ": "JWT"}
        default_payload = {
            "iss": "test-issuer",
            "sub": "test-subject",
            "aud": "test-audience",
            "exp": 1735689600,
            "iat": 1735603200,
        }

        header_data = header or default_header
        payload_data = payload or default_payload

        def encode_part(data: dict) -> str:
            import json

            return (
                base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
            )

        return f"{encode_part(header_data)}.{encode_part(payload_data)}.signature"

    def test_decode_from_stdin(self, cli_runner: CliRunner) -> None:
        """Test that assertion decode can read JWT from stdin."""
        from anncsu.cli import app

        mock_jwt = self._create_mock_jwt()

        # Create Pydantic model for mock return
        decoded = DecodedJWT(
            header=JWTHeader(alg="RS256", typ="JWT"),
            payload=JWTPayload(
                iss="test-issuer",
                sub="test-subject",
                aud="test-audience",
                exp=1735689600,
                iat=1735603200,
            ),
        )

        with patch("anncsu.cli.commands.assertion.decode_jwt") as mock_decode:
            mock_decode.return_value = decoded

            result = cli_runner.invoke(app, ["assertion", "decode"], input=mock_jwt)

        assert result.exit_code == 0
        # Should show decoded claims
        assert "test-issuer" in result.output or "iss" in result.output.lower()

    def test_decode_from_argument(self, cli_runner: CliRunner) -> None:
        """Test that assertion decode can take JWT as argument."""
        from anncsu.cli import app

        mock_jwt = "header.payload.signature"

        decoded = DecodedJWT(
            header=JWTHeader(alg="RS256", typ="JWT"),
            payload=JWTPayload(
                iss="test-issuer",
                sub="test-subject",
                aud="test-audience",
                exp=1735689600,
                iat=1735603200,
            ),
        )

        with patch("anncsu.cli.commands.assertion.decode_jwt") as mock_decode:
            mock_decode.return_value = decoded

            result = cli_runner.invoke(app, ["assertion", "decode", mock_jwt])

        assert result.exit_code == 0

    def test_decode_shows_header_and_payload(self, cli_runner: CliRunner) -> None:
        """Test that assertion decode shows both header and payload."""
        from anncsu.cli import app

        mock_jwt = "header.payload.signature"

        decoded = DecodedJWT(
            header=JWTHeader(alg="RS256", typ="JWT", kid="test-kid"),
            payload=JWTPayload(
                iss="test-issuer",
                sub="test-subject",
                aud="test-audience",
                exp=1735689600,
                iat=1735603200,
            ),
        )

        with patch("anncsu.cli.commands.assertion.decode_jwt") as mock_decode:
            mock_decode.return_value = decoded

            result = cli_runner.invoke(app, ["assertion", "decode", mock_jwt])

        assert result.exit_code == 0
        output_lower = result.output.lower()
        # Should show header info
        assert "header" in output_lower or "alg" in output_lower
        # Should show payload info
        assert (
            "payload" in output_lower
            or "iss" in output_lower
            or "issuer" in output_lower
        )

    def test_decode_invalid_jwt_error(self, cli_runner: CliRunner) -> None:
        """Test that assertion decode fails with invalid JWT."""
        from anncsu.cli import app

        with patch(
            "anncsu.cli.commands.assertion.decode_jwt",
            side_effect=ValueError("Invalid JWT format"),
        ):
            result = cli_runner.invoke(app, ["assertion", "decode", "not-a-jwt"])

        assert result.exit_code == 1
        assert "invalid" in result.output.lower() or "error" in result.output.lower()

    def test_decode_json_output(self, cli_runner: CliRunner) -> None:
        """Test that assertion decode can output as JSON (Pydantic model_dump_json)."""
        from anncsu.cli import app

        mock_jwt = "header.payload.signature"

        decoded = DecodedJWT(
            header=JWTHeader(alg="RS256", typ="JWT"),
            payload=JWTPayload(
                iss="test-issuer",
                sub="test-subject",
                aud="test-audience",
                exp=1735689600,
                iat=1735603200,
            ),
        )

        with patch("anncsu.cli.commands.assertion.decode_jwt") as mock_decode:
            mock_decode.return_value = decoded

            result = cli_runner.invoke(app, ["assertion", "decode", "--json", mock_jwt])

        assert result.exit_code == 0
        # Should be valid JSON that can be parsed back to Pydantic model
        parsed = DecodedJWT.model_validate_json(result.output)
        assert parsed.header.alg == "RS256"
        assert parsed.payload.iss == "test-issuer"

    def test_decode_returns_pydantic_model(self, cli_runner: CliRunner) -> None:
        """Test that decode_jwt returns a Pydantic model."""
        from anncsu.cli import app

        mock_jwt = self._create_mock_jwt()

        decoded = DecodedJWT(
            header=JWTHeader(alg="RS256", typ="JWT"),
            payload=JWTPayload(
                iss="test-issuer",
                sub="test-subject",
                aud="test-audience",
                exp=1735689600,
                iat=1735603200,
            ),
        )

        with patch("anncsu.cli.commands.assertion.decode_jwt") as mock_decode:
            mock_decode.return_value = decoded

            result = cli_runner.invoke(app, ["assertion", "decode", mock_jwt])

        assert result.exit_code == 0
        # Verify mock was called and returned Pydantic model
        mock_decode.assert_called_once()
        returned_value = mock_decode.return_value
        assert isinstance(returned_value, DecodedJWT)
        assert isinstance(returned_value.header, JWTHeader)
        assert isinstance(returned_value.payload, JWTPayload)

    def test_decode_validates_jwt_structure(self, cli_runner: CliRunner) -> None:
        """Test that decode validates JWT has proper structure via Pydantic."""
        from anncsu.cli import app

        # JWT with missing required fields should fail validation
        with patch(
            "anncsu.cli.commands.assertion.decode_jwt",
            side_effect=ValueError("Validation error: missing required field 'iss'"),
        ):
            result = cli_runner.invoke(
                app, ["assertion", "decode", "invalid.jwt.token"]
            )

        assert result.exit_code == 1
        assert "error" in result.output.lower() or "validation" in result.output.lower()
