"""Integration tests for multi-device group role and control logic."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import MethodType
from typing import Any

import pytest

from pywiim.exceptions import WiiMError
from pywiim.player import Player

pytestmark = [pytest.mark.integration, pytest.mark.groups]


def _log(message: str) -> None:
    """Emit progress logs so test output shows what the devices are doing."""
    print(f"[multiroom-test] {message}", flush=True)


async def _refresh_players(players: list[Player]) -> None:
    """Refresh all player objects, ignoring transient failures."""
    _log(f"Refreshing {len(players)} player(s)")
    await asyncio.gather(*(player.refresh() for player in players), return_exceptions=True)


async def _force_solo(players: list[Player]) -> None:
    """Ensure every player is in SOLO mode."""
    _log("Bringing all devices to SOLO state")
    await _refresh_players(players)

    # Masters disband first so slaves drop automatically
    for player in players:
        if player.is_master:
            _log(f"Disbanding existing group on master {player.host}")
            try:
                await player.leave_group()
            except RuntimeError:
                continue
    # Handle remaining slaves (if master not part of this fixture)
    for player in players:
        if not player.is_solo:
            role_label = "master" if player.is_master else "slave"
            _log(f"Forcing {role_label} {player.host} to leave group")
            try:
                await player.leave_group()
            except RuntimeError:
                continue

    await _refresh_players(players)


async def _create_group(master: Player, slaves: list[Player]) -> Any:
    """Create a fresh group with the provided master and slaves."""
    _log(f"Creating group with master {master.host} and {len(slaves)} slave(s)")
    group = await master.create_group()
    for slave in slaves:
        _log(f"Joining slave {slave.host} to {master.host}")
        await slave.join_group(master)
    await _refresh_players([master, *slaves])
    return group


async def _get_volume(player: Player) -> float | None:
    """Get a device volume level as a 0..1 float by querying the device."""
    # Always query device directly to confirm actual hardware state
    value = await player.get_volume()
    if value is None:
        return None
    return max(0.0, min(float(value), 1.0))


async def _get_mute(player: Player) -> bool | None:
    """Get a device mute state by querying the device."""
    # Always query device directly to confirm actual hardware state
    value = await player.get_muted()
    if value is None:
        return None
    return bool(value)


def _track_player_method(player: Player, method_name: str) -> tuple[dict[str, int], Callable[[], None]]:
    """Wrap a Player method to count invocations and return a restore callback."""
    original = getattr(player, method_name)
    calls: dict[str, int] = {"count": 0}

    async def wrapper(self, *args, **kwargs):
        calls["count"] += 1
        return await original(*args, **kwargs)

    setattr(player, method_name, MethodType(wrapper, player))

    def restore() -> None:
        setattr(player, method_name, MethodType(original.__func__, player))  # type: ignore[attr-defined]

    return calls, restore


def _log_device_states(players: list[Player], label: str = "Current state") -> None:
    """Log detailed state of all devices."""
    _log(f"{label}:")
    for player in players:
        role = player.role or "unknown"
        role_flags = []
        if player.is_master:
            role_flags.append("is_master")
        if player.is_slave:
            role_flags.append("is_slave")
        if player.is_solo:
            role_flags.append("is_solo")
        flags_str = ", ".join(role_flags) if role_flags else "no flags"

        # Get group info if available
        group_info = ""
        if player.group:
            group_info = f", group.size={player.group.size}"

        _log(f"  {player.host:15s} role={role:8s} ({flags_str}){group_info}")


@pytest.fixture
async def multi_device_testbed(multi_device_players):
    """Provide prepared master/slave Player objects for each test."""
    players = multi_device_players["all"]
    await _force_solo(players)
    try:
        yield multi_device_players
    finally:
        _log("Test cleanup starting")
        await _force_solo(players)


class TestMultiDeviceGroup:
    """Validate master/slave/virtual master behavior with real devices."""

    async def test_group_role_detection(self, multi_device_testbed):
        """Ensure master/slave roles and DeviceGroupInfo stay in sync."""
        master: Player = multi_device_testbed["master"]
        slaves: list[Player] = multi_device_testbed["slaves"]

        if not slaves:
            pytest.skip("Configure WIIM_TEST_GROUP_SLAVES with at least one slave device")

        _log("Starting role detection test")
        group = await _create_group(master, slaves)

        assert master.is_master
        assert group.master == master
        assert len(group.slaves) == len(slaves)
        assert {slave.host for slave in group.slaves} == {slave.host for slave in slaves}

        master_info = await master.client.get_device_group_info()
        assert master_info.role == "master"
        assert master_info.master_host == master.host
        assert set(master_info.slave_hosts) >= {slave.host for slave in slaves}

        for slave in slaves:
            info = await slave.client.get_device_group_info()
            assert info.role == "slave"
            # Note: WiiM API doesn't provide master_ip to slave devices, only master_uuid
            # The master_host may be None - this is an API limitation, not a bug
            assert info.master_uuid is not None, "Slave should know master's UUID"
            # If master_host is available, verify it matches (some firmware versions provide it)
            if info.master_host is not None:
                assert info.master_host == master.host
            assert slave.group is group

    async def test_group_volume_and_mute_propagation(self, multi_device_testbed):
        """Validate group set_volume/mute_all follow documented rules."""
        master: Player = multi_device_testbed["master"]
        slaves: list[Player] = multi_device_testbed["slaves"]

        if len(slaves) < 2:
            pytest.skip("Configure WIIM_TEST_GROUP_SLAVES with at least two slave devices")

        group = await _create_group(master, slaves)
        players = [master, *slaves]
        slave1, slave2 = slaves[0], slaves[1]

        # ===== Record Initial States (for restoration) =====
        _log("=" * 80)
        _log("RECORDING INITIAL STATES FOR RESTORATION")
        _log("=" * 80)

        initial_volumes: dict[str, float] = {}
        initial_mutes: dict[str, bool] = {}

        for player in players:
            volume = await _get_volume(player)
            if volume is None:
                pytest.skip(f"Device {player.host} does not report volume levels")
            initial_volumes[player.host] = volume
            role = "master" if player == master else f"slave-{slaves.index(player) + 1}"
            _log(f"  {role:8s} {player.host:15s} volume={volume:.2f}")

        for player in players:
            mute_state = await _get_mute(player)
            if mute_state is None:
                pytest.skip(f"Device {player.host} does not report mute state")
            initial_mutes[player.host] = mute_state
            role = "master" if player == master else f"slave-{slaves.index(player) + 1}"
            _log(f"  {role:8s} {player.host:15s} mute={mute_state}")

        try:
            # ===== TEST 1: Master is MAX, increase volume =====
            _log("=" * 80)
            _log("TEST 1: MASTER IS MAX -> INCREASE VOLUME")
            _log("=" * 80)
            _log("Setup: Master=0.30, Slave1=0.20, Slave2=0.10")
            await master.set_volume(0.30)
            await slave1.set_volume(0.20)
            await slave2.set_volume(0.10)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f}")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f}")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f}")
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.30 = master)")
            assert virtual_vol == pytest.approx(0.30, abs=0.05)

            _log("Applying group.set_volume_all(0.35) -> delta=+0.05 to all devices")
            await group.set_volume_all(0.35)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} 0.30 -> {vol_m:.2f} (expected 0.35)")
            _log(f"  slave-1  {slave1.host:15s} 0.20 -> {vol_s1:.2f} (expected 0.25)")
            _log(f"  slave-2  {slave2.host:15s} 0.10 -> {vol_s2:.2f} (expected 0.15)")
            assert vol_m == pytest.approx(0.35, abs=0.05)
            assert vol_s1 == pytest.approx(0.25, abs=0.05)
            assert vol_s2 == pytest.approx(0.15, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.35 = master still MAX)")
            assert virtual_vol == pytest.approx(0.35, abs=0.05)

            # ===== TEST 2: Slave1 is MAX, decrease volume =====
            _log("=" * 80)
            _log("TEST 2: SLAVE1 IS MAX -> DECREASE VOLUME")
            _log("=" * 80)
            _log("Setup: Master=0.15, Slave1=0.30, Slave2=0.20")
            await master.set_volume(0.15)
            await slave1.set_volume(0.30)
            await slave2.set_volume(0.20)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f}")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f}")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f}")
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.30 = slave1)")
            assert virtual_vol == pytest.approx(0.30, abs=0.05)

            _log("Applying group.set_volume_all(0.25) -> delta=-0.05 to all devices")
            await group.set_volume_all(0.25)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} 0.15 -> {vol_m:.2f} (expected 0.10)")
            _log(f"  slave-1  {slave1.host:15s} 0.30 -> {vol_s1:.2f} (expected 0.25)")
            _log(f"  slave-2  {slave2.host:15s} 0.20 -> {vol_s2:.2f} (expected 0.15)")
            assert vol_m == pytest.approx(0.10, abs=0.05)
            assert vol_s1 == pytest.approx(0.25, abs=0.05)
            assert vol_s2 == pytest.approx(0.15, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.25 = slave1 still MAX)")
            assert virtual_vol == pytest.approx(0.25, abs=0.05)

            # ===== TEST 3: Slave2 is MAX, increase volume =====
            _log("=" * 80)
            _log("TEST 3: SLAVE2 IS MAX -> INCREASE VOLUME")
            _log("=" * 80)
            _log("Setup: Master=0.10, Slave1=0.15, Slave2=0.30")
            await master.set_volume(0.10)
            await slave1.set_volume(0.15)
            await slave2.set_volume(0.30)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f}")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f}")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f}")
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.30 = slave2)")
            assert virtual_vol == pytest.approx(0.30, abs=0.05)

            _log("Applying group.set_volume_all(0.40) -> delta=+0.10 to all devices")
            await group.set_volume_all(0.40)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} 0.10 -> {vol_m:.2f} (expected 0.20)")
            _log(f"  slave-1  {slave1.host:15s} 0.15 -> {vol_s1:.2f} (expected 0.25)")
            _log(f"  slave-2  {slave2.host:15s} 0.30 -> {vol_s2:.2f} (expected 0.40)")
            assert vol_m == pytest.approx(0.20, abs=0.05)
            assert vol_s1 == pytest.approx(0.25, abs=0.05)
            assert vol_s2 == pytest.approx(0.40, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.40 = slave2 still MAX)")
            assert virtual_vol == pytest.approx(0.40, abs=0.05)

            # ===== TEST 4: All devices same volume =====
            _log("=" * 80)
            _log("TEST 4: ALL DEVICES EQUAL VOLUME -> CHANGE")
            _log("=" * 80)
            _log("Setup: Master=0.20, Slave1=0.20, Slave2=0.20")
            await master.set_volume(0.20)
            await slave1.set_volume(0.20)
            await slave2.set_volume(0.20)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f}")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f}")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f}")
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.20 = all equal)")
            assert virtual_vol == pytest.approx(0.20, abs=0.05)

            _log("Applying group.set_volume_all(0.30) -> delta=+0.10 to all devices")
            await group.set_volume_all(0.30)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} 0.20 -> {vol_m:.2f} (expected 0.30)")
            _log(f"  slave-1  {slave1.host:15s} 0.20 -> {vol_s1:.2f} (expected 0.30)")
            _log(f"  slave-2  {slave2.host:15s} 0.20 -> {vol_s2:.2f} (expected 0.30)")
            assert vol_m == pytest.approx(0.30, abs=0.05)
            assert vol_s1 == pytest.approx(0.30, abs=0.05)
            assert vol_s2 == pytest.approx(0.30, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.30 = all equal)")
            assert virtual_vol == pytest.approx(0.30, abs=0.05)

            # ===== TEST 5: All unmuted =====
            _log("=" * 80)
            _log("TEST 5: ALL UNMUTED -> VERIFY VIRTUAL MUTE=FALSE")
            _log("=" * 80)
            _log("Setup: All devices unmuted")
            await master.set_mute(False)
            await slave1.set_mute(False)
            await slave2.set_mute(False)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            _log(f"  Virtual group mute: {group.is_muted} (should be False)")
            assert group.is_muted is False

            # ===== TEST 6: All muted =====
            _log("=" * 80)
            _log("TEST 6: ALL MUTED -> VERIFY VIRTUAL MUTE=TRUE")
            _log("=" * 80)
            _log("Applying group.mute_all(True)")
            await group.mute_all(True)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            assert mute_m is True
            assert mute_s1 is True
            assert mute_s2 is True
            _log(f"  Virtual group mute: {group.is_muted} (should be True)")
            assert group.is_muted is True

            # ===== TEST 7: Only master muted =====
            _log("=" * 80)
            _log("TEST 7: ONLY MASTER MUTED -> VERIFY VIRTUAL MUTE=FALSE")
            _log("=" * 80)
            _log("Setup: Master=muted, Slaves=unmuted")
            await master.set_mute(True)
            await slave1.set_mute(False)
            await slave2.set_mute(False)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            assert mute_m is True
            assert mute_s1 is False
            assert mute_s2 is False
            _log(f"  Virtual group mute: {group.is_muted} (should be False - not all muted)")
            assert group.is_muted is False

            # ===== TEST 8: Only one slave muted =====
            _log("=" * 80)
            _log("TEST 8: ONLY SLAVE1 MUTED -> VERIFY VIRTUAL MUTE=FALSE")
            _log("=" * 80)
            _log("Setup: Master=unmuted, Slave1=muted, Slave2=unmuted")
            await master.set_mute(False)
            await slave1.set_mute(True)
            await slave2.set_mute(False)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            assert mute_m is False
            assert mute_s1 is True
            assert mute_s2 is False
            _log(f"  Virtual group mute: {group.is_muted} (should be False - not all muted)")
            assert group.is_muted is False

            # ===== TEST 9: Master + one slave muted =====
            _log("=" * 80)
            _log("TEST 9: MASTER + SLAVE1 MUTED -> VERIFY VIRTUAL MUTE=FALSE")
            _log("=" * 80)
            _log("Setup: Master=muted, Slave1=muted, Slave2=unmuted")
            await master.set_mute(True)
            await slave1.set_mute(True)
            await slave2.set_mute(False)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            assert mute_m is True
            assert mute_s1 is True
            assert mute_s2 is False
            _log(f"  Virtual group mute: {group.is_muted} (should be False - not all muted)")
            assert group.is_muted is False

            # ===== TEST 10: Unmute all =====
            _log("=" * 80)
            _log("TEST 10: MUTE ALL -> UNMUTE ALL")
            _log("=" * 80)
            _log("First muting all devices")
            await group.mute_all(True)
            await asyncio.sleep(1.0)
            await _refresh_players(players)
            _log(f"  Virtual group mute: {group.is_muted} (should be True)")
            assert group.is_muted is True

            _log("Now applying group.mute_all(False)")
            await group.mute_all(False)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current mute states:")
            mute_m = await _get_mute(master)
            mute_s1 = await _get_mute(slave1)
            mute_s2 = await _get_mute(slave2)
            _log(f"  master   {master.host:15s} mute={mute_m}")
            _log(f"  slave-1  {slave1.host:15s} mute={mute_s1}")
            _log(f"  slave-2  {slave2.host:15s} mute={mute_s2}")
            assert mute_m is False
            assert mute_s1 is False
            assert mute_s2 is False
            _log(f"  Virtual group mute: {group.is_muted} (should be False)")
            assert group.is_muted is False

            # ===== TEST 11: Volume at Boundaries =====
            _log("=" * 80)
            _log("TEST 11: VOLUME BOUNDARY -> MINIMUM (0.0)")
            _log("=" * 80)
            _log("Applying group.set_volume_all(0.0)")
            await group.set_volume_all(0.0)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f} (should be 0.00)")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f} (should be 0.00)")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f} (should be 0.00)")
            assert vol_m == pytest.approx(0.0, abs=0.05)
            assert vol_s1 == pytest.approx(0.0, abs=0.05)
            assert vol_s2 == pytest.approx(0.0, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.00)")
            assert virtual_vol == pytest.approx(0.0, abs=0.05)

            # ===== TEST 12: Volume at Boundaries - Maximum =====
            _log("=" * 80)
            _log("TEST 12: VOLUME BOUNDARY -> MAXIMUM (0.40) - NEVER EXCEED!")
            _log("=" * 80)
            _log("Applying group.set_volume_all(0.40)")
            await group.set_volume_all(0.40)
            await asyncio.sleep(1.0)
            await _refresh_players(players)

            _log("Current volumes:")
            vol_m = await _get_volume(master)
            vol_s1 = await _get_volume(slave1)
            vol_s2 = await _get_volume(slave2)
            _log(f"  master   {master.host:15s} volume={vol_m:.2f} (should be 0.40)")
            _log(f"  slave-1  {slave1.host:15s} volume={vol_s1:.2f} (should be 0.40)")
            _log(f"  slave-2  {slave2.host:15s} volume={vol_s2:.2f} (should be 0.40)")
            assert vol_m == pytest.approx(0.40, abs=0.05)
            assert vol_s1 == pytest.approx(0.40, abs=0.05)
            assert vol_s2 == pytest.approx(0.40, abs=0.05)
            virtual_vol = group.volume_level
            _log(f"  Virtual group master: {virtual_vol:.2f} (should be 0.40)")
            assert virtual_vol == pytest.approx(0.40, abs=0.05)

        finally:
            _log("=" * 80)
            _log("RESTORING INITIAL STATES")
            _log("=" * 80)
            await asyncio.gather(
                *(player.set_volume(initial_volumes[player.host]) for player in players),
                return_exceptions=True,
            )
            await asyncio.gather(
                *(player.set_mute(initial_mutes[player.host]) for player in players),
                return_exceptions=True,
            )
            await asyncio.sleep(2.0)
            await _refresh_players(players)

            for player in players:
                role = "master" if player == master else f"slave-{slaves.index(player) + 1}"
                volume = await _get_volume(player)
                mute = await _get_mute(player)
                _log(f"  {role:8s} {player.host:15s} volume={volume:.2f} mute={mute}")
            _log("=" * 80)

    async def test_group_next_previous_routed_to_master(self, multi_device_testbed):
        """Ensure virtual next/previous hit the physical master."""
        master: Player = multi_device_testbed["master"]
        slaves: list[Player] = multi_device_testbed["slaves"]

        if not slaves:
            pytest.skip("Configure WIIM_TEST_GROUP_SLAVES with at least one slave device")

        _log("Preparing group for transport control propagation test")
        await _create_group(master, slaves)
        slave = slaves[0]

        _log(f"Using slave {slave.host} to send next/previous commands via Group object")
        next_counter, restore_next = _track_player_method(master, "next_track")
        prev_counter, restore_prev = _track_player_method(master, "previous_track")

        try:
            try:
                await slave.group.next_track()  # type: ignore[union-attr]
            except WiiMError as err:
                pytest.skip(f"Next track command unavailable: {err}")
            assert next_counter["count"] == 1

            try:
                await slave.group.previous_track()  # type: ignore[union-attr]
            except WiiMError as err:
                pytest.skip(f"Previous track command unavailable: {err}")
            assert prev_counter["count"] == 1
        finally:
            restore_next()
            restore_prev()

    async def test_slave_direct_playback_routes_to_master(self, multi_device_testbed):
        """Ensure slave playback commands automatically route to master."""
        master: Player = multi_device_testbed["master"]
        slaves: list[Player] = multi_device_testbed["slaves"]

        if not slaves:
            pytest.skip("Configure WIIM_TEST_GROUP_SLAVES with at least one slave device")

        _log("Preparing group for slave routing test")
        await _create_group(master, slaves)
        slave = slaves[0]

        _log(f"Calling playback commands directly on slave {slave.host}")
        next_counter, restore_next = _track_player_method(master, "next_track")
        prev_counter, restore_prev = _track_player_method(master, "previous_track")
        pause_counter, restore_pause = _track_player_method(master, "pause")

        try:
            # Slave playback commands should route to master automatically
            _log("Testing slave.next_track() -> routes to master")
            try:
                await slave.next_track()
            except WiiMError as err:
                pytest.skip(f"Next track command unavailable: {err}")
            assert next_counter["count"] == 1, "slave.next_track() should route to master.next_track()"

            _log("Testing slave.previous_track() -> routes to master")
            try:
                await slave.previous_track()
            except WiiMError as err:
                pytest.skip(f"Previous track command unavailable: {err}")
            assert prev_counter["count"] == 1, "slave.previous_track() should route to master.previous_track()"

            _log("Testing slave.pause() -> routes to master")
            try:
                await slave.pause()
            except WiiMError as err:
                pytest.skip(f"Pause command unavailable: {err}")
            assert pause_counter["count"] == 1, "slave.pause() should route to master.pause()"

            _log("✅ All slave playback commands correctly routed to master")
        finally:
            restore_next()
            restore_prev()
            restore_pause()


class TestGroupEdgeCases:
    """Test edge cases for group formation, dissolution, and migration.

    These tests validate unusual but valid group operations with ALL device
    permutations to ensure behavior is consistent regardless of which device
    plays each role.

    With 3 devices (A, B, C), we test:
    - Each device as master
    - Each device as slave
    - Each device as solo that others join
    """

    async def test_all_devices_can_be_master(self, multi_device_testbed):
        """Each device can successfully become a master with slaves."""
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices")

        _log("=" * 80)
        _log("TEST: ALL DEVICES CAN BE MASTER")
        _log(f"Testing {len(players)} devices: {[p.host for p in players]}")
        _log("=" * 80)

        # Test each device as master
        for i, potential_master in enumerate(players):
            # Get other devices as potential slaves
            other_devices = [p for p in players if p != potential_master]
            slave = other_devices[0]  # Use first other device as slave

            _log(f"\n--- Round {i + 1}/{len(players)}: {potential_master.host} as MASTER ---")

            # Reset to solo
            await _force_solo(players)
            _log_device_states(players, "After reset to solo")

            # Form group with this device as master
            _log(f"Action: {slave.host}.join_group({potential_master.host})")
            await slave.join_group(potential_master)
            _log("Waiting 2s for group to stabilize...")
            await asyncio.sleep(2.0)
            await _refresh_players([potential_master, slave])

            _log_device_states([potential_master, slave], "After group formation")
            assert potential_master.is_master, f"{potential_master.host} should be master, got {potential_master.role}"
            assert slave.is_slave, f"{slave.host} should be slave, got {slave.role}"
            _log(f"✓ Round {i + 1} PASSED: {potential_master.host} is master, {slave.host} is slave")

        # Cleanup
        await _force_solo(players)
        _log("\n✅ All devices can be master test PASSED")

    async def test_all_devices_can_be_slave(self, multi_device_testbed):
        """Each device can successfully become a slave."""
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices")

        _log("=" * 80)
        _log("TEST: ALL DEVICES CAN BE SLAVE")
        _log("=" * 80)

        # Test each device as slave
        for i, potential_slave in enumerate(players):
            # Get another device to be master
            other_devices = [p for p in players if p != potential_slave]
            master = other_devices[0]

            _log(f"\n--- Round {i + 1}: {potential_slave.host} as SLAVE ---")

            # Reset to solo
            await _force_solo(players)

            # Form group with this device as slave
            _log(f"Creating group: {master.host} (master) + {potential_slave.host} (slave)")
            await potential_slave.join_group(master)
            await asyncio.sleep(2.0)
            await _refresh_players([master, potential_slave])

            assert master.is_master, f"{master.host} should be master, got {master.role}"
            assert potential_slave.is_slave, f"{potential_slave.host} should be slave, got {potential_slave.role}"
            _log(f"✓ {potential_slave.host} successfully became slave")

        # Cleanup
        await _force_solo(players)
        _log("\n✅ All devices can be slave test PASSED")

    async def test_slave_leave_rejoin_all_permutations(self, multi_device_testbed):
        """Each device can leave as slave and rejoin."""
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices")

        _log("=" * 80)
        _log("TEST: SLAVE LEAVE/REJOIN ALL PERMUTATIONS")
        _log("=" * 80)

        # Test each device leaving and rejoining
        for i, slave_device in enumerate(players):
            other_devices = [p for p in players if p != slave_device]
            master = other_devices[0]

            _log(f"\n--- Round {i + 1}: {slave_device.host} leaves and rejoins ---")

            # Reset and form group
            await _force_solo(players)
            await slave_device.join_group(master)
            await asyncio.sleep(2.0)
            await _refresh_players([master, slave_device])

            assert slave_device.is_slave, f"{slave_device.host} should be slave"

            # Leave
            _log(f"{slave_device.host} leaving group...")
            await slave_device.leave_group()
            await asyncio.sleep(2.0)
            await _refresh_players([master, slave_device])

            assert slave_device.is_solo, f"{slave_device.host} should be solo after leaving, got {slave_device.role}"
            _log(f"✓ {slave_device.host} is now solo")

            # Rejoin
            _log(f"{slave_device.host} rejoining {master.host}...")
            await slave_device.join_group(master)
            await asyncio.sleep(2.0)
            await _refresh_players([master, slave_device])

            assert slave_device.is_slave, f"{slave_device.host} should be slave after rejoin, got {slave_device.role}"
            _log(f"✓ {slave_device.host} successfully rejoined as slave")

        # Cleanup
        await _force_solo(players)
        _log("\n✅ Slave leave/rejoin all permutations test PASSED")

    async def test_group_dissolution_all_masters(self, multi_device_testbed):
        """Each device can disband a group as master."""
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices")

        _log("=" * 80)
        _log("TEST: GROUP DISSOLUTION WITH EACH DEVICE AS MASTER")
        _log("=" * 80)

        for i, master_device in enumerate(players):
            slaves = [p for p in players if p != master_device]

            _log(f"\n--- Round {i + 1}: {master_device.host} disbands group ---")

            # Reset and form group
            await _force_solo(players)
            await _create_group(master_device, slaves)
            await _refresh_players(players)

            assert master_device.is_master, f"{master_device.host} should be master"
            for slave in slaves:
                assert slave.is_slave, f"{slave.host} should be slave"
            _log(f"✓ Group formed: {master_device.host} + {len(slaves)} slaves")

            # Disband
            _log(f"{master_device.host} disbanding group...")
            await master_device.leave_group()
            await asyncio.sleep(3.0)
            await _refresh_players(players)

            for player in players:
                assert player.is_solo, f"{player.host} should be solo after disband, got {player.role}"
            _log("✓ All devices are now solo")

        _log("\n✅ Group dissolution all masters test PASSED")

    async def test_solo_joins_solo_all_permutations(self, multi_device_testbed):
        """Test all pairwise solo+solo->group combinations."""
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices")

        _log("=" * 80)
        _log("TEST: SOLO + SOLO -> GROUP (ALL PAIRS)")
        _log("=" * 80)

        # Test all pairs (A joins B, B joins A, A joins C, etc.)
        round_num = 0
        for joiner in players:
            for target in players:
                if joiner == target:
                    continue

                round_num += 1
                _log(f"\n--- Round {round_num}: {joiner.host} joins {target.host} ---")

                # Reset to solo
                await _force_solo(players)
                await _refresh_players([joiner, target])

                assert joiner.is_solo, f"{joiner.host} should be solo"
                assert target.is_solo, f"{target.host} should be solo"

                # Join
                _log(f"{joiner.host} joining {target.host}...")
                await joiner.join_group(target)
                await asyncio.sleep(2.0)
                await _refresh_players([joiner, target])

                assert target.is_master, f"{target.host} should be master, got {target.role}"
                assert joiner.is_slave, f"{joiner.host} should be slave, got {joiner.role}"
                _log(f"✓ {target.host}=master, {joiner.host}=slave")

        # Cleanup
        await _force_solo(players)
        _log(f"\n✅ Solo + Solo all permutations test PASSED ({round_num} combinations)")

    async def test_slave_migration_all_permutations(self, multi_device_testbed):
        """Test slave migrating from one master to another (all permutations).

        With 3 devices, tests all 6 permutations of:
        - Initial master, migrating slave, new master (solo)
        """
        players: list[Player] = multi_device_testbed["all"]

        if len(players) < 3:
            pytest.skip("Need at least 3 devices for slave migration test")

        _log("=" * 80)
        _log("TEST: SLAVE MIGRATION (ALL PERMUTATIONS)")
        _log("=" * 80)

        # Generate all permutations of (initial_master, slave, new_master)
        from itertools import permutations

        round_num = 0
        for initial_master, migrating_slave, new_master in permutations(players):
            round_num += 1
            _log(f"\n--- Round {round_num}: {migrating_slave.host} migrates ---")
            _log(f"    from {initial_master.host} to {new_master.host}")

            # Reset to solo
            await _force_solo(players)

            # Create initial group
            _log(f"Initial group: {initial_master.host} (master) + {migrating_slave.host} (slave)")
            await _create_group(initial_master, [migrating_slave])
            await _refresh_players(players)

            assert initial_master.is_master, f"{initial_master.host} should be master"
            assert migrating_slave.is_slave, f"{migrating_slave.host} should be slave"
            assert new_master.is_solo, f"{new_master.host} should be solo"

            # Migrate slave to new master
            _log(f"{migrating_slave.host} joining {new_master.host}...")
            await migrating_slave.join_group(new_master)
            await asyncio.sleep(3.0)
            await _refresh_players(players)

            # Verify new state
            assert (
                initial_master.is_solo
            ), f"{initial_master.host} should be solo after losing slave, got {initial_master.role}"
            assert new_master.is_master, f"{new_master.host} should be master, got {new_master.role}"
            assert (
                migrating_slave.is_slave
            ), f"{migrating_slave.host} should be slave of new master, got {migrating_slave.role}"
            _log(f"✓ Migration complete: {initial_master.host}=solo, {new_master.host}=master")
            _log(f"  {migrating_slave.host}=slave")

        # Cleanup
        await _force_solo(players)
        _log(f"\n✅ Slave migration all permutations test PASSED ({round_num} combinations)")
