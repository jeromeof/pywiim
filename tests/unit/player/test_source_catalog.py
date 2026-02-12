"""Tests for Player.source_catalog."""

from __future__ import annotations

import pytest

from pywiim.models import DeviceInfo, PlayerStatus


def _get_entry(catalog: list[dict[str, object]], source_id: str) -> dict[str, object]:
    """Find one source catalog entry by ID."""
    for entry in catalog:
        if entry.get("id") == source_id:
            return entry
    raise AssertionError(f"Source '{source_id}' not found in catalog: {catalog}")


class TestSourceCatalog:
    """Validate normalized source catalog behavior."""

    @pytest.mark.asyncio
    async def test_source_catalog_empty_without_device_info(self, mock_client):
        """Catalog is empty when device info has not been fetched yet."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = None

        assert player.source_catalog == []

    @pytest.mark.asyncio
    async def test_source_catalog_includes_hardware_and_known_services(self, mock_client):
        """Catalog includes selectable hardware plus non-selectable services."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = DeviceInfo(uuid="test", input_list=["wifi", "bluetooth", "line_in"])
        player._status_model = PlayerStatus(source="spotify", play_state="play")

        catalog = player.source_catalog

        network = _get_entry(catalog, "network")
        assert network["name"] == "Network"
        assert network["kind"] == "hardware_input"
        assert network["selectable"] is True

        bluetooth = _get_entry(catalog, "bluetooth")
        assert bluetooth["kind"] == "hardware_input"
        assert bluetooth["selectable"] is True

        spotify = _get_entry(catalog, "spotify")
        assert spotify["kind"] == "service"
        assert spotify["selectable"] is False
        assert spotify["is_current"] is True
        assert spotify["supports_shuffle"] is True
        assert spotify["supports_repeat"] is True
        assert spotify["supports_next_track"] is True
        assert spotify["supports_seek"] is True

        # Known services are included even when not active.
        airplay = _get_entry(catalog, "airplay")
        assert airplay["kind"] == "service"
        assert airplay["selectable"] is False
        assert airplay["is_current"] is False

    @pytest.mark.asyncio
    async def test_source_catalog_capability_flags_for_source_types(self, mock_client):
        """Capability flags match source behavior model."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = DeviceInfo(uuid="test", input_list=["wifi", "line_in"])
        player._status_model = PlayerStatus(source="airplay", play_state="play")

        catalog = player.source_catalog

        line_in = _get_entry(catalog, "line_in")
        assert line_in["supports_pause"] is False
        assert line_in["supports_seek"] is False
        assert line_in["supports_next_track"] is False
        assert line_in["supports_shuffle"] is False

        airplay = _get_entry(catalog, "airplay")
        assert airplay["supports_pause"] is True
        assert airplay["supports_seek"] is True
        assert airplay["supports_next_track"] is True
        assert airplay["supports_shuffle"] is False
        assert airplay["supports_repeat"] is False

    @pytest.mark.asyncio
    async def test_source_catalog_handles_virtual_current_source(self, mock_client):
        """Non-standard current source is represented as virtual and conservative."""
        from pywiim.player import Player

        player = Player(mock_client)
        player._device_info = DeviceInfo(uuid="test", input_list=["wifi", "bluetooth", "line_in"])
        player._status_model = PlayerStatus(source="Master Bedroom", play_state="play")

        catalog = player.source_catalog
        virtual = _get_entry(catalog, "master_bedroom")

        assert virtual["name"] == "Master Bedroom"
        assert virtual["kind"] == "virtual"
        assert virtual["selectable"] is False
        assert virtual["is_current"] is True
        assert virtual["supports_pause"] is False
        assert virtual["supports_seek"] is False
        assert virtual["supports_next_track"] is False
        assert virtual["supports_shuffle"] is False
