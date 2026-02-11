"""Unit tests for MCP server tools."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pywiim.discovery import DiscoveredDevice
from pywiim.mcp.config import load_config
from pywiim.mcp.context import MCPContext


class TestLoadConfig:
    """Test config loading from file and env."""

    def test_load_config_from_file(self):
        """Config file values are loaded."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "default_device": "192.168.1.100",
                    "named_devices": {"Living Room": "192.168.1.100"},
                    "discovery_disabled": True,
                    "timeout": 10.0,
                },
                f,
            )
            path = f.name

        try:
            with patch.dict("os.environ", {"WIIM_CONFIG_FILE": path}, clear=False):
                cfg = load_config()
            assert cfg["default_device"] == "192.168.1.100"
            assert cfg["named_devices"] == {"Living Room": "192.168.1.100"}
            assert cfg["discovery_disabled"] is True
            assert cfg["timeout"] == 10.0
        finally:
            Path(path).unlink(missing_ok=True)

    def test_env_overrides_file(self):
        """Env vars override config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"default_device": "192.168.1.100", "named_devices": {}}, f)
            path = f.name

        try:
            with patch.dict(
                "os.environ",
                {"WIIM_CONFIG_FILE": path, "WIIM_DEFAULT_DEVICE": "192.168.1.101"},
                clear=False,
            ):
                cfg = load_config()
            assert cfg["default_device"] == "192.168.1.101"
        finally:
            Path(path).unlink(missing_ok=True)

    def test_discovery_disabled_env(self):
        """WIIM_DISCOVERY_DISABLED env parsed correctly."""
        with patch.dict("os.environ", {"WIIM_DISCOVERY_DISABLED": "true"}, clear=False):
            cfg = load_config()
        assert cfg.get("discovery_disabled") is True


class TestMCPContext:
    """Test MCPContext device resolution and player registry."""

    @pytest.mark.asyncio
    async def test_get_player_by_ip_creates_player(self):
        """get_player with device_ip creates player from IP."""
        ctx = MCPContext()
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch("pywiim.mcp.context.WiiMClient") as mock_client_cls:
            with patch("pywiim.mcp.context.Player", return_value=mock_player):
                player = await ctx.get_player(device_ip="192.168.1.100")
                assert player is mock_player
                mock_player.refresh.assert_called_once()
                mock_client_cls.assert_called_once_with(host="192.168.1.100", timeout=ctx.timeout)

    @pytest.mark.asyncio
    async def test_get_player_by_ip_reuses_cached(self):
        """get_player with device_ip reuses cached player."""
        ctx = MCPContext()
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch("pywiim.mcp.context.WiiMClient"):
            with patch("pywiim.mcp.context.Player", return_value=mock_player):
                p1 = await ctx.get_player(device_ip="192.168.1.100")
                p2 = await ctx.get_player(device_ip="192.168.1.100")
                assert p1 is p2
                assert p1.refresh.call_count == 2

    @pytest.mark.asyncio
    async def test_get_player_requires_device_param(self):
        """get_player raises when neither device_name nor device_ip provided."""
        ctx = MCPContext()
        ctx.default_device = None

        with pytest.raises(ValueError, match="device_name or device_ip required"):
            await ctx.get_player()

    @pytest.mark.asyncio
    async def test_get_player_uses_default_device(self):
        """get_player uses WIIM_DEFAULT_DEVICE when device params omitted."""
        ctx = MCPContext()
        ctx.default_device = "192.168.1.100"
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch("pywiim.mcp.context.WiiMClient"):
            with patch("pywiim.mcp.context.Player", return_value=mock_player):
                player = await ctx.get_player()
                assert player is mock_player

    @pytest.mark.asyncio
    async def test_get_player_uses_named_devices_config(self):
        """get_player resolves device_name via WIIM_NAMED_DEVICES map."""
        ctx = MCPContext()
        ctx.named_devices = {"Living Room": "192.168.1.100"}
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch("pywiim.mcp.context.WiiMClient"):
            with patch("pywiim.mcp.context.Player", return_value=mock_player):
                player = await ctx.get_player(device_name="Living Room")
                assert player is mock_player

    @pytest.mark.asyncio
    async def test_get_player_resolves_by_discovery_fuzzy_match(self):
        """get_player resolves device_name via discovery + fuzzy match."""
        ctx = MCPContext()
        ctx.default_device = None
        ctx.named_devices = {}
        ctx.discovery_disabled = False
        devices = [
            DiscoveredDevice(ip="192.168.1.100", name="Living Room", model="WiiM Pro"),
        ]
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch.object(ctx, "_ensure_discovery", AsyncMock(return_value=devices)):
            with patch("pywiim.mcp.context.WiiMClient"):
                with patch("pywiim.mcp.context.Player", return_value=mock_player):
                    player = await ctx.get_player(device_name="Living Room")
                    assert player is mock_player

    @pytest.mark.asyncio
    async def test_get_player_rejects_unknown_device_name(self):
        """get_player raises when device_name not found in discovery."""
        ctx = MCPContext()
        ctx.default_device = None
        ctx.named_devices = {}
        ctx.discovery_disabled = False
        devices = [
            DiscoveredDevice(ip="192.168.1.100", name="Living Room", model="WiiM Pro"),
        ]

        with patch.object(ctx, "_ensure_discovery", AsyncMock(return_value=devices)):
            with pytest.raises(ValueError, match="Device 'Kitchen' not found"):
                await ctx.get_player(device_name="Kitchen")


class TestMCPContextFuzzyMatch:
    """Test fuzzy matching for device names."""

    @pytest.mark.asyncio
    async def test_fuzzy_match_substring(self):
        """'living' matches 'Living Room'."""
        ctx = MCPContext()
        ctx.default_device = None
        ctx.named_devices = {}
        ctx.discovery_disabled = False
        devices = [
            DiscoveredDevice(ip="192.168.1.100", name="Living Room", model="WiiM Pro"),
        ]
        mock_player = MagicMock()
        mock_player.refresh = AsyncMock()

        with patch.object(ctx, "_ensure_discovery", AsyncMock(return_value=devices)):
            with patch("pywiim.mcp.context.WiiMClient"):
                with patch("pywiim.mcp.context.Player", return_value=mock_player):
                    player = await ctx.get_player(device_name="living")
                    assert player is mock_player


class TestMCPContextDiscoveryDisabled:
    """Test discovery_disabled behavior."""

    @pytest.mark.asyncio
    async def test_get_player_raises_when_discovery_disabled_and_not_configured(self):
        """When discovery_disabled and device not in named_devices, raise helpful error."""
        ctx = MCPContext()
        ctx.default_device = None
        ctx.named_devices = {"Living Room": "192.168.1.100"}
        ctx.discovery_disabled = True

        with pytest.raises(ValueError, match="Discovery disabled"):
            await ctx.get_player(device_name="Kitchen")

    @pytest.mark.asyncio
    async def test_ensure_discovery_returns_configured_when_disabled(self):
        """_ensure_discovery returns configured devices when discovery_disabled."""
        ctx = MCPContext()
        ctx.named_devices = {"Living Room": "192.168.1.100", "Bedroom": "192.168.1.101"}
        ctx.discovery_disabled = True

        devices = await ctx._ensure_discovery()
        assert len(devices) == 2
        ips = {d.ip for d in devices}
        assert ips == {"192.168.1.100", "192.168.1.101"}


class TestMCPContextDiscoveryCache:
    """Test discovery cache behavior."""

    @pytest.mark.asyncio
    async def test_ensure_discovery_caches_results(self):
        """_ensure_discovery caches results."""
        ctx = MCPContext()
        ctx.discovery_disabled = False
        devices = [
            DiscoveredDevice(ip="192.168.1.100", name="Living Room", model="WiiM Pro"),
        ]

        with patch("pywiim.mcp.context.discover_devices", AsyncMock(return_value=devices)):
            r1 = await ctx._ensure_discovery()
            r2 = await ctx._ensure_discovery()
            assert r1 is r2

    @pytest.mark.asyncio
    async def test_ensure_discovery_force_refresh_disables_cache(self):
        """_ensure_discovery with force_refresh bypasses cache."""
        ctx = MCPContext()
        ctx.discovery_disabled = False
        devices = [
            DiscoveredDevice(ip="192.168.1.100", name="Living Room", model="WiiM Pro"),
        ]
        mock_discover = AsyncMock(return_value=devices)

        with patch("pywiim.mcp.context.discover_devices", mock_discover):
            await ctx._ensure_discovery()
            await ctx._ensure_discovery(force_refresh=True)
            assert mock_discover.call_count == 2
