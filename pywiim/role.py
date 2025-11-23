"""Framework-agnostic role detection for WiiM/LinkPlay devices.

This module provides role detection logic to determine if a device is acting
as a "master", "slave", or "solo" in a multiroom group. The detection is
firmware-aware and handles both legacy Audio Pro devices and modern WiiM devices.

Role Detection Rules:
- **Master**: Device has at least one slave attached (slave_count > 0)
- **Slave**: Part of a group (group_field != "0") and knows master (master_uuid/master_ip)
- **Solo**: Not in a group (group_field == "0") and no slaves

"""

from __future__ import annotations

import logging
from typing import Any

from .models import DeviceInfo, PlayerStatus

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "detect_role",
    "RoleDetectionResult",
]


class RoleDetectionResult:
    """Result of role detection with additional metadata.

    Attributes:
        role: Detected role ("master", "slave", or "solo")
        master_host: Master IP address (if slave or master)
        master_uuid: Master UUID (if slave or master)
        slave_hosts: List of slave IP addresses (if master)
        slave_count: Number of slaves (if master)
    """

    def __init__(
        self,
        role: str,
        master_host: str | None = None,
        master_uuid: str | None = None,
        slave_hosts: list[str] | None = None,
        slave_count: int = 0,
    ) -> None:
        """Initialize role detection result.

        Args:
            role: Detected role ("master", "slave", or "solo")
            master_host: Master IP address (if slave or master)
            master_uuid: Master UUID (if slave or master)
            slave_hosts: List of slave IP addresses (if master)
            slave_count: Number of slaves (if master)
        """
        self.role = role
        self.master_host = master_host
        self.master_uuid = master_uuid
        self.slave_hosts = slave_hosts or []
        self.slave_count = slave_count


def detect_role(
    status: PlayerStatus,
    multiroom: dict[str, Any],
    device_info: DeviceInfo | None = None,
    capabilities: dict[str, Any] | None = None,
    device_host: str | None = None,
) -> RoleDetectionResult:
    """Detect device role (master/slave/solo) from status and multiroom data.

    This function determines the device's role in a multiroom group based on:
    - Device status (play state, mode)
    - Multiroom information (slave count, slave list)
    - Device info (group field, master UUID/IP)
    - Device capabilities (legacy vs enhanced firmware)

    Args:
        status: Player status from getPlayerStatus or getStatusEx
        multiroom: Multiroom information from getMultiroomStatus or getSlaveList
        device_info: Optional device information (for enhanced detection)
        capabilities: Optional device capabilities (for firmware-aware detection)
        device_host: Optional device hostname/IP (for logging)

    Returns:
        RoleDetectionResult with detected role and metadata

    Example:
        ```python
        from pywiim import WiiMClient, detect_role

        client = WiiMClient("192.168.1.100")
        status = await client.get_player_status_model()
        multiroom = await client.get_multiroom_status()
        device_info = await client.get_device_info_model()
        capabilities = await client._detect_capabilities()

        result = detect_role(status, multiroom, device_info, capabilities, client.host)
        print(f"Role: {result.role}")
        print(f"Slave count: {result.slave_count}")
        ```
    """
    # Determine if legacy device
    is_legacy = False
    if capabilities:
        is_legacy = capabilities.get("is_legacy_device", False)

    # Use appropriate detection method
    if is_legacy:
        return _detect_role_legacy_firmware(status, multiroom, device_info, device_host)
    else:
        return _detect_role_enhanced_firmware(status, multiroom, device_info, device_host)


def _detect_role_legacy_firmware(
    status: PlayerStatus,
    multiroom: dict[str, Any],
    device_info: DeviceInfo | None,
    device_host: str | None,
) -> RoleDetectionResult:
    """Simplified role detection for older Audio Pro units.

    Legacy devices often have unreliable group state, so we use conservative
    detection to avoid false positives.

    Args:
        status: Player status
        multiroom: Multiroom information
        device_info: Device information (optional)
        device_host: Device hostname/IP (for logging)

    Returns:
        RoleDetectionResult with detected role
    """
    # Extract group field and master info
    if device_info:
        group_field = device_info.group or getattr(status, "group", "0") or "0"
        master_uuid = device_info.master_uuid or getattr(status, "master_uuid", None)
        device_name = device_info.name or "Unknown"
    else:
        group_field = getattr(status, "group", "0") or "0"
        master_uuid = getattr(status, "master_uuid", None)
        device_name = getattr(status, "name", "Unknown") or "Unknown"

    # Get slave count from multiroom data
    slaves_data = multiroom.get("slaves", 0)
    slaves_list = multiroom.get("slave_list", [])

    # Handle different data types for slaves field
    if isinstance(slaves_data, list):
        slave_count = len(slaves_data)
        slaves_list = slaves_data
    elif isinstance(slaves_data, int):
        slave_count = slaves_data
    else:
        slave_count = multiroom.get("slave_count", 0)

    # If slaves_list is a number, use it as count
    if isinstance(slaves_list, int):
        slave_count = slaves_list
        slaves_list = []
    elif isinstance(slaves_list, list) and slave_count == 0:
        slave_count = len(slaves_list)

    # Extract slave IPs from slave list
    slave_hosts: list[str] = [
        str(entry.get("ip")) for entry in slaves_list if isinstance(entry, dict) and entry.get("ip") is not None
    ]

    # SLAVE – part of a group (group_field == "1") and knows master
    # Check slave FIRST (before master) to match design guide logic
    if group_field == "1" and master_uuid:
        if device_host:
            _LOGGER.debug(
                "LEGACY ROLE DETECTION: %s (%s) detected as SLAVE",
                device_host,
                device_name,
            )
        return RoleDetectionResult(
            role="slave",
            master_uuid=master_uuid,
            slave_count=0,
        )

    # MASTER – device has at least one slave attached
    # Check master AFTER slave (only if not a slave)
    if slave_count > 0:
        if device_host:
            _LOGGER.debug(
                "LEGACY ROLE DETECTION: %s (%s) is MASTER because slave_count=%s > 0",
                device_host,
                device_name,
                slave_count,
            )
        return RoleDetectionResult(
            role="master",
            master_host=device_host,
            slave_hosts=slave_hosts,
            slave_count=slave_count,
        )

    # SOLO – group_field == "0" and no slaves detected
    if group_field == "0":
        if device_host:
            _LOGGER.debug(
                "LEGACY ROLE DETECTION: %s (%s) detected as SOLO (group='0', slave_count=%s)",
                device_host,
                device_name,
                slave_count,
            )
        return RoleDetectionResult(role="solo")

    # Ambiguous state - treat as solo to avoid breaking controls
    if device_host:
        _LOGGER.warning(
            "LEGACY ROLE DETECTION: %s (%s) has ambiguous group state (group='%s'), treating as SOLO",
            device_host,
            device_name,
            group_field,
        )
    return RoleDetectionResult(role="solo")


def _detect_role_enhanced_firmware(
    status: PlayerStatus,
    multiroom: dict[str, Any],
    device_info: DeviceInfo | None,
    device_host: str | None,
) -> RoleDetectionResult:
    """Enhanced role detection for WiiM devices.

    This detection handles modern WiiM devices with enhanced multiroom features.
    Uses group field as authoritative source (mode=99 can get stuck after leaving group).

    Args:
        status: Player status
        multiroom: Multiroom information
        device_info: Device information (optional)
        device_host: Device hostname/IP (for logging)

    Returns:
        RoleDetectionResult with detected role
    """
    # Extract group field and master info
    if device_info:
        group_field = device_info.group or getattr(status, "group", "0") or "0"
        master_uuid = device_info.master_uuid or getattr(status, "master_uuid", None)
        master_ip = device_info.master_ip or getattr(status, "master_ip", None)
        device_uuid = device_info.uuid or getattr(status, "uuid", None)
        device_name = device_info.name or "Unknown"
    else:
        group_field = getattr(status, "group", "0") or "0"
        master_uuid = getattr(status, "master_uuid", None)
        master_ip = getattr(status, "master_ip", None)
        device_uuid = getattr(status, "uuid", None)
        device_name = getattr(status, "name", "Unknown") or "Unknown"

    # Get slave count from API
    slaves_data = multiroom.get("slaves", 0)
    slaves_list = multiroom.get("slave_list", [])

    # Handle different data types for slaves field
    if isinstance(slaves_data, list):
        slave_count = len(slaves_data)
        slaves_list = slaves_data
    elif isinstance(slaves_data, int):
        slave_count = slaves_data
    else:
        slave_count = multiroom.get("slave_count", 0)

    # If slaves_list is a number, use it as count
    if isinstance(slaves_list, int):
        slave_count = slaves_list
        slaves_list = []
    elif isinstance(slaves_list, list) and slave_count == 0:
        slave_count = len(slaves_list)

    # Extract slave IPs from slave list
    slave_hosts: list[str] = [
        str(entry.get("ip")) for entry in slaves_list if isinstance(entry, dict) and entry.get("ip") is not None
    ]

    if device_host:
        _LOGGER.debug("Role detection inputs for %s:", device_host)
        _LOGGER.debug("  - device_name: '%s'", device_name)
        _LOGGER.debug("  - device_uuid: '%s'", device_uuid)
        _LOGGER.debug("  - group_field: '%s'", group_field)
        _LOGGER.debug(
            "  - slave_count: %s (from multiroom.slaves=%s)",
            slave_count,
            multiroom.get("slaves"),
        )
        _LOGGER.debug("  - slaves_list: %s", slaves_list)
        _LOGGER.debug("  - master_uuid: '%s'", master_uuid)
        _LOGGER.debug("  - master_ip: '%s'", master_ip)

    # SLAVE – part of a group (group_field != "0") and knows master (pointing to another device)
    # Check slave FIRST (before master) to match design guide logic
    # Design guide: Slave = group == "1" and has master_uuid
    # Note: We use group_field != "0" to handle any non-zero group value
    if group_field != "0":
        if master_uuid or master_ip:
            # Check if master info points to this device (then it's the master, not a slave)
            is_master_self = (master_ip and device_host and master_ip == device_host) or (
                master_uuid and device_uuid and master_uuid == device_uuid
            )
            if not is_master_self:
                # Master info points to another device - we're a slave
                if device_host:
                    _LOGGER.debug(
                        "ROLE DETECTION: %s (%s) is SLAVE – group='%s', master uuid/ip present",
                        device_host,
                        device_name,
                        group_field,
                    )
                return RoleDetectionResult(
                    role="slave",
                    master_host=master_ip,
                    master_uuid=master_uuid,
                    slave_count=0,
                )
            # else: master info points to self, continue to check if we have slaves
        # else: no master info, continue to check if we have slaves (might be master)

    # MASTER – device has at least one slave attached
    # Check master AFTER slave (only if not a slave)
    if slave_count > 0:
        if device_host:
            _LOGGER.debug(
                "ROLE DETECTION: %s (%s) is MASTER because slave_count=%s > 0",
                device_host,
                device_name,
                slave_count,
            )
        return RoleDetectionResult(
            role="master",
            master_host=device_host,
            slave_hosts=slave_hosts,
            slave_count=slave_count,
        )

    # Default – SOLO
    if device_host:
        _LOGGER.debug(
            "ROLE DETECTION: %s (%s) is SOLO (group='%s', slave_count=%s)",
            device_host,
            device_name,
            group_field,
            slave_count,
        )
    return RoleDetectionResult(role="solo")
