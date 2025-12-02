"""Base Player class - core initialization and properties."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from ..client import WiiMClient
from ..models import DeviceInfo, PlayerStatus
from ..state import StateSynchronizer

if TYPE_CHECKING:
    from ..group import Group
    from ..upnp.client import UpnpClient
    from ..upnp.health import UpnpHealthTracker
else:
    Group = None
    UpnpHealthTracker = None

_LOGGER = logging.getLogger(__name__)


class PlayerBase:
    """Base player with core state and initialization."""

    def __init__(
        self,
        client: WiiMClient,
        upnp_client: UpnpClient | None = None,
        on_state_changed: Callable[[], None] | None = None,
        player_finder: Callable[[str], Any] | None = None,
    ) -> None:
        """Initialize a Player instance.

        Args:
            client: WiiMClient instance for this device.
            upnp_client: Optional UPnP client for queue management and events.
            on_state_changed: Optional callback function called when state is updated.
            player_finder: Optional callback to find Player objects by host/IP.
                Called as `player_finder(host)` and should return Player | None.
                Used to automatically link Player objects when groups are detected.
        """
        self.client = client
        self._upnp_client = upnp_client
        self._group: Group | None = None

        # State management
        self._state_synchronizer = StateSynchronizer()
        self._on_state_changed = on_state_changed
        self._player_finder = player_finder

        # Cached state (updated via refresh())
        self._status_model: PlayerStatus | None = None
        self._device_info: DeviceInfo | None = None
        self._last_refresh: float | None = None

        # Device role from device API state (single source of truth)
        # Updated during refresh() from get_device_group_info()
        # Independent of Group objects (which are for linking Player objects)
        self._detected_role: str = "solo"  # Default to solo until detected

        # Cached audio output status (updated via refresh())
        self._audio_output_status: dict[str, Any] | None = None
        self._last_audio_output_check: float = 0  # Track when audio output status was last fetched

        # Cached EQ presets (updated via refresh())
        self._eq_presets: list[str] | None = None
        self._last_eq_presets_check: float = 0  # Track when EQ presets were last fetched

        # Cached preset stations (playback presets - updated via refresh())
        self._presets: list[dict[str, Any]] | None = None
        self._last_presets_check: float = 0  # Track when presets were last fetched

        # Cached metadata (audio quality info - updated via refresh())
        self._metadata: dict[str, Any] | None = None

        # Cached Bluetooth history (updated via refresh() every 60 seconds)
        self._bluetooth_history: list[dict[str, Any]] = []
        self._last_bt_history_check: float = 0

        # UPnP health tracking (only if UPnP client is provided)
        self._upnp_health_tracker: UpnpHealthTracker | None = None
        if upnp_client is not None:
            from ..upnp.health import UpnpHealthTracker

            self._upnp_health_tracker = UpnpHealthTracker()

        # Availability tracking
        self._available: bool = True  # Assume available until proven otherwise

        # Last played URL tracking (for media_title fallback)
        self._last_played_url: str | None = None

        # Cover art cache (in-memory, keyed by URL hash)
        # Format: {url_hash: (image_bytes, content_type, timestamp)}
        self._cover_art_cache: dict[str, tuple[bytes, str, float]] = {}
        self._cover_art_cache_max_size: int = 10  # Max cached images per player
        self._cover_art_cache_ttl: float = 3600.0  # 1 hour TTL

    @property
    def role(self) -> str:
        """Current role: 'solo', 'master', or 'slave'.

        Role comes from device API state via get_device_group_info(), cached in
        _detected_role. This is the SINGLE source of truth, independent of Group
        objects (which are for linking Player objects in coordinators like HA).

        Returns:
            'solo' if not in a group, 'master' if group master with slaves,
            'slave' if in group as slave.
        """
        return self._detected_role

    @property
    def is_solo(self) -> bool:
        """True if this player is not in a group (or is master with no slaves)."""
        return self.role == "solo"

    @property
    def is_master(self) -> bool:
        """True if this player is the master of a group with slaves."""
        return self.role == "master"

    @property
    def is_slave(self) -> bool:
        """True if this player is a slave in a group."""
        return self.role == "slave"

    @property
    def group(self) -> Group | None:
        """Group this player belongs to, or None if solo."""
        return self._group

    @property
    def host(self) -> str:
        """Device hostname or IP address."""
        return self.client.host

    @property
    def port(self) -> int:
        """Device port number."""
        return self.client.port

    @property
    def timeout(self) -> float:
        """Network timeout in seconds."""
        return self.client.timeout

    @property
    def name(self) -> str | None:
        """Device name from cached device_info."""
        if self._device_info:
            return self._device_info.name
        return None

    @property
    def model(self) -> str | None:
        """Device model from cached device_info."""
        if self._device_info:
            return self._device_info.model
        return None

    @property
    def firmware(self) -> str | None:
        """Firmware version from cached device_info."""
        if self._device_info:
            return self._device_info.firmware
        return None

    @property
    def mac_address(self) -> str | None:
        """MAC address from cached device_info."""
        if self._device_info:
            return self._device_info.mac
        return None

    @property
    def uuid(self) -> str | None:
        """Device UUID from cached device_info."""
        if self._device_info:
            return self._device_info.uuid
        return None

    @property
    def available(self) -> bool:
        """Device availability status."""
        return self._available

    @property
    def status_model(self) -> PlayerStatus | None:
        """Cached PlayerStatus model (None if not refreshed yet)."""
        return self._status_model

    @property
    def device_info(self) -> DeviceInfo | None:
        """Cached DeviceInfo model (None if not refreshed yet)."""
        return self._device_info

    def __repr__(self) -> str:
        """String representation."""
        role = self.role
        return f"Player(host={self.host!r}, role={role!r})"
