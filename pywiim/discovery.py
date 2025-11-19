"""Device discovery for WiiM and LinkPlay devices.

This module provides SSDP/UPnP discovery to find WiiM and LinkPlay devices
on the local network (matches HA integration behavior).
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
from dataclasses import dataclass
from typing import Any

try:
    from async_upnp_client.search import async_search
except ImportError:
    async_search = None  # type: ignore[assignment]

from .client import WiiMClient

_LOGGER = logging.getLogger(__name__)

__all__ = [
    "DiscoveredDevice",
    "discover_devices",
    "discover_via_ssdp",
    "validate_device",
]

# Known non-LinkPlay server patterns (ONLY devices we're CERTAIN are not LinkPlay)
# These patterns are specific to non-LinkPlay devices that clearly identify themselves
# ⚠️ CONSERVATIVE: Only filter devices we're 100% certain are not LinkPlay.
# Audio Pro, Arylic, and other LinkPlay devices use generic "Linux" headers
# and will pass through this filter (which is correct - they need validation).
NON_LINKPLAY_SERVER_PATTERNS = [
    "Chromecast",  # Google Chromecast - definitely not LinkPlay
    "Denon-Heos",  # Denon Heos - definitely not LinkPlay
    "MINT-X",  # Sony devices - definitely not LinkPlay
    "KnOS",  # Kodi/OSMC - definitely not LinkPlay
    # Add more ONLY if we're 100% certain they're not LinkPlay-compatible
    # DO NOT add generic patterns like "Linux" - Audio Pro uses this!
]


@dataclass
class DiscoveredDevice:
    """Represents a discovered WiiM/LinkPlay device."""

    ip: str
    name: str | None = None
    model: str | None = None
    firmware: str | None = None
    mac: str | None = None
    uuid: str | None = None
    port: int = 80
    protocol: str = "http"  # "http" or "https"
    vendor: str | None = None  # "wiim", "arylic", "audio_pro", etc.
    discovery_method: str = "unknown"  # "ssdp", "manual"
    validated: bool = False  # Whether device was validated via API
    ssdp_response: dict[str, Any] | None = None  # Store SSDP response for filtering

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ip": self.ip,
            "name": self.name,
            "model": self.model,
            "firmware": self.firmware,
            "mac": self.mac,
            "uuid": self.uuid,
            "port": self.port,
            "protocol": self.protocol,
            "vendor": self.vendor,
            "discovery_method": self.discovery_method,
            "validated": self.validated,
        }

    def __str__(self) -> str:
        """String representation."""
        name = self.name or "Unknown"
        model = f" ({self.model})" if self.model else ""
        return f"{name}{model} @ {self.ip}"


async def discover_via_ssdp(
    timeout: int = 5,
    target: str | None = None,
) -> list[DiscoveredDevice]:
    """Discover devices via SSDP/UPnP.

    Args:
        timeout: Discovery timeout in seconds
        target: Optional SSDP search target (default: "upnp:rootdevice")

    Returns:
        List of discovered devices
    """
    if async_search is None:
        _LOGGER.warning(
            "async-upnp-client not available, SSDP discovery disabled. " "Install with: pip install async-upnp-client"
        )
        return []

    devices: list[DiscoveredDevice] = []
    seen_ips: set[str] = set()

    try:
        _LOGGER.info("Starting SSDP discovery (timeout=%ds)...", timeout)
        # HA integration uses "upnp:rootdevice" as the search target
        search_target = target or "upnp:rootdevice"

        # New API requires async_callback instead of async generator
        async def process_response(response: dict[str, Any]) -> None:
            """Process a single SSDP response (matches HA integration pattern)."""
            try:
                _LOGGER.debug(
                    "SSDP response received, keys: %s",
                    list(response.keys()) if hasattr(response, "keys") else "no keys",
                )

                # Extract location URL (CaseInsensitiveDict handles case)
                # Try multiple key variations
                location = (
                    response.get("location", "")
                    or response.get("LOCATION", "")
                    or response.get("_location_original", "")
                )
                _LOGGER.debug("Extracted location: %s", location)

                if not location:
                    _LOGGER.debug(
                        "No location in SSDP response, skipping. Response keys: %s",
                        list(response.keys()) if hasattr(response, "keys") else "unknown",
                    )
                    return

                # Parse IP from location URL
                ip = _extract_ip_from_url(location)
                _LOGGER.debug("Extracted IP: %s from location: %s", ip, location)

                if not ip:
                    _LOGGER.debug("Could not extract IP from location: %s", location)
                    return

                if ip in seen_ips:
                    _LOGGER.debug("Already seen IP: %s, skipping", ip)
                    return

                _LOGGER.debug("Processing new device with IP: %s", ip)
                seen_ips.add(ip)

                # Extract port and protocol from UPnP description URL
                # NOTE: This port (typically 49152) is ONLY for UPnP description.xml, NOT for HTTP API
                # The HTTP API is always on port 80 (or 443 for HTTPS)
                upnp_port, protocol = _extract_port_and_protocol(location)

                # Extract device info from SSDP response
                usn = response.get("usn", "") or response.get("USN", "")
                name = None
                if usn:
                    name = usn.split("::")[0]
                    if name and name.startswith("uuid:"):
                        name = None

                # Extract UUID from USN if present (format: uuid:xxxx-xxxx-xxxx-xxxx::...)
                uuid = None
                if usn.startswith("uuid:"):
                    uuid_part = usn.split("::")[0]
                    if uuid_part.startswith("uuid:"):
                        uuid = uuid_part[5:]

                # Accept all SSDP responses - validation will filter LinkPlay devices
                # This matches HA integration behavior
                # IMPORTANT: Use port 80 for HTTP API (not the UPnP description port)
                # The UPnP port (49152) is only for description.xml, not for API calls
                api_port = 80  # HTTP API is always on port 80 (or 443 for HTTPS)
                device = DiscoveredDevice(
                    ip=ip,
                    name=name,
                    model=None,  # Will be filled during validation
                    uuid=uuid,
                    port=api_port,  # Use standard HTTP API port, not UPnP port
                    protocol=protocol,
                    discovery_method="ssdp",
                    ssdp_response=response,  # Store full SSDP response for filtering
                )

                devices.append(device)
                _LOGGER.debug(
                    "SSDP discovered device: %s @ %s (UPnP port: %d, API port: %d)",
                    device.name or "Unknown",
                    ip,
                    upnp_port,
                    api_port,
                )

            except Exception as e:
                _LOGGER.warning("Error processing SSDP response: %s", e, exc_info=True)

        # Use new callback-based API (matches HA integration)
        # Note: async_search expects CaseInsensitiveDict but we use dict[str, Any]
        # This is compatible at runtime, so we suppress the type check
        if async_search is None:
            raise RuntimeError("async_upnp_client.search.async_search is not available")
        # Type ignore needed: async_search expects CaseInsensitiveDict but dict[str, Any] is compatible
        await async_search(
            async_callback=process_response,  # type: ignore[arg-type]
            timeout=timeout,
            search_target=search_target,
        )

    except Exception as e:
        _LOGGER.warning("SSDP discovery failed: %s", e)

    _LOGGER.info("SSDP discovery found %d device(s)", len(devices))
    return devices


async def validate_device(device: DiscoveredDevice) -> DiscoveredDevice:
    """Validate a discovered device by querying its API.

    Args:
        device: Device to validate

    Returns:
        Updated device with full information
    """
    if device.validated:
        return device

    try:
        # Use discovered protocol to set initial protocol priority
        # This ensures we try the discovered protocol first (e.g., HTTP for port 49152)
        capabilities = {}
        if device.protocol:
            # Set protocol priority based on discovered protocol
            if device.protocol == "https":
                capabilities["protocol_priority"] = ["https", "http"]
            else:
                capabilities["protocol_priority"] = ["http", "https"]

        # Device port should already be 80 (set during discovery)
        # Port 49152 is only for UPnP description.xml, not for HTTP API
        client = WiiMClient(
            device.ip,
            port=device.port,  # Should be 80 for HTTP API
            timeout=5.0,
            capabilities=capabilities,
        )

        try:
            # Ensure capabilities are detected (triggers vendor detection)
            await client._detect_capabilities()

            # Get device info
            device_info = await client.get_device_info_model()
            await client.get_player_status()  # Refresh player status

            # Update device with full info
            device.name = device_info.name or device.name
            device.model = device_info.model or device.model
            device.firmware = device_info.firmware or device.firmware
            device.mac = device_info.mac or device.mac
            device.uuid = device_info.uuid or device.uuid

            # Update port to the actual API port (may differ from discovered UPnP port)
            device.port = client.port

            # Detect vendor from capabilities (normalized)
            # Capabilities are now guaranteed to be detected
            from .capabilities import detect_vendor
            from .normalize import normalize_vendor

            if client.capabilities and client.capabilities.get("vendor"):
                vendor = client.capabilities.get("vendor")
                device.vendor = normalize_vendor(vendor)
            else:
                # Fallback: detect vendor from device info
                vendor = detect_vendor(device_info)
                device.vendor = normalize_vendor(vendor)

            device.validated = True

            await client.close()

        except Exception as e:
            await client.close()
            _LOGGER.debug("Validation failed for %s: %s", device.ip, e)

    except Exception as e:
        _LOGGER.debug("Could not validate device %s: %s", device.ip, e)

    return device


async def discover_devices(
    methods: list[str] | None = None,
    validate: bool = True,
    ssdp_timeout: int = 5,
) -> list[DiscoveredDevice]:
    """Discover WiiM/LinkPlay devices via SSDP/UPnP (like HA integration).

    Args:
        methods: Discovery methods to use (default: ["ssdp"])
            Only "ssdp" is supported (network scanning removed to match HA integration)
        validate: Whether to validate discovered devices via API
        ssdp_timeout: SSDP discovery timeout in seconds

    Returns:
        List of discovered and validated devices
    """
    if methods is None:
        methods = ["ssdp"]

    all_devices: list[DiscoveredDevice] = []
    seen_ips: set[str] = set()

    # SSDP discovery (only method, like HA integration)
    if "ssdp" in methods:
        _LOGGER.info("Discovering devices via SSDP...")
        ssdp_devices = await discover_via_ssdp(timeout=ssdp_timeout)

        # Quick filter: Skip known non-LinkPlay devices before validation
        # ⚠️ CONSERVATIVE: Only filters devices we're 100% certain are not LinkPlay
        devices_to_validate = []
        for device in ssdp_devices:
            if device.ip in seen_ips:
                continue

            # Apply quick filter if SSDP response is available
            if device.ssdp_response and is_likely_non_linkplay(device.ssdp_response):
                _LOGGER.debug(
                    "Skipping known non-LinkPlay device: %s (SERVER: %s)",
                    device.ip,
                    device.ssdp_response.get("SERVER", device.ssdp_response.get("server", "unknown")),
                )
                continue

            # Device passes filter - will be validated (Audio Pro, Arylic, WiiM, etc.)
            devices_to_validate.append(device)
            seen_ips.add(device.ip)

        all_devices = devices_to_validate

    # Validate devices if requested
    # This is critical: validation determines if devices are actually LinkPlay/WiiM
    # by checking if they respond to the LinkPlay API
    if validate:
        _LOGGER.info("Validating %d discovered device(s) to confirm LinkPlay/WiiM compatibility...", len(all_devices))
        validation_tasks = [validate_device(device) for device in all_devices]
        validated_devices = await asyncio.gather(*validation_tasks)

        # Filter to only include devices that successfully validated
        # (devices that respond to LinkPlay API)
        all_devices = [device for device in validated_devices if device.validated]

        if len(validated_devices) != len(all_devices):
            _LOGGER.info(
                "Filtered out %d non-LinkPlay device(s) (did not respond to LinkPlay API)",
                len(validated_devices) - len(all_devices),
            )

    # Remove duplicates (by IP)
    unique_devices: list[DiscoveredDevice] = []
    seen_ips_again: set[str] = set()
    for device in all_devices:
        if device.ip not in seen_ips_again:
            unique_devices.append(device)
            seen_ips_again.add(device.ip)

    _LOGGER.info("Discovery complete: found %d unique device(s)", len(unique_devices))
    return unique_devices


def _extract_ip_from_url(url: str) -> str | None:
    """Extract IP address from URL."""
    try:
        # Remove protocol
        if "://" in url:
            url = url.split("://", 1)[1]

        # Remove path
        if "/" in url:
            url = url.split("/", 1)[0]

        # Remove port
        if ":" in url:
            url = url.split(":")[0]

        # Validate IP
        ipaddress.ip_address(url)
        return url
    except Exception:
        return None


def _extract_port_and_protocol(url: str) -> tuple[int, str]:
    """Extract port and protocol from URL."""
    protocol = "https" if url.startswith("https://") else "http"
    default_port = 443 if protocol == "https" else 80

    try:
        # Remove protocol
        if "://" in url:
            url = url.split("://", 1)[1]

        # Extract port
        if ":" in url:
            port_str = url.split(":")[1].split("/")[0]
            port = int(port_str)
            return port, protocol
    except Exception:
        pass

    return default_port, protocol


def is_likely_non_linkplay(ssdp_response: dict[str, Any]) -> bool:
    """Quick check if device is likely not a LinkPlay device based on SSDP headers.

    ⚠️ CONSERVATIVE: Only filters devices we're 100% certain are not LinkPlay.
    Audio Pro, Arylic, and other LinkPlay devices use generic "Linux" headers
    and will pass through this filter (which is correct - they need validation).

    Args:
        ssdp_response: SSDP response dictionary containing headers

    Returns:
        True if device is CERTAINLY not a LinkPlay device, False otherwise
    """
    server = ssdp_response.get("SERVER", "") or ssdp_response.get("server", "")
    if not server:
        return False  # No SERVER header - can't filter, must validate

    server_upper = server.upper()
    return any(pattern.upper() in server_upper for pattern in NON_LINKPLAY_SERVER_PATTERNS)
