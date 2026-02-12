"""Integration tests for source catalog output."""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.smoke
@pytest.mark.asyncio
class TestSourceCatalogIntegration:
    """Validate source catalog shape against a real device."""

    async def test_source_catalog_shape(self, real_device_player, integration_test_marker):
        """Catalog exposes expected fields and at least one selectable hardware source."""
        player = real_device_player
        await player.refresh(full=True)

        catalog = player.source_catalog
        assert isinstance(catalog, list)
        assert len(catalog) > 0

        required_keys = {
            "id",
            "name",
            "kind",
            "selectable",
            "is_current",
            "supports_pause",
            "supports_seek",
            "supports_next_track",
            "supports_previous_track",
            "supports_shuffle",
            "supports_repeat",
        }

        for entry in catalog:
            assert required_keys.issubset(set(entry.keys()))

        hardware_entries = [e for e in catalog if e.get("kind") == "hardware_input"]
        assert len(hardware_entries) > 0
        assert any(e.get("selectable") is True for e in hardware_entries)
