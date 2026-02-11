"""MCP server context: player registry, device resolution, config."""

from __future__ import annotations

import ipaddress
import logging
import time
from dataclasses import dataclass

from ..client import WiiMClient
from ..discovery import DiscoveredDevice, discover_devices
from ..player import Player
from .config import load_config

_LOGGER = logging.getLogger(__name__)

# Discovery cache TTL (seconds)
DISCOVERY_CACHE_TTL = 300  # 5 minutes


def _fuzzy_match_name(query: str, name: str | None) -> bool:
    """Case-insensitive substring match for device names."""
    if not name:
        return False
    return query.lower() in name.lower()


@dataclass
class MCPContext:
    """Shared context for MCP tools: player registry, discovery cache, config."""

    player_registry: dict[str, Player]
    discovery_cache: list[DiscoveredDevice] | None
    discovery_cache_time: float
    default_device: str | None
    named_devices: dict[str, str]  # name -> ip
    discovery_disabled: bool
    timeout: float

    def __init__(self) -> None:
        self.player_registry = {}
        self.discovery_cache = None
        self.discovery_cache_time = 0.0
        cfg = load_config()
        self.default_device = cfg.get("default_device")
        self.named_devices = cfg.get("named_devices") or {}
        self.discovery_disabled = cfg.get("discovery_disabled", False)
        self.timeout = cfg.get("timeout", 5.0)

    def _get_host_key(self, device: DiscoveredDevice) -> str:
        """Get registry key for a device (ip:port for uniqueness)."""
        if device.port and device.port not in (80, 443):
            return f"{device.ip}:{device.port}"
        return device.ip

    def _create_player_from_device(self, device: DiscoveredDevice) -> Player:
        """Create a Player for a discovered device."""
        host_key = self._get_host_key(device)
        if host_key in self.player_registry:
            return self.player_registry[host_key]

        client = WiiMClient(
            host=device.ip,
            port=device.port if device.port not in (80, 443) else None,
            protocol=device.protocol if device.protocol != "http" else None,
            timeout=self.timeout,
        )
        player = Player(
            client,
            player_finder=lambda h: self.player_registry.get(h) or self._find_by_ip(h),
            all_players_finder=lambda: list(self.player_registry.values()),
        )
        self.player_registry[host_key] = player
        return player

    def _create_player_from_ip(self, ip: str) -> Player:
        """Create a Player for a bare IP (client will probe for port/protocol)."""
        if ip in self.player_registry:
            return self.player_registry[ip]

        client = WiiMClient(host=ip, timeout=self.timeout)
        player = Player(
            client,
            player_finder=lambda h: self.player_registry.get(h) or self._find_by_ip(h),
            all_players_finder=lambda: list(self.player_registry.values()),
        )
        self.player_registry[ip] = player
        return player

    def _find_by_ip(self, host: str) -> Player | None:
        """Find player by host (ip or ip:port)."""
        if host in self.player_registry:
            return self.player_registry[host]
        # Try matching by ip only
        for key, player in self.player_registry.items():
            if key.startswith(host) or host.startswith(player.client.host):
                return player
        return None

    async def _ensure_discovery(self, force_refresh: bool = False) -> list[DiscoveredDevice]:
        """Get discovery results, using cache if fresh. When discovery_disabled, returns configured devices."""
        if self.discovery_disabled:
            # Return configured devices as DiscoveredDevice-like objects
            devices = [DiscoveredDevice(ip=ip, name=name, model=None) for name, ip in self.named_devices.items()]
            return devices

        cfg = load_config()
        timeout = cfg.get("discovery_timeout", 5)

        now = time.monotonic()
        if (
            not force_refresh
            and self.discovery_cache is not None
            and (now - self.discovery_cache_time) < DISCOVERY_CACHE_TTL
        ):
            return self.discovery_cache

        devices = await discover_devices(validate=True, ssdp_timeout=timeout)
        self.discovery_cache = devices
        self.discovery_cache_time = now
        return devices

    async def get_player(
        self,
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> Player:
        """Resolve device_name or device_ip to a Player, refresh, and return.

        Raises:
            ValueError: If device cannot be resolved.
        """
        # 1. Explicit IP
        if device_ip:
            player = self._create_player_from_ip(device_ip)
            await player.refresh()
            return player

        # 2. Default device when both omitted
        if not device_name and self.default_device:
            device_name = self.default_device

        if not device_name:
            raise ValueError("device_name or device_ip required (or set WIIM_DEFAULT_DEVICE)")

        # 2b. If device_name looks like an IP, treat as device_ip
        try:
            ipaddress.ip_address(device_name)
            return await self.get_player(device_ip=device_name)
        except ValueError:
            pass  # Not an IP, continue with name resolution

        # 3. Config mapping
        if device_name in self.named_devices:
            return await self.get_player(device_ip=self.named_devices[device_name])

        # 4. Discover and fuzzy match (skip if discovery disabled)
        if self.discovery_disabled:
            available = ", ".join(self.named_devices.keys()) or "none"
            raise ValueError(
                f"Device '{device_name}' not found. Discovery disabled; "
                f"add to config (named_devices) or set WIIM_DISCOVERY_DISABLED=false. "
                f"Configured: {available}"
            )

        devices = await self._ensure_discovery()
        matches = [d for d in devices if _fuzzy_match_name(device_name, d.name)]
        if not matches:
            available = ", ".join(d.name or d.ip for d in devices) or "none"
            raise ValueError(f"Device '{device_name}' not found. Available: {available}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous device '{device_name}': matches {[m.name for m in matches]}")

        device = matches[0]
        player = self._create_player_from_device(device)
        await player.refresh()
        return player

    def invalidate_cache(self) -> None:
        """Clear discovery cache (e.g. on connection error)."""
        self.discovery_cache = None
        self.discovery_cache_time = 0.0
