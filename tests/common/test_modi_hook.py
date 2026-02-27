"""Tests for ModI pre-request hook.

This module tests the ModIPreRequestHook that calculates the Digest header
from the actual serialized HTTP body and generates the ModI JWT headers.

The hook intercepts requests AFTER Speakeasy serializes the body, ensuring
the Digest header matches the exact bytes that will be sent to the server.
"""

from __future__ import annotations

import base64
import hashlib
import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import httpx

if TYPE_CHECKING:
    pass


# Test RSA key pair for JWT signing (for testing only)
# Generated with: openssl genrsa 2048
TEST_PRIVATE_KEY = b"""-----BEGIN RSA PRIVATE KEY-----
MIIEoQIBAAKCAQEAwllvtqjOmsQPQumpcfPUy2D9SwZBq0BzneiggRSnMgakuKfY
v04FZFLsEGdwYL5EJYFaGkgaNRnHmTXRKK/bdKfUC1cIbfQjplolwjbar5oe5WAg
a7OWcHLICNGrXtOfiYd1xE7nXUjJ2Hi02plRSJsUr9S8p0zrRIugscRAcCOiinHn
3BPzVNcyi56TydUtuz14v8s+U/a9T7aqj7jrOOc+s1LMQ6zpGX9P6eB7Hc7TEXPh
k0eA6/oufaYRQHI4sryui92qWgBh0F4touiJbv7qtNxpBjMysx0NLWOAbrvEfJyk
kGxbeXQ7AhfXA4waT/OGNxdc+ir6qyI0fxom2wIDAQABAoH/E8mYIocb8tNIlHwp
Ulbwr7T4Fd2O07S6l9/vDTVoGurbCeKZvTmMimU5DHqblW9YkkRrj+u5qR87KsO7
il+nUJKp7ZMUh7kXDBuc6kHnw9ACvgg0vPIy/edhXc1LqeI9bQwJKb6WEWPoNBJN
7NfmWBdir7EzFGPs+QUnsk2NtHXfJNszW42ggHcSZgkiaJAxk1k6dPb+vBGj+wjK
Cic9QB0HBGMVtZnsZTdjPJmWpDY0wguFEjwfe1Q7N489fNRlT6ZsJmxpgpOUWeY8
qtR7TUyOeE9AfdgnzwB6V8OBFKJ+5+x2hO35u/SbxftHROYtcdFK7i2ge4WpK0kP
W7GpAoGBAPGWYAB25t29oa8NnUcAxcV1e5idt8HtzitIIk3EgBYWQnIic0U7W7nu
3j0dOTT7v4Q6Qu64RjjdvRuuntTmLhBT1LQf45RNTaONwCD//qhoAQbEDLusmYCY
JKM3sfV7N0lKFks7PSfLS47dK3ORp6Iv7yFunB5FH3z0IoRYRG1FAoGBAM3xnzzx
53mv992xCUjrdxlr6Hc/KhtpYNL1i/azUWLJ42CYZJnObBiPwXIGWv3kn6GLObO+
HmAMq2sJ3xLZdrjWzH5Y3nwNqcuR4yNLZYW0+Ivj5emY0FWEDSNL5u5LQvGwjfGW
FKKiEQrpJc05ERUHwHv5C5hTBlwJZ9EGPzWfAoGBALtvnzZdCgvaV/p4RqFTER59
YxJqs6prtbzQ74SEw5ffV1g0MFjzj9w3Xwfth3f7JoERruKF6D2wlEtI9QRbPjv+
vpWt9CUYwPb3QKyZ0VuZrcoxC2wEougpoqtbx9+c5K0hJSDjajRYv1utb0vwIy5r
oE3BArFdkeuhgrJJxXU9AoGAfow9rEZ9VZIivlA+A1flXHKpazUeG6/6Nkd6VQLF
PO4P0VhzYOuuEr2rQfTTzvXAfZS+xUtLAPxoDSMIt113jYc4K19Sf2op7xRbPWHk
JXAZ1mQY8Bzdz96P8COA6ObIYRl7b3sofPMXg9vWRbAOZhzYU5WqYVSLMNz6tT+g
ccMCgYA0hR+kXVwQbO0Nb+wwj6YN2QdrMQgrZ0/32tR0654DLcIfZ4QrLRPwv/lE
X+vkvleC7IuujtVJH7Nd7zFZorGN3ReVqaYxCvVvvqESq8W2wSy2GC/JLkzhUM8H
mM4ZG9HRMdYKpSZT4kctPPcI71jauhfqcgF2IWivJ1wxgTJ3Hw==
-----END RSA PRIVATE KEY-----"""

TEST_KID = "test-kid-12345"
TEST_ISSUER = "test-client-id"
TEST_AUDIENCE = "https://modipa-val.agenziaentrate.it/govway/rest/in/AgenziaEntrate-PDND/anncsu-coordinate/v1"


def compute_expected_digest(body: bytes) -> str:
    """Compute expected SHA-256 digest for test verification."""
    digest = hashlib.sha256(body).digest()
    digest_b64 = base64.b64encode(digest).decode("utf-8")
    return f"SHA-256={digest_b64}"


class TestModIPreRequestHookInterface:
    """Tests for ModIPreRequestHook interface compliance."""

    def test_hook_implements_before_request_hook_interface(self):
        """Test that ModIPreRequestHook implements BeforeRequestHook."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.hooks.types import BeforeRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)
        assert isinstance(hook, BeforeRequestHook)

    def test_hook_has_before_request_method(self):
        """Test that hook has before_request method."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)
        assert hasattr(hook, "before_request")
        assert callable(hook.before_request)


class TestModIPreRequestHookHappyPath:
    """Tests for successful ModI header injection."""

    def test_hook_adds_digest_header_from_request_body(self):
        """Test that hook computes Digest from actual request body bytes."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        # Create request with JSON body
        body = b'{"codcom":"H501","operazione":"M"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should return modified request
        assert isinstance(result, httpx.Request)

        # Should have Digest header computed from actual body
        expected_digest = compute_expected_digest(body)
        assert result.headers.get("Digest") == expected_digest

    def test_hook_adds_agid_jwt_signature_header(self):
        """Test that hook adds Agid-JWT-Signature header."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should have Agid-JWT-Signature header
        assert "Agid-JWT-Signature" in result.headers
        signature = result.headers["Agid-JWT-Signature"]

        # Should be a valid JWT (3 parts separated by dots)
        parts = signature.split(".")
        assert len(parts) == 3

    def test_hook_adds_agid_jwt_tracking_evidence_header(self):
        """Test that hook adds Agid-JWT-TrackingEvidence header when audit context provided."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should have Agid-JWT-TrackingEvidence header
        assert "Agid-JWT-TrackingEvidence" in result.headers
        tracking = result.headers["Agid-JWT-TrackingEvidence"]

        # Should be a valid JWT
        parts = tracking.split(".")
        assert len(parts) == 3

    def test_hook_signature_jwt_contains_correct_digest_in_signed_headers(self):
        """Test that signature JWT contains the same digest as HTTP header."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        body = b'{"codcom":"H501","operazione":"M"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Extract digest from HTTP header
        http_digest = result.headers["Digest"]

        # Extract digest from JWT signed_headers claim
        signature_jwt = result.headers["Agid-JWT-Signature"]
        # Decode JWT payload (middle part)
        payload_b64 = signature_jwt.split(".")[1]
        # Add padding if needed
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Find digest in signed_headers
        jwt_digest = None
        for header in payload["signed_headers"]:
            if "digest" in header:
                jwt_digest = header["digest"]
                break

        # Digests must match
        assert jwt_digest == http_digest

    def test_hook_preserves_existing_headers(self):
        """Test that hook preserves existing request headers."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer existing-token",
                "X-Custom-Header": "custom-value",
            },
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Original headers should be preserved
        assert result.headers.get("Authorization") == "Bearer existing-token"
        assert result.headers.get("X-Custom-Header") == "custom-value"
        assert result.headers.get("Content-Type") == "application/json"

    def test_hook_works_without_audit_context(self):
        """Test that hook works without audit context (no tracking header)."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        # No audit context
        hook = ModIPreRequestHook(config=config, audit_context=None)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should have Digest and Signature headers
        assert "Digest" in result.headers
        assert "Agid-JWT-Signature" in result.headers

        # Should NOT have TrackingEvidence header
        assert "Agid-JWT-TrackingEvidence" not in result.headers


class TestModIPreRequestHookSkipConditions:
    """Tests for conditions where hook should skip processing."""

    def test_hook_skips_get_requests(self):
        """Test that hook skips GET requests (no body to digest)."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        request = httpx.Request(
            "GET",
            "https://api.example.com/coordinate",
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should return original request unchanged
        assert result == request
        assert "Digest" not in result.headers
        assert "Agid-JWT-Signature" not in result.headers

    def test_hook_skips_requests_without_body(self):
        """Test that hook skips requests without body."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        # POST without body
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should return original request unchanged
        assert result == request

    def test_hook_skips_requests_with_empty_body(self):
        """Test that hook skips requests with empty body."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=b"",
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should return original request unchanged
        assert result == request


class TestModIPreRequestHookErrorScenarios:
    """Tests for error scenarios in ModI hook."""

    def test_hook_returns_error_when_private_key_invalid(self):
        """Test that hook returns error when private key is invalid."""
        from anncsu.common.hooks.modi_hook import (
            ModIHookError,
            ModIPreRequestHook,
        )
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=b"invalid-key",
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hook = ModIPreRequestHook(config=config, audit_context=audit)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Should return an error, not raise
        assert isinstance(result, ModIHookError)
        error_msg = str(result).lower()
        assert (
            "private key" in error_msg
            or "sign" in error_msg
            or "pem" in error_msg
            or "key" in error_msg
        )

    def test_hook_handles_empty_kid_gracefully(self):
        """Test that hook works even with empty kid (validation is elsewhere)."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        # Config with empty kid - JWT will still be generated
        # (kid validation should happen at configuration time, not in hook)
        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid="",  # Empty kid
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Hook should still work (generates JWT with empty kid)
        # Configuration validation should happen elsewhere
        assert isinstance(result, httpx.Request)
        assert "Agid-JWT-Signature" in result.headers


class TestModIHookError:
    """Tests for ModIHookError exception class."""

    def test_modi_hook_error_is_exception(self):
        """Test that ModIHookError is an Exception."""
        from anncsu.common.hooks.modi_hook import ModIHookError

        error = ModIHookError("Test error")
        assert isinstance(error, Exception)

    def test_modi_hook_error_with_message(self):
        """Test ModIHookError with message."""
        from anncsu.common.hooks.modi_hook import ModIHookError

        error = ModIHookError("Failed to generate headers")
        assert "Failed to generate headers" in str(error)

    def test_modi_hook_error_with_cause(self):
        """Test ModIHookError with original cause."""
        from anncsu.common.hooks.modi_hook import ModIHookError

        original = ValueError("Original error")
        error = ModIHookError("Failed to sign JWT", cause=original)

        assert error.cause == original
        assert "Failed to sign JWT" in str(error)


class TestModIPreRequestHookRegistration:
    """Tests for registering ModIPreRequestHook with SDK hooks system."""

    def test_hook_can_be_registered_with_hooks_system(self):
        """Test that hook can be registered with Speakeasy hooks system."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hooks = SDKHooks()
        hook = ModIPreRequestHook(config=config, audit_context=audit)

        # Should not raise
        hooks.register_before_request_hook(hook)

        # Hook should be in the list
        assert hook in hooks.before_request_hooks

    def test_register_modi_hook_helper_function(self):
        """Test helper function to register ModI hook."""
        from anncsu.common.hooks.modi_hook import (
            ModIPreRequestHook,
            register_modi_hook,
        )
        from anncsu.common.hooks.sdkhooks import SDKHooks
        from anncsu.common.modi import AuditContext, ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )
        audit = AuditContext(
            user_id="test-user",
            user_location="test-location",
            loa="SPID_L2",
        )

        hooks = SDKHooks()
        hook = register_modi_hook(hooks, config=config, audit_context=audit)

        # Should return the created hook instance
        assert isinstance(hook, ModIPreRequestHook)
        assert hook in hooks.before_request_hooks


class TestModIPreRequestHookExports:
    """Tests for module exports."""

    def test_hook_exported_from_hooks_module(self):
        """Test that ModIPreRequestHook is exported from hooks module."""
        from anncsu.common.hooks import ModIPreRequestHook

        assert ModIPreRequestHook is not None

    def test_modi_hook_error_exported_from_hooks_module(self):
        """Test that ModIHookError is exported from hooks module."""
        from anncsu.common.hooks import ModIHookError

        assert ModIHookError is not None

    def test_register_function_exported_from_hooks_module(self):
        """Test that register_modi_hook is exported."""
        from anncsu.common.hooks import register_modi_hook

        assert register_modi_hook is not None


class TestModIPreRequestHookDigestCalculation:
    """Tests for digest calculation from actual HTTP body."""

    def test_digest_calculated_from_exact_body_bytes(self):
        """Test that digest is calculated from exact body bytes, not re-serialized."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        # Body with specific formatting (keys not sorted, spaces after colons)
        # This is what Speakeasy might produce
        body = b'{"operazione": "M", "codcom": "H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Digest should match the EXACT bytes, not a re-serialized version
        expected_digest = compute_expected_digest(body)
        assert result.headers["Digest"] == expected_digest

        # If we sorted keys, the digest would be different
        sorted_body = b'{"codcom": "H501", "operazione": "M"}'
        wrong_digest = compute_expected_digest(sorted_body)
        assert result.headers["Digest"] != wrong_digest

    def test_digest_consistent_for_same_body(self):
        """Test that same body always produces same digest."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        body = b'{"codcom":"H501","operazione":"M"}'

        # Call hook multiple times
        digests = []
        for _ in range(3):
            request = httpx.Request(
                "POST",
                "https://api.example.com/coordinate",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            ctx = MagicMock()
            result = hook.before_request(ctx, request)
            digests.append(result.headers["Digest"])

        # All digests should be identical
        assert all(d == digests[0] for d in digests)

    def test_different_bodies_produce_different_digests(self):
        """Test that different bodies produce different digests."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        body1 = b'{"codcom":"H501"}'
        body2 = b'{"codcom":"H502"}'

        request1 = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body1,
            headers={"Content-Type": "application/json"},
        )
        request2 = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body2,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result1 = hook.before_request(ctx, request1)
        result2 = hook.before_request(ctx, request2)

        assert result1.headers["Digest"] != result2.headers["Digest"]


class TestModIPreRequestHookEServiceKid:
    """Regression tests: hook correctly uses whatever kid/key is in ModIConfig.

    The hook itself doesn't know about voucher vs ModI signing keys. It simply
    uses the kid and private_key from its ModIConfig. These tests verify
    that the hook works correctly with any kid value - confirming that once
    the config layer provides the right key, the hook will use it.
    """

    def test_hook_uses_kid_from_config_in_jwt_header(self):
        """Test that JWT header kid matches the config's kid value."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        # Use a distinctive kid to prove it ends up in the JWT header
        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid="my-custom-e-service-kid-789",
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Decode JWT header to verify kid
        sig_jwt = result.headers["Agid-JWT-Signature"]
        parts = sig_jwt.split(".")
        header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
        header = json.loads(base64.urlsafe_b64decode(header_b64))

        assert header["kid"] == "my-custom-e-service-kid-789"

    def test_hook_signs_with_private_key_from_config(self):
        """Test that JWT is signed with the config's private key."""
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        config = ModIConfig(
            private_key=TEST_PRIVATE_KEY,
            kid=TEST_KID,
            issuer=TEST_ISSUER,
            audience=TEST_AUDIENCE,
        )

        hook = ModIPreRequestHook(config=config, audit_context=None)

        body = b'{"codcom":"H501"}'
        request = httpx.Request(
            "POST",
            "https://api.example.com/coordinate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        ctx = MagicMock()
        result = hook.before_request(ctx, request)

        # Verify JWT can be decoded with the corresponding public key
        private_key_obj = load_pem_private_key(TEST_PRIVATE_KEY, password=None)
        public_key = private_key_obj.public_key()
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        from authlib.jose import jwt as jose_jwt

        sig_jwt = result.headers["Agid-JWT-Signature"]
        decoded = jose_jwt.decode(sig_jwt, public_key_pem)
        assert decoded["iss"] == TEST_ISSUER

    def test_hook_works_with_different_kid_values(self):
        """Test that hook works correctly with various kid values."""
        from anncsu.common.hooks.modi_hook import ModIPreRequestHook
        from anncsu.common.modi import ModIConfig

        kid_values = [
            "interop-kid-abc",
            "e-service-kid-xyz",
            "K5nXXEGyPeylnlgSlBk9s4G-1CNLaiNqBr_TWIgikcI",
            "3fFrxthtnwe6rkBtJ7TkI_UFS7gEhENW7Gf198lMIR8",
        ]

        for kid in kid_values:
            config = ModIConfig(
                private_key=TEST_PRIVATE_KEY,
                kid=kid,
                issuer=TEST_ISSUER,
                audience=TEST_AUDIENCE,
            )

            hook = ModIPreRequestHook(config=config, audit_context=None)

            body = b'{"test":"data"}'
            request = httpx.Request(
                "POST",
                "https://api.example.com/coordinate",
                content=body,
                headers={"Content-Type": "application/json"},
            )

            ctx = MagicMock()
            result = hook.before_request(ctx, request)

            assert isinstance(result, httpx.Request)

            # Verify kid in JWT header
            sig_jwt = result.headers["Agid-JWT-Signature"]
            parts = sig_jwt.split(".")
            header_b64 = parts[0] + "=" * (4 - len(parts[0]) % 4)
            header = json.loads(base64.urlsafe_b64decode(header_b64))

            assert header["kid"] == kid
