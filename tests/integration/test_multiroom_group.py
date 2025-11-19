"""Integration tests for multi-device group role and control logic."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import MethodType
from typing import Any

import pytest

from pywiim.exceptions import WiiMError
from pywiim.player import Player

pytestmark = pytest.mark.integration


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
            role = "master" if player == master else f"slave-{slaves.index(player)+1}"
            _log(f"  {role:8s} {player.host:15s} volume={volume:.2f}")

        for player in players:
            mute_state = await _get_mute(player)
            if mute_state is None:
                pytest.skip(f"Device {player.host} does not report mute state")
            initial_mutes[player.host] = mute_state
            role = "master" if player == master else f"slave-{slaves.index(player)+1}"
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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)
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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)
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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)
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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)
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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
            _log("Waiting 5 seconds - check WiiM app...")
            await asyncio.sleep(5.0)

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
                role = "master" if player == master else f"slave-{slaves.index(player)+1}"
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

        _log(f"Using slave {slave.host} to send next/previous commands")
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
