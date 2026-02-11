"""MCP server for WiiM/LinkPlay device control."""

from __future__ import annotations

from ..exceptions import WiiMConnectionError, WiiMError, WiiMTimeoutError
from .context import MCPContext


def _error_msg(err: Exception) -> str:
    """Format exception as user-friendly message."""
    if isinstance(err, WiiMConnectionError):
        return f"Connection failed: {err}"
    if isinstance(err, WiiMTimeoutError):
        return f"Timeout: {err}"
    if isinstance(err, WiiMError):
        return str(err)
    return f"Error: {err}"


def _run_server() -> None:
    """Run the MCP server (stdio transport)."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("PyWiim", json_response=True)
    ctx = MCPContext()

    @mcp.tool()
    async def wiim_discover(force_refresh: bool = False) -> str:
        """Discover WiiM/LinkPlay devices on the network.

        Returns a list of devices with name, host (IP), and model.
        Use device names (e.g. "Living Room") with other tools for targeting.
        Results are cached for 5 minutes unless force_refresh is True.
        """
        try:
            devices = await ctx._ensure_discovery(force_refresh=force_refresh)
            lines = []
            for d in devices:
                name = d.name or d.ip
                lines.append(f"- {name}: {d.ip} ({d.model or 'unknown'})")
            return "\n".join(lines) if lines else "No devices found."
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_status(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Get playback status for a device: state, track, position, duration, volume, mute, source, role, group.

        Use device_name (e.g. "Living Room") or device_ip. Omit both if WIIM_DEFAULT_DEVICE is set.
        """
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            parts = [
                f"State: {player.state}",
                f"Volume: {int((player.volume_level or 0) * 100)}%",
                f"Mute: {player.is_muted}",
                f"Source: {player.source or 'unknown'}",
                f"Role: {player.role}",
            ]
            if player.media_title:
                parts.append(f"Track: {player.media_title}")
            if player.media_artist:
                parts.append(f"Artist: {player.media_artist}")
            if player.media_album:
                parts.append(f"Album: {player.media_album}")
            if player.media_position is not None and player.media_duration is not None:
                left = player.media_duration - player.media_position
                parts.append(f"Position: {player.media_position}s")
                parts.append(f"Duration: {player.media_duration}s")
                parts.append(f"Time left: {left}s")
            if player.role == "master" and player.group:
                members = [p.name or p.host for p in player.group.all_players if p != player]
                if members:
                    parts.append(f"Group members: {', '.join(members)}")
            elif player.role == "slave" and player.group:
                master = player.group.master
                if master:
                    parts.append(f"Group master: {master.name or master.host}")
            return "\n".join(parts)
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_play(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Start playback on a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.play()
            return "Playing."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_pause(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Pause playback on a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.pause()
            return "Paused."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_media_play_pause(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Toggle play/pause on a device. Uses resume when paused to avoid restarting track."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.media_play_pause()
            return "Toggled."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_stop(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Stop playback on a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.stop()
            return "Stopped."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_next_track(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Skip to next track on a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.next_track()
            return "Next track."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_previous_track(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Skip to previous track on a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.previous_track()
            return "Previous track."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_volume(
        device_name: str | None = None,
        device_ip: str | None = None,
        level: int | None = None,
    ) -> str:
        """Get or set volume (0-100) on a device. Omit level to get current volume."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            if level is not None:
                if level < 0 or level > 100:
                    return "Volume must be 0-100."
                await player.set_volume(level / 100.0)
                return f"Volume set to {level}%."
            vol = player.volume_level
            return f"Volume: {int((vol or 0) * 100)}%"
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_mute(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Mute a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.set_mute(True)
            return "Muted."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_unmute(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Unmute a device."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.set_mute(False)
            return "Unmuted."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_sources(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """List available audio sources for a device (e.g. Bluetooth, Line In, NETWORK)."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            sources = player.available_sources
            return "\n".join(sources) if sources else "No sources available."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_set_source(
        device_name: str | None = None,
        device_ip: str | None = None,
        source_id: str = "",
    ) -> str:
        """Set audio input source (e.g. 'Bluetooth', 'Line In', 'NETWORK'). Use wiim_sources to list options."""
        try:
            if not source_id:
                return "source_id is required. Use wiim_sources to list options."
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.set_source(source_id)
            return f"Source set to {source_id}."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_play_url(
        device_name: str | None = None,
        device_ip: str | None = None,
        url: str = "",
    ) -> str:
        """Play a URL on a device. Use when another tool (e.g. Spotify MCP) provides the URL."""
        try:
            if not url:
                return "url is required."
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.play_url(url)
            return "Playing URL."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_group_join(
        slave_device_name: str | None = None,
        slave_device_ip: str | None = None,
        master_device_name: str | None = None,
        master_device_ip: str | None = None,
    ) -> str:
        """Sync a device (slave) into another device's group (master). E.g. sync Kitchen to Living Room."""
        try:
            if not slave_device_name and not slave_device_ip:
                return "slave_device_name or slave_device_ip required."
            if not master_device_name and not master_device_ip:
                return "master_device_name or master_device_ip required."
            slave = await ctx.get_player(
                device_name=slave_device_name,
                device_ip=slave_device_ip,
            )
            master = await ctx.get_player(
                device_name=master_device_name,
                device_ip=master_device_ip,
            )
            await slave.join_group(master)
            return f"Synced {slave.name or slave.host} to {master.name or master.host}."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    @mcp.tool()
    async def wiim_group_leave(
        device_name: str | None = None,
        device_ip: str | None = None,
    ) -> str:
        """Unsync a device from its group."""
        try:
            player = await ctx.get_player(device_name=device_name, device_ip=device_ip)
            await player.leave_group()
            return "Left group."
        except ValueError as e:
            return str(e)
        except (WiiMError, Exception) as e:
            return _error_msg(e)

    mcp.run()


def run() -> None:
    """Entry point for wiim-mcp console script."""
    _run_server()
