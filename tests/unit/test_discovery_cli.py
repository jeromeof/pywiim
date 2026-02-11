"""Tests for discovery CLI output filtering."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pywiim.cli.discovery_cli import main
from pywiim.discovery import DiscoveredDevice


@pytest.mark.asyncio
async def test_discovery_cli_validated_only_filters_unvalidated(capsys):
    """Show only validated devices when --validated-only is used."""
    devices = [
        DiscoveredDevice(ip="192.168.1.100", name="Valid", validated=True, protocol="https", port=443),
        DiscoveredDevice(ip="192.168.1.101", name="Invalid", validated=False, protocol="http", port=80),
    ]

    async_validate = AsyncMock(side_effect=lambda device: device)

    with patch("sys.argv", ["wiim-discover", "--validated-only"]):
        with patch("pywiim.discovery.discover_via_ssdp", return_value=devices):
            with patch("pywiim.discovery.validate_device", async_validate):
                rc = await main()

    output = capsys.readouterr().out
    assert rc == 0
    assert "Total devices: 1" in output
    assert "Validated: 1/1" in output
    assert "Device: Valid" in output
    assert "Device: Invalid" not in output


@pytest.mark.asyncio
async def test_discovery_cli_validated_only_returns_error_when_none_valid(capsys):
    """Return non-zero when filtering leaves no validated devices."""
    devices = [
        DiscoveredDevice(ip="192.168.1.101", name="Invalid", validated=False, protocol="http", port=80),
    ]

    async_validate = AsyncMock(side_effect=lambda device: device)

    with patch("sys.argv", ["wiim-discover", "--validated-only"]):
        with patch("pywiim.discovery.discover_via_ssdp", return_value=devices):
            with patch("pywiim.discovery.validate_device", async_validate):
                rc = await main()

    output = capsys.readouterr().out
    assert rc == 1
    assert "No validated devices found" in output
