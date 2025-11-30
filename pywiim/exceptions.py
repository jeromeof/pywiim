"""Exception classes for pywiim library."""


class WiiMError(Exception):
    """Base exception for all WiiM API errors."""


class WiiMRequestError(WiiMError):
    """Raised when there is an error communicating with the WiiM device.

    Enhanced with context for better debugging and user feedback.
    """

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        attempts: int | None = None,
        last_error: Exception | None = None,
        device_info: dict[str, str] | None = None,
        operation_context: str | None = None,
    ) -> None:
        """Initialize request error with enhanced context.

        Args:
            message: The error message
            endpoint: API endpoint that failed
            attempts: Number of retry attempts made
            last_error: The underlying exception that caused this error
            device_info: Device information (firmware, model, etc.)
            operation_context: Context about what operation was being performed
        """
        self.endpoint = endpoint
        self.attempts = attempts
        self.last_error = last_error
        self.device_info = device_info or {}
        self.operation_context = operation_context or "api_call"
        super().__init__(message)

    def __str__(self) -> str:
        """Enhanced string representation with context."""
        context_parts = []

        if self.endpoint:
            context_parts.append(f"endpoint={self.endpoint}")
        if self.attempts:
            context_parts.append(f"attempts={self.attempts}")
        if self.device_info:
            firmware = self.device_info.get("firmware_version", "unknown")
            device_model = self.device_info.get("device_model", "unknown")
            device_type = (
                "WiiM"
                if self.device_info.get("is_wiim_device")
                else "Legacy" if self.device_info.get("is_legacy_device") else "Unknown"
            )

            device_context = f"{device_type} {device_model} (fw:{firmware})"
            context_parts.append(f"device={device_context}")
        if self.operation_context != "api_call":
            context_parts.append(f"context={self.operation_context}")

        if context_parts:
            return f"{super().__str__()} ({', '.join(context_parts)})"
        return super().__str__()


class WiiMResponseError(WiiMError):
    """Raised when the WiiM device returns an error response.

    Enhanced with context for better debugging and user feedback.
    """

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        last_error: Exception | None = None,
        device_info: dict[str, str] | None = None,
    ) -> None:
        """Initialize response error with enhanced context.

        Args:
            message: The error message
            endpoint: API endpoint that failed
            last_error: The underlying exception that caused this error
            device_info: Device information (firmware, model, etc.)
        """
        self.endpoint = endpoint
        self.last_error = last_error
        self.device_info = device_info or {}
        super().__init__(message)

    def __str__(self) -> str:
        """Enhanced string representation with context."""
        context_parts = []
        if self.endpoint:
            context_parts.append(f"endpoint={self.endpoint}")
        if self.device_info:
            firmware = self.device_info.get("firmware_version", "unknown")
            device_model = self.device_info.get("device_model", "unknown")
            device_type = (
                "WiiM"
                if self.device_info.get("is_wiim_device")
                else "Legacy" if self.device_info.get("is_legacy_device") else "Unknown"
            )
            device_context = f"{device_type} {device_model} (fw:{firmware})"
            context_parts.append(f"device={device_context}")
        if context_parts:
            return f"{super().__str__()} ({', '.join(context_parts)})"
        return super().__str__()


class WiiMTimeoutError(WiiMRequestError):
    """Raised when a request to the WiiM device times out.

    Enhanced with context for better debugging and user feedback.
    """


class WiiMConnectionError(WiiMRequestError):
    """Raised on network-level connectivity problems (SSL, unreachable, …).

    Enhanced with context for better debugging and user feedback.
    """


class WiiMInvalidDataError(WiiMError):
    """The device responded with malformed or non-JSON data."""


class WiiMGroupCompatibilityError(WiiMError):
    """Raised when attempting to group devices with incompatible multiroom protocol versions.

    Devices can only group with matching major wmrm_version:
    - wmrm_version 2.x: Legacy LinkPlay protocol (older devices, Audio Pro Gen 1)
    - wmrm_version 4.x: Current router-based multiroom protocol (WiiM, Audio Pro Gen 2+/W-Gen)

    This is a protocol-level requirement - devices with different major versions cannot join groups together.
    Minor version differences (e.g., 4.2 vs 4.3) are compatible.
    """

    def __init__(
        self,
        slave_version: str | None,
        master_version: str | None,
        slave_model: str | None = None,
        master_model: str | None = None,
    ) -> None:
        """Initialize group compatibility error.

        Args:
            slave_version: WMRM version of the slave device attempting to join.
            master_version: WMRM version of the master device.
            slave_model: Optional model name of the slave device.
            master_model: Optional model name of the master device.
        """
        self.slave_version = slave_version
        self.master_version = master_version
        self.slave_model = slave_model
        self.master_model = master_model

        # Build user-friendly error message
        slave_info = f"{slave_model} " if slave_model else ""
        master_info = f"{master_model} " if master_model else ""
        slave_ver_str = slave_version or "unknown"
        master_ver_str = master_version or "unknown"

        message = (
            f"Cannot group devices with incompatible multiroom protocol versions: "
            f"{slave_info}(wmrm_version={slave_ver_str}) cannot join "
            f"{master_info}(wmrm_version={master_ver_str}). "
            f"Devices can only group with matching major wmrm_version. "
            f"Audio Pro Gen1 devices (wmrm_version 2.x) can only group with other Gen1 devices. "
            f"WiiM and Audio Pro Gen2+ devices (wmrm_version 4.x) can only group with other Gen2+ devices."
        )

        super().__init__(message)
