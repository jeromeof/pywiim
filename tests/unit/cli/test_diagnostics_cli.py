"""Unit tests for diagnostics CLI helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pywiim.cli.diagnostics import DeviceDiagnostics


class DummyClient:
    """Minimal client stub for diagnostics tests."""

    def __init__(self) -> None:
        self.host = "192.168.1.100"
        self.port = 80
        self._capabilities_detected = True
        self._detect_capabilities = AsyncMock()
        self.capabilities = {
            "vendor": "wiim",
            "is_wiim_device": True,
            "upnp_description_available": True,
            "upnp_model_name": "WiiM Pro Receiver",
            "upnp_friendly_name": "Living Room",
            "upnp_has_playqueue": True,
            "upnp_has_qplay": True,
            "upnp_has_content_directory": True,
        }


@pytest.mark.asyncio
async def test_gather_capabilities_prints_upnp_description_enrichment(capsys):
    """Diagnostics output shows UPnP description.xml enrichment details."""
    diagnostics = DeviceDiagnostics(DummyClient())  # type: ignore[arg-type]

    await diagnostics._gather_capabilities()
    output = capsys.readouterr().out

    assert "UPnP model: WiiM Pro Receiver" in output
    assert "UPnP friendly name: Living Room" in output
    assert "UPnP advertised services: PlayQueue, QPlay, ContentDirectory" in output
    assert diagnostics.report["capabilities"]["upnp_description_available"] is True
