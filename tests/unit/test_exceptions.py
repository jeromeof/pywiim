"""Test exceptions module.

Tests exception hierarchy, creation, string representation, and context handling.
"""

from pywiim.exceptions import (
    WiiMConnectionError,
    WiiMError,
    WiiMInvalidDataError,
    WiiMRequestError,
    WiiMResponseError,
    WiiMTimeoutError,
)


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_exception_inheritance(self):
        """Test that exceptions inherit from WiiMError."""
        assert issubclass(WiiMConnectionError, WiiMError)
        assert issubclass(WiiMTimeoutError, WiiMError)
        assert issubclass(WiiMRequestError, WiiMError)
        assert issubclass(WiiMResponseError, WiiMError)
        assert issubclass(WiiMInvalidDataError, WiiMError)

    def test_request_error_inheritance(self):
        """Test that request error subclasses inherit correctly."""
        assert issubclass(WiiMTimeoutError, WiiMRequestError)
        assert issubclass(WiiMConnectionError, WiiMRequestError)


class TestExceptionCreation:
    """Test exception creation and basic functionality."""

    def test_base_exception_creation(self):
        """Test that base exception can be created."""
        err = WiiMError("Test message")
        assert str(err) == "Test message"

    def test_request_error_creation(self):
        """Test WiiMRequestError creation with context."""
        err = WiiMRequestError(
            "Request failed",
            endpoint="/api/status",
            attempts=3,
        )
        # String representation includes context
        assert "Request failed" in str(err)
        assert "endpoint=/api/status" in str(err)
        assert "attempts=3" in str(err)
        assert err.endpoint == "/api/status"
        assert err.attempts == 3
        assert err.device_info == {}
        assert err.operation_context == "api_call"

    def test_request_error_with_device_info(self):
        """Test WiiMRequestError with device information."""
        device_info = {
            "firmware_version": "5.0.1",
            "device_model": "WiiM Pro",
            "is_wiim_device": True,
        }
        err = WiiMRequestError(
            "Request failed",
            endpoint="/api/status",
            device_info=device_info,
        )
        assert err.device_info == device_info

    def test_request_error_with_last_error(self):
        """Test WiiMRequestError with underlying exception."""
        last_error = ValueError("Connection refused")
        err = WiiMRequestError(
            "Request failed",
            endpoint="/api/status",
            last_error=last_error,
        )
        assert err.last_error == last_error

    def test_response_error_creation(self):
        """Test WiiMResponseError creation."""
        err = WiiMResponseError(
            "Invalid JSON response",
            endpoint="/api/status",
        )
        # String representation includes context
        assert "Invalid JSON response" in str(err)
        assert "endpoint=/api/status" in str(err)
        assert err.endpoint == "/api/status"
        assert err.device_info == {}

    def test_connection_error_creation(self):
        """Test WiiMConnectionError creation."""
        err = WiiMConnectionError(
            "Connection failed",
            endpoint="/api/status",
        )
        assert isinstance(err, WiiMRequestError)
        # String representation includes context
        assert "Connection failed" in str(err)
        assert "endpoint=/api/status" in str(err)

    def test_timeout_error_creation(self):
        """Test WiiMTimeoutError creation."""
        err = WiiMTimeoutError(
            "Request timed out",
            endpoint="/api/status",
        )
        assert isinstance(err, WiiMRequestError)
        # String representation includes context
        assert "Request timed out" in str(err)
        assert "endpoint=/api/status" in str(err)

    def test_invalid_data_error_creation(self):
        """Test WiiMInvalidDataError creation."""
        err = WiiMInvalidDataError("Malformed response")
        assert str(err) == "Malformed response"


class TestExceptionStringRepresentation:
    """Test exception string representation with context."""

    def test_request_error_string_with_endpoint(self):
        """Test WiiMRequestError string with endpoint."""
        err = WiiMRequestError("Request failed", endpoint="/api/status")
        error_str = str(err)
        assert "Request failed" in error_str
        assert "endpoint=/api/status" in error_str

    def test_request_error_string_with_attempts(self):
        """Test WiiMRequestError string with attempts."""
        err = WiiMRequestError("Request failed", attempts=3)
        error_str = str(err)
        assert "Request failed" in error_str
        assert "attempts=3" in error_str

    def test_request_error_string_with_device_info(self):
        """Test WiiMRequestError string with device info."""
        device_info = {
            "firmware_version": "5.0.1",
            "device_model": "WiiM Pro",
            "is_wiim_device": True,
        }
        err = WiiMRequestError("Request failed", device_info=device_info)
        error_str = str(err)
        assert "Request failed" in error_str
        assert "WiiM" in error_str
        assert "WiiM Pro" in error_str
        assert "fw:5.0.1" in error_str

    def test_request_error_string_with_legacy_device(self):
        """Test WiiMRequestError string with legacy device."""
        device_info = {
            "firmware_version": "4.0.0",
            "device_model": "Audio Pro",
            "is_legacy_device": True,
        }
        err = WiiMRequestError("Request failed", device_info=device_info)
        error_str = str(err)
        assert "Legacy" in error_str
        assert "Audio Pro" in error_str

    def test_request_error_string_with_operation_context(self):
        """Test WiiMRequestError string with operation context."""
        err = WiiMRequestError(
            "Request failed",
            operation_context="protocol_fallback",
        )
        error_str = str(err)
        assert "Request failed" in error_str
        assert "context=protocol_fallback" in error_str

    def test_request_error_string_all_context(self):
        """Test WiiMRequestError string with all context."""
        device_info = {
            "firmware_version": "5.0.1",
            "device_model": "WiiM Pro",
            "is_wiim_device": True,
        }
        err = WiiMRequestError(
            "Request failed",
            endpoint="/api/status",
            attempts=3,
            device_info=device_info,
            operation_context="protocol_fallback",
        )
        error_str = str(err)
        assert "Request failed" in error_str
        assert "endpoint=/api/status" in error_str
        assert "attempts=3" in error_str
        assert "WiiM" in error_str
        assert "context=protocol_fallback" in error_str

    def test_response_error_string_with_endpoint(self):
        """Test WiiMResponseError string with endpoint."""
        err = WiiMResponseError("Invalid JSON", endpoint="/api/status")
        error_str = str(err)
        assert "Invalid JSON" in error_str
        assert "endpoint=/api/status" in error_str

    def test_response_error_string_with_device_info(self):
        """Test WiiMResponseError string with device info."""
        device_info = {
            "firmware_version": "5.0.1",
            "device_model": "WiiM Pro",
            "is_wiim_device": True,
        }
        err = WiiMResponseError("Invalid JSON", device_info=device_info)
        error_str = str(err)
        assert "Invalid JSON" in error_str
        assert "WiiM" in error_str

    def test_base_error_string_simple(self):
        """Test base error string without context."""
        err = WiiMError("Simple error")
        assert str(err) == "Simple error"
