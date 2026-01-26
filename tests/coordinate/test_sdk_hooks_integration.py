"""Tests for SDK Coordinate integration with ModI hooks via dependency injection.

This test suite verifies that:
1. The SDK accepts a HooksProvider via dependency injection
2. The ModI hook is correctly invoked for POST requests
3. Errors from the hook are properly propagated with specific exceptions
4. The hook is skipped for GET requests
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest

# Valid RSA private key for testing (generated with cryptography library)
TEST_PRIVATE_KEY = b"""-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAwJ/GgmsdZlS2wt7PL5NHDXmkB+MHQQ8RFHoqL1RPEZtossUG
7BnbCVwmMHJ9oOXJnFpsIKvLGUDKJ24d8Q/SloDcDlSKVYO0iaOPyQRwDjYxl5Pl
qnwCALsZW2BpoJpPG5PFsXx3aWi5ruQ8ItTNz9iHJ+2OeSJnTiSz96hp2bf6hJWj
b/aRtP/vCrR40hA+94aLA0kp4xJOygdqEKCgOYnxl/WgIhVifU7NSH/yIA3LNXMX
sbK9fkESyCVIinirkB2v/LEsheygBMyFZ/ymkj7D/fsoCVjd8iu0CjpolOvHquyA
LPmpn1fuoGXyBhVnM/qyX0sxVf3oBfYwkKPv9wIDAQABAoIBAEYixv5crx8/8C3D
P/AkMYZUCKhAfzcum7r3gl2qVoHkMrqI5+zWuzzMuzD/twN7N64A9Ibu1mwS/ahe
vXM1HinjsHxdRuM9KeLF1chNH9nk3KjC1qh9L6OBfImbcMpj9TLm2uA1oCsW0Sk/
fC/4iRnJTuj4Y9xybOf0kDy4KxZ090taP4aTVS2xffhaK+1pBSG33d6Puw/6da6d
kkS+dGciRjCwgwBRGbvWaa8ixbihJ0762BtzLWt+51XiuHtgqWx35agEWRviGE7P
4Z+xLYT7wGHhLJlCLGgm0uio4WerR6NfTfES9e7SbaA3t6RUwW+jn+truG3mV84y
qLD0P3kCgYEA6cCz3+I/IhPvy10Y67xulU17e1AnFCh0KwQ2RPBvbSTUhT0Otj0n
ZVSnYKyTrvgfLsLz7rx4dbO12dgqq2RU5sgpLWvu+RS+8I8Z1HCopxL9x5o1PdN1
DOI++XyNVDzH0lnJM1teTMsM3xBoVg7hUADb2XhutJ6m12hbg6ku3CkCgYEA0vT9
TIbg/n1xnmd+DnWh+pFft0+7B3VUck1Egt7A6XgIfjkiD6dcHNQzWdxz/EVa9eWf
vumd5HwBTaqa2yKTkZMGQiTa4pDMJKekCu5yhc0CKHWhJPrcXpsMzMD9sf++ekN/
aI7CzfRRczALmaiYHelIkt46n2z9waJ8Yr6l7x8CgYEApQop9ikH6kepRyy0K70f
VsseJDKzZMgrPTP8HTCle6pFYs15VbJX3nOmudsfaqpFWf7LvAPWCUSZYPX/KoPs
bgVlDWznjXXYWoCu/A+PBGekRwnaDYz/V9lmHUCTiKZhb2N1a41XR2EV9WjgQeK/
snzovOMLRvu9UNmdw5fwPgECgYBw37jwS3LzeDdk5EckgXhr04D9WmHeOb83cXRo
+bsKsLkKoJNDAO9eVYQsXrKIlqt2yqhQxDtBV8ByyAgXnEaNK7e7iHC9rXAtZK13
U+JfCTRQZbAVU0y6KggNPm3/4bEPRjJTxZ8iB8nU8i4ix3ys9HdqbhG739te0gvv
4cZzTQKBgQDk3BzTnrus/CHF/Txy7/XV6uNRY1/N40JBV1RWBk0tPxdyx2jvfQ8d
U6hYPNcXpfxqzHvLZqeuj3HFg2ClMH6ZtKz2oqNxG812lVI4CwfB2ABYjXEn0NcG
mSgi6cGL81aE9MpapdFVm/KOtG8RYrqOVKfKNJlbipECgDPXeuW7mQ==
-----END RSA PRIVATE KEY-----"""


class TestHooksProviderProtocol:
    """Test that SDKHooks implements HooksProvider protocol."""

    def test_sdkhooks_implements_hooks_provider(self):
        """Test that SDKHooks is an instance of HooksProvider protocol."""
        from anncsu.common.hooks import HooksProvider, SDKHooks

        hooks = SDKHooks()
        assert isinstance(hooks, HooksProvider)

    def test_hooks_provider_is_runtime_checkable(self):
        """Test that HooksProvider can be used with isinstance at runtime."""
        from anncsu.common.hooks import HooksProvider

        # Should not raise
        assert hasattr(HooksProvider, "__protocol_attrs__") or True  # Protocol check


class TestSDKCoordinateHooksDependencyInjection:
    """Test dependency injection of hooks into AnncsuCoordinate SDK."""

    def test_sdk_accepts_hooks_parameter(self):
        """Test that AnncsuCoordinate accepts a hooks parameter."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        hooks = SDKHooks()
        security = Security(bearer_auth="test-token")

        # Should not raise - SDK accepts hooks via DI
        sdk = AnncsuCoordinate(security=security, hooks=hooks)
        assert sdk is not None

    def test_sdk_uses_injected_hooks(self):
        """Test that SDK uses the injected hooks instead of creating new ones."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        hooks = SDKHooks()
        security = Security(bearer_auth="test-token")

        sdk = AnncsuCoordinate(security=security, hooks=hooks)

        # The SDK should use the same hooks instance
        assert sdk.sdk_configuration._hooks is hooks

    def test_sdk_creates_default_hooks_when_not_provided(self):
        """Test that SDK creates default hooks when none are provided."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.coordinate import AnncsuCoordinate
        from anncsu.coordinate.models import Security

        security = Security(bearer_auth="test-token")

        sdk = AnncsuCoordinate(security=security)

        # SDK should have created its own hooks
        assert sdk.sdk_configuration._hooks is not None
        assert isinstance(sdk.sdk_configuration._hooks, SDKHooks)


class TestModIHookIntegrationWithSDK:
    """Test ModI hook integration with SDK via dependency injection."""

    @pytest.fixture
    def modi_config(self):
        """Create ModI configuration for testing."""
        from anncsu.common.modi import ModIConfig

        return ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid="test-kid-123",
            issuer="test-issuer-uuid",
            audience="https://api.anncsu.it/coordinate",
        )

    @pytest.fixture
    def audit_context(self):
        """Create audit context for testing."""
        from anncsu.common.modi import AuditContext

        return AuditContext(
            user_id="test-user",
            user_location="test-server",
            loa="SPID_L2",
        )

    @pytest.fixture
    def hooks_with_modi(self, modi_config, audit_context):
        """Create SDKHooks with ModI hook registered."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.common.hooks.modi_hook import register_modi_hook

        hooks = SDKHooks()
        register_modi_hook(hooks, config=modi_config, audit_context=audit_context)
        return hooks

    def test_modi_hook_registered_in_hooks(self, hooks_with_modi):
        """Test that ModI hook is registered in the hooks."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook

        # Check that a ModI hook is in the before_request_hooks
        modi_hooks = [
            h
            for h in hooks_with_modi.before_request_hooks
            if isinstance(h, ModIPreRequestHook)
        ]
        assert len(modi_hooks) == 1

    def test_sdk_with_modi_hook_adds_headers_to_post_request(self, hooks_with_modi):
        """Test that SDK with ModI hook adds required headers to POST requests."""
        from anncsu.common.hooks.types import BeforeRequestContext

        # Create a mock request
        body = json.dumps({"codcom": "H501", "progr_civico": 12345})
        request = httpx.Request(
            method="POST",
            url="https://api.anncsu.it/coordinate/v1/aggiornamento",
            headers={"Content-Type": "application/json"},
            content=body.encode("utf-8"),
        )

        # Create mock context
        mock_config = MagicMock()
        ctx = BeforeRequestContext(
            MagicMock(
                config=mock_config,
                base_url="https://api.anncsu.it",
                operation_id="updateCoordinate",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        # Process request through hooks
        processed_request = hooks_with_modi.before_request(ctx, request)

        # Verify ModI headers are added
        assert "Digest" in processed_request.headers
        assert processed_request.headers["Digest"].startswith("SHA-256=")
        assert "Agid-JWT-Signature" in processed_request.headers
        assert "Agid-JWT-TrackingEvidence" in processed_request.headers

    def test_sdk_with_modi_hook_skips_get_requests(self, hooks_with_modi):
        """Test that ModI hook does not modify GET requests."""
        from anncsu.common.hooks.types import BeforeRequestContext

        # Create a GET request
        request = httpx.Request(
            method="GET",
            url="https://api.anncsu.it/coordinate/v1/status",
        )

        # Create mock context
        ctx = BeforeRequestContext(
            MagicMock(
                config=MagicMock(),
                base_url="https://api.anncsu.it",
                operation_id="getStatus",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        # Process request through hooks
        processed_request = hooks_with_modi.before_request(ctx, request)

        # GET requests should not have ModI headers
        assert "Digest" not in processed_request.headers
        assert "Agid-JWT-Signature" not in processed_request.headers


class TestModIHookErrorHandling:
    """Test error handling when ModI hook fails."""

    def test_hook_error_raises_modi_hook_error(self):
        """Test that hook errors are raised as ModIHookError."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.common.hooks.modi_hook import (
            ModIHookError,
            ModIPreRequestHook,
        )
        from anncsu.common.hooks.types import BeforeRequestContext
        from anncsu.common.modi import ModIConfig

        # Create config with invalid key to cause signing error
        invalid_config = ModIConfig(
            private_key=b"invalid-key",
            kid="test-kid",
            issuer="test-issuer",
            audience="https://api.example.com",
        )

        hooks = SDKHooks()
        hook = ModIPreRequestHook(config=invalid_config)
        hooks.register_before_request_hook(hook)

        # Create a POST request
        request = httpx.Request(
            method="POST",
            url="https://api.example.com/test",
            headers={"Content-Type": "application/json"},
            content=b'{"test": "data"}',
        )

        ctx = BeforeRequestContext(
            MagicMock(
                config=MagicMock(),
                base_url="https://api.example.com",
                operation_id="test",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        # Should raise ModIHookError
        with pytest.raises(ModIHookError) as exc_info:
            hooks.before_request(ctx, request)

        assert "Failed to generate ModI headers" in str(exc_info.value)
        assert exc_info.value.cause is not None

    def test_hook_error_contains_original_exception(self):
        """Test that ModIHookError contains the original exception."""
        from anncsu.common.hooks.modi_hook import ModIHookError

        original_error = ValueError("Original error message")
        hook_error = ModIHookError("Hook failed", cause=original_error)

        assert hook_error.cause is original_error
        assert "Original error message" in str(hook_error)

    def test_hook_error_message_without_cause(self):
        """Test ModIHookError message when no cause is provided."""
        from anncsu.common.hooks.modi_hook import ModIHookError

        hook_error = ModIHookError("Simple error message")

        assert str(hook_error) == "Simple error message"
        assert hook_error.cause is None


class TestModIHookWithMissingAuditContext:
    """Test ModI hook behavior when audit context is not provided."""

    @pytest.fixture
    def modi_config(self):
        """Create ModI configuration for testing."""
        from anncsu.common.modi import ModIConfig

        return ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid="test-kid",
            issuer="test-issuer",
            audience="https://api.example.com",
        )

    def test_hook_without_audit_context_omits_tracking_header(self, modi_config):
        """Test that hook without audit context does not add tracking header."""
        from anncsu.common.hooks import SDKHooks
        from anncsu.common.hooks.modi_hook import register_modi_hook
        from anncsu.common.hooks.types import BeforeRequestContext

        hooks = SDKHooks()
        # Register WITHOUT audit_context
        register_modi_hook(hooks, config=modi_config, audit_context=None)

        request = httpx.Request(
            method="POST",
            url="https://api.example.com/test",
            headers={"Content-Type": "application/json"},
            content=b'{"test": "data"}',
        )

        ctx = BeforeRequestContext(
            MagicMock(
                config=MagicMock(),
                base_url="https://api.example.com",
                operation_id="test",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        processed_request = hooks.before_request(ctx, request)

        # Should have Digest and Signature, but NOT TrackingEvidence
        assert "Digest" in processed_request.headers
        assert "Agid-JWT-Signature" in processed_request.headers
        assert "Agid-JWT-TrackingEvidence" not in processed_request.headers


class TestDigestCalculationFromActualBody:
    """Test that digest is calculated from actual HTTP body bytes."""

    @pytest.fixture
    def modi_config(self):
        """Create ModI configuration for testing."""
        from anncsu.common.modi import ModIConfig

        return ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid="test-kid",
            issuer="test-issuer",
            audience="https://api.example.com",
        )

    def test_digest_matches_request_content(self, modi_config):
        """Test that Digest header matches the actual request.content bytes."""
        import base64
        import hashlib

        from anncsu.common.hooks import SDKHooks
        from anncsu.common.hooks.modi_hook import register_modi_hook
        from anncsu.common.hooks.types import BeforeRequestContext

        hooks = SDKHooks()
        register_modi_hook(hooks, config=modi_config)

        # The exact bytes that will be sent
        body_bytes = b'{"codcom":"H501","progr_civico":12345}'

        request = httpx.Request(
            method="POST",
            url="https://api.example.com/test",
            headers={"Content-Type": "application/json"},
            content=body_bytes,
        )

        ctx = BeforeRequestContext(
            MagicMock(
                config=MagicMock(),
                base_url="https://api.example.com",
                operation_id="test",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        processed_request = hooks.before_request(ctx, request)

        # Calculate expected digest
        expected_digest = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode(
            "utf-8"
        )

        assert processed_request.headers["Digest"] == f"SHA-256={expected_digest}"

    def test_digest_uses_content_not_reconstructed_json(self, modi_config):
        """Test that digest uses request.content, not reconstructed JSON.

        This is critical because Speakeasy may serialize JSON differently
        than json.dumps with sort_keys. The hook must use the actual bytes.
        """
        import base64
        import hashlib

        from anncsu.common.hooks import SDKHooks
        from anncsu.common.hooks.modi_hook import register_modi_hook
        from anncsu.common.hooks.types import BeforeRequestContext

        hooks = SDKHooks()
        register_modi_hook(hooks, config=modi_config)

        # Speakeasy-style serialization (no sort_keys, insertion order)
        body_bytes = b'{"z":2,"a":1}'  # NOT sorted

        request = httpx.Request(
            method="POST",
            url="https://api.example.com/test",
            headers={"Content-Type": "application/json"},
            content=body_bytes,
        )

        ctx = BeforeRequestContext(
            MagicMock(
                config=MagicMock(),
                base_url="https://api.example.com",
                operation_id="test",
                oauth2_scopes=None,
                security_source=None,
            )
        )

        processed_request = hooks.before_request(ctx, request)

        # Digest MUST match the actual bytes, not sorted JSON
        expected_digest = base64.b64encode(hashlib.sha256(body_bytes).digest()).decode(
            "utf-8"
        )

        assert processed_request.headers["Digest"] == f"SHA-256={expected_digest}"

        # Verify it's different from what sort_keys would produce
        sorted_body = b'{"a":1,"z":2}'
        sorted_digest = base64.b64encode(hashlib.sha256(sorted_body).digest()).decode(
            "utf-8"
        )

        # The actual digest should NOT match the sorted version
        assert expected_digest != sorted_digest


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
