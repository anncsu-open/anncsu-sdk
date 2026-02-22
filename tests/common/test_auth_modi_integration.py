# SPDX-FileCopyrightText: 2025-present Geobeyond <info@geobeyond.it>
# SPDX-License-Identifier: MIT
"""Tests for PDNDAuthManager integration with ModI headers."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    pass


class TestPDNDAuthManagerModIIntegration:
    """Tests for PDNDAuthManager ModI header generation."""

    @pytest.fixture
    def mock_env_with_modi(self, mock_private_key: Path) -> dict[str, str]:
        """Create environment variables with ModI audit context."""
        return {
            "PDND_KID": "test-key-id",
            "PDND_ISSUER": "test-client-id",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.uat.interop.pagopa.it/client-assertion",
            "PDND_KEY_PATH": str(mock_private_key),
            "PDND_PURPOSE_ID_PA": "pa-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE": "coordinate-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "coordinate-bulk-purpose-id",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
            # ModI audit context
            "PDND_MODI_USER_ID": "test-batch-user",
            "PDND_MODI_USER_LOCATION": "test-server-01",
            "PDND_MODI_LOA": "SPID_L2",
        }

    @pytest.fixture
    def mock_env_without_modi(self, mock_private_key: Path) -> dict[str, str]:
        """Create environment variables without ModI audit context."""
        return {
            "PDND_KID": "test-key-id",
            "PDND_ISSUER": "test-client-id",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.uat.interop.pagopa.it/client-assertion",
            "PDND_KEY_PATH": str(mock_private_key),
            "PDND_PURPOSE_ID_PA": "pa-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE": "coordinate-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "coordinate-bulk-purpose-id",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
            # No ModI audit context
        }

    def test_get_modi_headers_returns_digest_header(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that get_modi_headers includes HTTP Digest header."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            assert "Digest" in headers
            assert headers["Digest"].startswith("SHA-256=")

    def test_get_modi_headers_returns_signature_jwt(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that get_modi_headers includes Agid-JWT-Signature header."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            assert "Agid-JWT-Signature" in headers
            # JWT has 3 parts separated by dots
            assert headers["Agid-JWT-Signature"].count(".") == 2

    def test_get_modi_headers_returns_tracking_jwt(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that get_modi_headers includes Agid-JWT-TrackingEvidence header."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            assert "Agid-JWT-TrackingEvidence" in headers
            assert headers["Agid-JWT-TrackingEvidence"].count(".") == 2

    def test_get_modi_headers_digest_matches_jwt_signed_headers(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Digest header matches the digest in JWT signed_headers."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Get HTTP Digest header value
            http_digest = headers["Digest"]

            # Extract digest from JWT signed_headers
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            jwt_digest = claims["signed_headers"][0]["digest"]

            # Both should be identical
            assert http_digest == jwt_digest

    def test_get_modi_headers_signature_jwt_has_required_claims(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Signature JWT has all required ModI claims."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode JWT claims
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            # Required claims per ModI INTEGRITY_REST_02
            assert "iss" in claims
            assert "aud" in claims
            assert "iat" in claims
            assert "nbf" in claims  # Not before
            assert "exp" in claims
            assert "jti" in claims  # Unique ID
            assert "signed_headers" in claims

            # Verify signed_headers structure
            signed_headers = claims["signed_headers"]
            assert len(signed_headers) >= 2
            assert "digest" in signed_headers[0]
            assert "content-type" in signed_headers[1]

    def test_get_modi_headers_tracking_jwt_has_required_claims(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Tracking JWT has all required ModI AUDIT_REST_02 claims."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode JWT claims
            track_jwt = headers["Agid-JWT-TrackingEvidence"]
            parts = track_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            # Required claims per ModI AUDIT_REST_02
            assert "iss" in claims
            assert "aud" in claims
            assert "iat" in claims
            assert "nbf" in claims
            assert "exp" in claims
            assert "jti" in claims
            assert "userID" in claims
            assert "userLocation" in claims
            assert "LoA" in claims

            # Verify values from settings
            assert claims["userID"] == "test-batch-user"
            assert claims["userLocation"] == "test-server-01"
            assert claims["LoA"] == "SPID_L2"

    def test_get_modi_headers_uses_standard_base64_for_digest(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Digest uses standard base64 with padding (RFC 3230)."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Extract base64 part from Digest header
            digest_b64 = headers["Digest"].split("=", 1)[1]

            # Standard base64 should NOT contain urlsafe characters
            assert "-" not in digest_b64
            assert "_" not in digest_b64

            # Should decode with standard base64
            decoded = base64.b64decode(digest_b64)
            assert len(decoded) == 32  # SHA-256 = 32 bytes

    def test_get_modi_headers_without_modi_context_returns_empty(
        self, mock_env_without_modi: dict[str, str]
    ) -> None:
        """Test that get_modi_headers returns empty dict without ModI context."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_without_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            assert headers == {}

    def test_get_modi_headers_without_modi_audience_returns_empty(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that get_modi_headers returns empty dict without modi_audience."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                # No modi_audience
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            assert headers == {}

    def test_get_modi_headers_jwt_header_has_correct_structure(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that JWT header has correct alg, typ, and kid."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode JWT header
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
            header = json.loads(base64.urlsafe_b64decode(header_b64))

            assert header["alg"] == "RS256"
            assert header["typ"] == "JWT"
            assert header["kid"] == "test-key-id"

    def test_get_modi_headers_each_call_generates_unique_jti(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that each call generates a unique jti in both JWTs."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}

            sig_jtis = set()
            track_jtis = set()

            for _ in range(5):
                headers = manager.get_modi_headers(payload)

                # Extract jti from Signature JWT
                sig_jwt = headers["Agid-JWT-Signature"]
                parts = sig_jwt.split(".")
                claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                claims = json.loads(base64.urlsafe_b64decode(claims_b64))
                sig_jtis.add(claims["jti"])

                # Extract jti from Tracking JWT
                track_jwt = headers["Agid-JWT-TrackingEvidence"]
                parts = track_jwt.split(".")
                claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                claims = json.loads(base64.urlsafe_b64decode(claims_b64))
                track_jtis.add(claims["jti"])

            # All jti values should be unique
            assert len(sig_jtis) == 5
            assert len(track_jtis) == 5

    def test_get_modi_headers_nbf_equals_iat(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that nbf equals iat in both JWTs (token valid immediately)."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://api.example.com",
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Check Signature JWT
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))
            assert claims["nbf"] == claims["iat"]

            # Check Tracking JWT
            track_jwt = headers["Agid-JWT-TrackingEvidence"]
            parts = track_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))
            assert claims["nbf"] == claims["iat"]


class TestModIAudienceRequirements:
    """Tests for ModI JWT audience requirements.

    The audience (aud) claim in ModI JWTs MUST match the API server URL.
    This is a critical requirement for INTEGRITY_REST_02 pattern validation.
    """

    @pytest.fixture
    def mock_env_with_modi(self, mock_private_key: Path) -> dict[str, str]:
        """Create environment variables with ModI audit context."""
        return {
            "PDND_KID": "test-key-id",
            "PDND_ISSUER": "test-client-id",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.uat.interop.pagopa.it/client-assertion",
            "PDND_KEY_PATH": str(mock_private_key),
            "PDND_PURPOSE_ID_PA": "pa-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE": "coordinate-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "coordinate-bulk-purpose-id",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
            "PDND_MODI_USER_ID": "test-batch-user",
            "PDND_MODI_USER_LOCATION": "test-server-01",
            "PDND_MODI_LOA": "SPID_L2",
        }

    def test_signature_jwt_audience_matches_modi_audience(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Signature JWT aud claim matches the modi_audience parameter."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        # The modi_audience should be the API server URL
        api_server_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=api_server_url,
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode Signature JWT claims
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            # aud MUST match the API server URL (modi_audience)
            assert claims["aud"] == api_server_url

    def test_tracking_jwt_audience_matches_modi_audience(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that Tracking JWT aud claim matches the modi_audience parameter."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        api_server_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=api_server_url,
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode Tracking JWT claims
            track_jwt = headers["Agid-JWT-TrackingEvidence"]
            parts = track_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            # aud MUST match the API server URL (modi_audience)
            assert claims["aud"] == api_server_url

    def test_audience_is_full_api_url_not_base_domain(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that audience is the full API URL, not just the base domain.

        Per ModI INTEGRITY_REST_02, the audience should be the complete API
        endpoint URL, not a shortened or different domain.
        """
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        # Full API URL (correct)
        full_api_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=full_api_url,
            )

            payload = {"codcom": "H501", "operazione": "M"}
            headers = manager.get_modi_headers(payload)

            # Decode JWT claims
            sig_jwt = headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
            claims = json.loads(base64.urlsafe_b64decode(claims_b64))

            # Audience should be the full URL with path
            assert "/govway/rest/in/" in claims["aud"]
            assert claims["aud"].startswith("https://")
            # Should NOT be just a base domain like "https://modipa-val.anpr.interno.it"
            assert claims["aud"] != "https://modipa-val.anpr.interno.it"

    def test_different_apis_have_different_audiences(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that different API endpoints produce different audiences.

        Each API (coordinate, consultazione, etc.) has its own endpoint URL
        and thus should have a different audience in the JWT.
        """
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        coordinate_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"
        consultazione_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-consultazione/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)

            # Create manager for coordinate API
            coord_manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=coordinate_url,
            )

            # Create manager for PA (consultazione) API
            pa_manager = PDNDAuthManager(
                api_type=APIType.PA,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=consultazione_url,
            )

            payload = {"codcom": "H501"}

            # Get headers from both
            coord_headers = coord_manager.get_modi_headers(payload)
            pa_headers = pa_manager.get_modi_headers(payload)

            # Decode audiences
            def get_audience(jwt_token: str) -> str:
                parts = jwt_token.split(".")
                claims_b64 = parts[1] + "=" * (4 - len(parts[1]) % 4)
                claims = json.loads(base64.urlsafe_b64decode(claims_b64))
                return claims["aud"]

            coord_aud = get_audience(coord_headers["Agid-JWT-Signature"])
            pa_aud = get_audience(pa_headers["Agid-JWT-Signature"])

            # Audiences should be different for different APIs
            assert coord_aud != pa_aud
            assert coord_aud == coordinate_url
            assert pa_aud == consultazione_url


class TestModIAudienceMismatchError:
    """Tests for ModI audience mismatch detection and error messaging.

    When the modi_audience doesn't match the actual API server URL,
    the system should detect this and provide a clear error message.
    """

    @pytest.fixture
    def mock_env_with_modi(self, mock_private_key: Path) -> dict[str, str]:
        """Create environment variables with ModI audit context."""
        return {
            "PDND_KID": "test-key-id",
            "PDND_ISSUER": "test-client-id",
            "PDND_SUBJECT": "test-subject",
            "PDND_AUDIENCE": "https://auth.uat.interop.pagopa.it/client-assertion",
            "PDND_KEY_PATH": str(mock_private_key),
            "PDND_PURPOSE_ID_PA": "pa-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE": "coordinate-purpose-id",
            "PDND_PURPOSE_ID_COORDINATE_BULK": "coordinate-bulk-purpose-id",
            "PDND_PURPOSE_ID_ACCESSI": "",
            "PDND_PURPOSE_ID_INTERNI": "",
            "PDND_PURPOSE_ID_ODONIMI": "",
            "PDND_MODI_USER_ID": "test-batch-user",
            "PDND_MODI_USER_LOCATION": "test-server-01",
            "PDND_MODI_LOA": "SPID_L2",
        }

    def test_audience_mismatch_raises_error_with_clear_message(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that mismatched audience raises an error with clear message.

        If someone passes a modi_audience that doesn't match the server_url,
        this is likely a configuration error that will cause 400 errors from
        the API. We should detect and report this clearly.
        """
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings
        from anncsu.common.errors import AudienceMismatchError

        # Wrong audience (different domain than the actual API)
        wrong_audience = "https://modipa-val.anpr.interno.it"
        actual_server_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)

            # Should raise an error when audience doesn't match server URL
            with pytest.raises(AudienceMismatchError) as exc_info:
                PDNDAuthManager(
                    api_type=APIType.COORDINATE,
                    settings=settings,
                    token_endpoint="https://auth.example.com/token",
                    modi_audience=wrong_audience,
                    server_url=actual_server_url,
                )

            # Error message should be helpful
            error_msg = str(exc_info.value)
            assert "audience" in error_msg.lower()
            assert wrong_audience in error_msg or "anpr.interno.it" in error_msg
            assert actual_server_url in error_msg or "agenziaentrate.it" in error_msg

    def test_audience_matching_server_url_does_not_raise(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that matching audience and server_url works without error."""
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        # Correct: audience matches server URL
        server_url = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-aggiornamento-coordinate/v1"

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)

            # Should NOT raise when audience matches server URL
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience=server_url,
                server_url=server_url,
            )

            assert manager.has_modi_generator

    def test_audience_mismatch_detected_by_domain(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that audience mismatch is detected when domains differ.

        Common mistake: using modipa-val.anpr.interno.it instead of
        modipa-val.agenziaentrate.it
        """
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings
        from anncsu.common.errors import AudienceMismatchError

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)

            # Different domains - this is wrong
            with pytest.raises(AudienceMismatchError):
                PDNDAuthManager(
                    api_type=APIType.COORDINATE,
                    settings=settings,
                    token_endpoint="https://auth.example.com/token",
                    modi_audience="https://wrong-domain.example.com/api/v1",
                    server_url="https://correct-domain.example.com/api/v1",
                )

    def test_no_validation_when_server_url_not_provided(
        self, mock_env_with_modi: dict[str, str]
    ) -> None:
        """Test that no validation occurs when server_url is not provided.

        When server_url is None, we can't validate the audience.
        This is acceptable for backward compatibility.
        """
        from anncsu.common.auth import PDNDAuthManager
        from anncsu.common.config import APIType, ClientAssertionSettings

        with patch.dict("os.environ", mock_env_with_modi, clear=False):
            settings = ClientAssertionSettings(_env_file=None)

            # Should not raise even with potentially wrong audience
            # when server_url is not provided
            manager = PDNDAuthManager(
                api_type=APIType.COORDINATE,
                settings=settings,
                token_endpoint="https://auth.example.com/token",
                modi_audience="https://any-audience.example.com",
                # No server_url provided
            )

            assert manager.has_modi_generator
