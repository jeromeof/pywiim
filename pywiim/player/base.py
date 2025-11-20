"""Base Player class - core initialization and properties."""

from __future__ import annotations

import asyncio
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

        # Device role is computed from _group membership (see role property)
        # The Group structure is synced from device API state via refresh()

        # Cached audio output status (updated via refresh())
        self._audio_output_status: dict[str, Any] | None = None

        # Cached EQ presets (updated via refresh())
        self._eq_presets: list[str] | None = None

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

        # Position timer for active updates (for clients displaying media position)
        # Timer triggers callbacks every second while playing so UIs can update smoothly
        # Position estimation is handled by StateSynchronizer, timer just triggers callbacks
        self._position_timer_task: asyncio.Task | None = None
        self._position_timer_interval: float = 1.0  # Update every 1 second
        self._position_timer_running: bool = False
        self._last_timer_position: int | None = None  # Track last position sent to callback

        # Cover art cache (in-memory, keyed by URL hash)
        # Format: {url_hash: (image_bytes, content_type, timestamp)}
        self._cover_art_cache: dict[str, tuple[bytes, str, float]] = {}
        self._cover_art_cache_max_size: int = 10  # Max cached images per player
        self._cover_art_cache_ttl: float = 3600.0  # 1 hour TTL

    @property
    def role(self) -> str:
        """Current role: 'solo', 'master', or 'slave'.

        Role is computed from Group object membership, which is the SINGLE
        source of truth. The Group structure is kept in sync with device state
        via refresh() and updated optimistically during group operations.

        Returns:
            'solo' if not in a group, 'master' if group master with slaves,
            'slave' if in group as slave.
        """
        if self._group is None:
            return "solo"
        elif self._group.master == self:
            # Master with slaves = "master", master with no slaves = "solo"
            return "master" if len(self._group.slaves) > 0 else "solo"
        else:
            return "slave"

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

    # === Position Timer (for active position updates) ===

    async def _position_timer_loop(self) -> None:
        """Background task to update position estimation and trigger callbacks while playing.

        Runs every second while playing to:
        1. Update position estimation in StateSynchronizer (fills in between HTTP polls)
        2. Trigger callbacks so UIs can update their displays smoothly
        """
        while self._position_timer_running:
            try:
                # Update position estimation in StateSynchronizer
                # This "ticks" the position forward based on elapsed time
                current_position = self._state_synchronizer.tick_position_estimation()

                _LOGGER.debug("⏱️  Timer tick: position=%s (last=%s)", current_position, self._last_timer_position)

                if current_position is None:
                    # Not playing anymore - stop timer
                    self._position_timer_running = False
                    break

                # Only trigger callback if position changed by 1+ second
                # This avoids callback spam while still providing smooth updates
                if self._last_timer_position is None or abs(current_position - self._last_timer_position) >= 1:
                    self._last_timer_position = current_position

                    # Trigger callback so UIs can update
                    if self._on_state_changed:
                        _LOGGER.debug("🔔 Triggering callback for position update: %s", current_position)
                        try:
                            self._on_state_changed()
                        except Exception as err:
                            _LOGGER.debug("Error in position timer callback for %s: %s", self.host, err)

                await asyncio.sleep(self._position_timer_interval)

            except asyncio.CancelledError:
                break
            except Exception as err:
                _LOGGER.warning("Error in position timer loop for %s: %s", self.host, err)
                await asyncio.sleep(self._position_timer_interval)

    def _start_position_timer(self) -> None:
        """Start position update timer if playing.

        The timer runs in the background and triggers callbacks every second
        so clients can update their displayed position smoothly.
        """
        if self._position_timer_running:
            _LOGGER.debug("Timer already running, skipping")
            return  # Already running

        # Check if playing (from merged state)
        merged = self._state_synchronizer.get_merged_state()
        play_state = merged.get("play_state")
        is_playing = play_state and str(play_state).lower() in ("play", "playing", "load")

        if not is_playing:
            _LOGGER.info("Not playing, not starting timer")
            return  # Not playing, don't start timer

        # Check if we have a position to report
        position = merged.get("position")

        if position is None:
            _LOGGER.info("No position yet, not starting timer")
            return  # No position yet, wait for first poll/event

        self._position_timer_running = True
        self._last_timer_position = None  # Reset to trigger callback on first update

        try:
            loop = asyncio.get_running_loop()
            self._position_timer_task = loop.create_task(self._position_timer_loop())
        except RuntimeError:
            # No event loop running (sync context) - timer won't work
            # This is OK, callbacks just won't be triggered during playback
            self._position_timer_running = False
            _LOGGER.warning("❌ No event loop available for position timer on %s (sync context)", self.host)

    def _stop_position_timer(self) -> None:
        """Stop position update timer."""
        if not self._position_timer_running:
            return

        self._position_timer_running = False
        if self._position_timer_task:
            self._position_timer_task.cancel()
            self._position_timer_task = None
        self._last_timer_position = None
        _LOGGER.debug("Position timer stopped for %s", self.host)

    async def _cleanup_position_timer(self) -> None:
        """Clean up position timer (async cleanup for proper task cancellation)."""
        if self._position_timer_task:
            self._position_timer_running = False
            self._position_timer_task.cancel()
            try:
                await self._position_timer_task
            except asyncio.CancelledError:
                pass
            self._position_timer_task = None
            _LOGGER.debug("Position timer cleaned up for %s", self.host)
