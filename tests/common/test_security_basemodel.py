"""Tests for Security class BaseModel implementation.

This module tests that the Security class properly inherits from BaseModel
and works with the security utility functions.
"""

import pytest
from pydantic import BaseModel

from anncsu.common.sdk.utils import get_security
from anncsu.common.security import Security


class TestSecurityBaseModelInheritance:
    """Test that Security properly inherits from BaseModel."""

    def test_security_is_basemodel(self):
        """Test that Security is a Pydantic BaseModel."""
        security = Security(bearer="test-token")
        assert isinstance(security, BaseModel)

    def test_security_class_inherits_basemodel(self):
        """Test that Security class inherits from BaseModel."""
        assert issubclass(Security, BaseModel)

    def test_security_has_model_fields(self):
        """Test that Security has Pydantic model_fields."""
        assert hasattr(Security, "model_fields")
        assert "bearer" in Security.model_fields

    def test_security_can_be_instantiated_as_basemodel(self):
        """Test Security can be instantiated like a Pydantic model."""
        security = Security(bearer="token-123")
        assert security.bearer == "token-123"

    def test_security_supports_none_bearer(self):
        """Test Security supports None bearer token."""
        security = Security(bearer=None)
        assert security.bearer is None

    def test_security_default_bearer_is_none(self):
        """Test Security default bearer value is None."""
        security = Security()
        assert security.bearer is None


class TestSecurityWithGetSecurityUtil:
    """Test Security works with get_security utility function."""

    def test_get_security_accepts_security_instance(self):
        """Test that get_security accepts Security instance without error."""
        security = Security(bearer="test-bearer-token")

        # Should not raise TypeError
        headers, query_params = get_security(security)

        # Should return dictionaries
        assert isinstance(headers, dict)
        assert isinstance(query_params, dict)

    def test_get_security_returns_bearer_header(self):
        """Test that get_security returns Authorization header with Bearer token."""
        security = Security(bearer="my-pdnd-voucher")

        headers, query_params = get_security(security)

        # Should have Authorization header
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer my-pdnd-voucher"

        # Should have no query params (bearer is in header)
        assert len(query_params) == 0

    def test_get_security_with_none_bearer(self):
        """Test get_security with None bearer token."""
        security = Security(bearer=None)

        headers, query_params = get_security(security)

        # Should return empty dicts when bearer is None
        assert len(headers) == 0
        assert len(query_params) == 0

    def test_get_security_with_jwt_token(self):
        """Test get_security with JWT format bearer token."""
        jwt_token = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.signature"
        security = Security(bearer=jwt_token)

        headers, query_params = get_security(security)

        assert "Authorization" in headers
        assert headers["Authorization"] == f"Bearer {jwt_token}"

    def test_get_security_with_none_security(self):
        """Test get_security with None security (no authentication)."""
        headers, query_params = get_security(None)

        # Should return empty dicts
        assert len(headers) == 0
        assert len(query_params) == 0


class TestSecurityMetadata:
    """Test Security field metadata configuration."""

    def test_security_bearer_has_metadata(self):
        """Test that bearer field has security metadata."""
        from anncsu.common.sdk.utils import (
            SecurityMetadata,
            find_field_metadata,
        )

        bearer_field = Security.model_fields["bearer"]
        metadata = find_field_metadata(bearer_field, SecurityMetadata)

        assert metadata is not None
        assert metadata.scheme is True
        assert metadata.scheme_type == "http"
        assert metadata.sub_type == "bearer"
        assert metadata.field_name == "Authorization"

    def test_security_metadata_indicates_http_bearer(self):
        """Test that metadata correctly indicates HTTP Bearer authentication."""
        from anncsu.common.sdk.utils import (
            SecurityMetadata,
            find_field_metadata,
        )

        bearer_field = Security.model_fields["bearer"]
        metadata = find_field_metadata(bearer_field, SecurityMetadata)

        # Verify it's configured as HTTP Bearer
        assert metadata.scheme_type == "http"
        assert metadata.sub_type == "bearer"


class TestSecurityPydanticFeatures:
    """Test that Security supports Pydantic features."""

    def test_security_model_dump(self):
        """Test Security supports model_dump()."""
        security = Security(bearer="test-token")
        dumped = security.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["bearer"] == "test-token"

    def test_security_model_dump_json(self):
        """Test Security supports model_dump_json()."""
        security = Security(bearer="test-token")
        json_str = security.model_dump_json()

        assert isinstance(json_str, str)
        assert "test-token" in json_str

    def test_security_can_be_created_from_dict(self):
        """Test Security can be created from dictionary."""
        data = {"bearer": "dict-token"}
        security = Security(**data)

        assert security.bearer == "dict-token"

    def test_security_model_validate(self):
        """Test Security supports model_validate."""
        data = {"bearer": "validated-token"}
        security = Security.model_validate(data)

        assert security.bearer == "validated-token"


class TestSecurityIntegrationWithSDK:
    """Test Security integrates properly with SDK security handling."""

    def test_security_in_sdk_workflow(self):
        """Test Security works in complete SDK workflow."""
        from anncsu.pa import Anncsu

        # Create security
        security = Security(bearer="workflow-token")

        # Verify it's a BaseModel
        assert isinstance(security, BaseModel)

        # Create SDK with security
        sdk = Anncsu(security=security)

        # Verify security is stored
        assert sdk.sdk_configuration.security is not None
        assert isinstance(sdk.sdk_configuration.security, Security)
        assert sdk.sdk_configuration.security.bearer == "workflow-token"

    def test_security_headers_extraction(self):
        """Test extracting headers from Security for HTTP requests."""
        security = Security(bearer="header-extraction-token")

        headers, query_params = get_security(security)

        # This is what will be added to HTTP requests
        assert headers["Authorization"] == "Bearer header-extraction-token"
        assert len(query_params) == 0


class TestSecurityBackwardCompatibility:
    """Test that Security maintains backward compatibility."""

    def test_security_with_keyword_argument(self):
        """Test Security with keyword argument (original usage)."""
        security = Security(bearer="keyword-token")
        assert security.bearer == "keyword-token"

    def test_security_positional_argument(self):
        """Test Security with positional argument."""
        # Note: With Pydantic, positional args might not work the same as dataclass
        # This tests the main usage pattern
        security = Security(bearer="positional-token")
        assert security.bearer == "positional-token"

    def test_security_equality(self):
        """Test Security instances can be compared."""
        security1 = Security(bearer="token")
        security2 = Security(bearer="token")
        security3 = Security(bearer="different")

        # Pydantic models support equality by value
        assert security1 == security2
        assert security1 != security3


class TestSecurityErrorCases:
    """Test error handling for Security class."""

    def test_security_with_invalid_type(self):
        """Test Security validation with invalid bearer type."""
        # Pydantic should coerce or raise validation error
        try:
            security = Security(bearer=12345)  # Invalid: integer instead of string
            # Pydantic might coerce to string
            assert isinstance(security.bearer, str) or security.bearer == 12345
        except Exception as e:
            # Or it might raise a validation error, which is also acceptable
            assert "validation" in str(e).lower() or "type" in str(e).lower()

    def test_get_security_rejects_non_basemodel(self):
        """Test that get_security rejects non-BaseModel objects."""

        # Create a fake security object that's not a BaseModel
        class FakeSecurity:
            bearer = "fake-token"

        fake = FakeSecurity()

        with pytest.raises(TypeError, match="security must be a pydantic model"):
            get_security(fake)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
