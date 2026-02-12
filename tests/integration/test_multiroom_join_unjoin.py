"""Integration tests focused on multiroom join/unjoin behavior.

These tests are designed for validating real-world group transitions on
multiple devices (including larger labs with 6 devices).
"""

from __future__ import annotations

import asyncio

import pytest

from pywiim.player import Player

pytestmark = [pytest.mark.integration, pytest.mark.groups, pytest.mark.destructive]


def _log(message: str) -> None:
    """Emit progress logs so test output shows what devices are doing."""
    print(f"[join-unjoin-test] {message}", flush=True)


def _player_snapshot(player: Player) -> str:
    """Build a compact role/group snapshot string for logging."""
    group_size = player.group.size if player.group else 0
    return (
        f"{player.host} role={player.role}"
        f" solo={player.is_solo} master={player.is_master} slave={player.is_slave}"
        f" group_size={group_size}"
    )


def _log_players_state(players: list[Player], label: str) -> None:
    """Log current state for a list of players."""
    _log(label)
    for player in players:
        _log(f"  - {_player_snapshot(player)}")


async def _refresh_players(players: list[Player]) -> None:
    """Refresh all player objects, ignoring transient failures."""
    results = await asyncio.gather(*(player.refresh() for player in players), return_exceptions=True)
    for player, result in zip(players, results, strict=False):
        if isinstance(result, Exception):
            _log(f"  refresh warning for {player.host}: {result}")


async def _force_solo(players: list[Player]) -> None:
    """Ensure every player is in SOLO mode before/after tests."""
    _log("Forcing all players to SOLO state")
    await _refresh_players(players)
    _log_players_state(players, "State after initial refresh:")

    # Masters disband first so slaves drop automatically.
    for player in players:
        if player.is_master:
            try:
                _log(f"  disbanding current group on master {player.host}")
                await player.leave_group()
            except RuntimeError:
                continue

    # Handle remaining non-solo players.
    for player in players:
        if not player.is_solo:
            try:
                _log(f"  forcing non-solo player {player.host} to leave group")
                await player.leave_group()
            except RuntimeError:
                continue

    await _refresh_players(players)
    _log_players_state(players, "State after SOLO enforcement:")


async def _join_with_retry(
    joiner: Player,
    master: Player,
    players: list[Player],
    attempts: int = 2,
    settle_seconds: float = 2.0,
) -> bool:
    """Join with retry for real-device timing flakiness.

    Returns True when join is verified (master=master role, joiner=slave role),
    otherwise False after all attempts.
    """
    for attempt in range(1, attempts + 1):
        _log(f"  join attempt {attempt}/{attempts}: {joiner.host} -> {master.host}")
        await joiner.join_group(master)
        await asyncio.sleep(settle_seconds)
        await _refresh_players(players)
        _log_players_state([master, joiner], f"  state after join attempt {attempt}:")
        if master.is_master and joiner.is_slave:
            return True

        if attempt < attempts:
            _log(
                f"  join not yet stable for {joiner.host}; "
                f"master_role={master.role}, joiner_role={joiner.role}; retrying"
            )
            # Give devices an extra settle window before retry.
            await asyncio.sleep(settle_seconds)

    return False


async def _roles_match(
    players: list[Player],
    expected: dict[str, str],
    retries: int = 6,
    delay_seconds: float = 1.5,
) -> bool:
    """Wait for expected roles with refresh retries.

    expected maps host -> role ("solo" | "master" | "slave").
    """
    for attempt in range(1, retries + 1):
        await _refresh_players(players)
        actual = {player.host: player.role for player in players}
        if all(actual.get(host) == role for host, role in expected.items()):
            return True

        if attempt < retries:
            _log(f"  role convergence attempt {attempt}/{retries} not met; " f"actual={actual}, expected={expected}")
            await asyncio.sleep(delay_seconds)

    return False


@pytest.fixture
async def join_unjoin_testbed(multi_device_players):
    """Prepared players for join/unjoin integration tests."""
    players = multi_device_players["all"]
    await _force_solo(players)
    try:
        yield multi_device_players
    finally:
        await _force_solo(players)


class TestJoinUnjoinRealDevices:
    """Real-device join/unjoin validation scenarios."""

    async def test_each_slave_can_join_and_leave_master(self, join_unjoin_testbed):
        """Each configured slave joins master, then leaves back to solo."""
        master: Player = join_unjoin_testbed["master"]
        slaves: list[Player] = join_unjoin_testbed["slaves"]
        players: list[Player] = join_unjoin_testbed["all"]

        if not slaves:
            pytest.skip("Configure WIIM_TEST_GROUP_SLAVES with at least one slave device")

        for idx, slave in enumerate(slaves, start=1):
            _log(f"Round {idx}: {slave.host} joining {master.host}")
            await _force_solo(players)
            _log_players_state([master, slave], "Pre-join state:")

            await slave.join_group(master)
            await asyncio.sleep(2.0)
            await _refresh_players([master, slave])
            _log_players_state([master, slave], "Post-join state:")

            assert master.is_master, f"{master.host} should be master after join, got {master.role}"
            assert slave.is_slave, f"{slave.host} should be slave after join, got {slave.role}"

            _log(f"Round {idx}: {slave.host} leaving group")
            await slave.leave_group()
            await asyncio.sleep(2.0)
            await _refresh_players([master, slave])
            _log_players_state([master, slave], "Post-leave state:")

            assert slave.is_solo, f"{slave.host} should be solo after leave, got {slave.role}"
            assert master.is_solo, f"{master.host} should be solo after slave leaves, got {master.role}"

    @pytest.mark.slow
    async def test_pairwise_join_unjoin_matrix(self, join_unjoin_testbed):
        """All pairwise join/unjoin combinations across all configured devices."""
        players: list[Player] = join_unjoin_testbed["all"]

        if len(players) < 2:
            pytest.skip("Need at least 2 devices for pairwise join/unjoin matrix")

        round_num = 0
        for joiner in players:
            for target in players:
                if joiner is target:
                    continue

                round_num += 1
                _log(f"Matrix round {round_num}: {joiner.host} -> {target.host}")
                await _force_solo(players)
                _log_players_state([joiner, target], "Pre-join state:")

                await joiner.join_group(target)
                await asyncio.sleep(2.0)
                await _refresh_players([joiner, target])
                _log_players_state([joiner, target], "Post-join state:")

                assert target.is_master, f"{target.host} should be master, got {target.role}"
                assert joiner.is_slave, f"{joiner.host} should be slave, got {joiner.role}"

                await joiner.leave_group()
                await asyncio.sleep(2.0)
                await _refresh_players([joiner, target])
                _log_players_state([joiner, target], "Post-leave state:")

                assert joiner.is_solo, f"{joiner.host} should be solo after leave, got {joiner.role}"
                assert target.is_solo, f"{target.host} should be solo after leave, got {target.role}"

    @pytest.mark.slow
    async def test_three_player_full_join_unjoin_stress(self, join_unjoin_testbed):
        """Stress all 3-player master/slave combinations with join/unjoin cycles.

        For each master candidate among 3 players, run both slave join orders:
        - join slave_a
        - join slave_b (master now has 2 slaves)
        - slave_a leaves
        - slave_a rejoins
        - slave_b leaves
        - slave_a leaves

        This validates repeated role transitions and group integrity under churn.
        """
        import itertools

        players: list[Player] = join_unjoin_testbed["all"]

        if len(players) < 3:
            pytest.skip("Need at least 3 devices for full 3-player stress test")

        trio = players[:3]
        _log("Starting 3-player full join/unjoin stress test")
        _log_players_state(trio, "Initial 3-player subset:")

        scenario_num = 0
        for master in trio:
            slaves = [p for p in trio if p is not master]
            for join_order in itertools.permutations(slaves, 2):
                scenario_num += 1
                slave_a, slave_b = join_order
                _log("=" * 72)
                _log(
                    f"Stress scenario {scenario_num}: master={master.host}, "
                    f"join_order=[{slave_a.host}, {slave_b.host}]"
                )
                await _force_solo(trio)
                _log_players_state(trio, "Scenario pre-state (expect all solo):")

                # 1) First slave joins.
                _log(f"Step 1: {slave_a.host} joins {master.host}")
                joined = await _join_with_retry(slave_a, master, trio)
                _log_players_state(trio, "After step 1:")
                assert joined, f"{slave_a.host} failed to join {master.host} after retries"
                assert await _roles_match(
                    trio, {master.host: "master", slave_a.host: "slave"}
                ), f"Role convergence failed after step 1: master={master.role}, slave_a={slave_a.role}"

                # 2) Second slave joins.
                _log(f"Step 2: {slave_b.host} joins {master.host}")
                joined = await _join_with_retry(slave_b, master, trio)
                _log_players_state(trio, "After step 2:")
                assert joined, f"{slave_b.host} failed to join {master.host} after retries"
                assert await _roles_match(
                    trio,
                    {master.host: "master", slave_a.host: "slave", slave_b.host: "slave"},
                ), (
                    "Role convergence failed after step 2: "
                    f"master={master.role}, slave_a={slave_a.role}, slave_b={slave_b.role}"
                )

                # 3) First slave leaves.
                _log(f"Step 3: {slave_a.host} leaves group")
                await slave_a.leave_group()
                await asyncio.sleep(2.0)
                await _refresh_players(trio)
                _log_players_state(trio, "After step 3:")
                assert await _roles_match(
                    trio,
                    {master.host: "master", slave_a.host: "solo", slave_b.host: "slave"},
                ), (
                    "Role convergence failed after step 3: "
                    f"master={master.role}, slave_a={slave_a.role}, slave_b={slave_b.role}"
                )

                # 4) First slave rejoins.
                _log(f"Step 4: {slave_a.host} rejoins {master.host}")
                joined = await _join_with_retry(slave_a, master, trio)
                _log_players_state(trio, "After step 4:")
                assert joined, f"{slave_a.host} failed to rejoin {master.host} after retries"
                assert await _roles_match(
                    trio,
                    {master.host: "master", slave_a.host: "slave", slave_b.host: "slave"},
                ), (
                    "Role convergence failed after step 4: "
                    f"master={master.role}, slave_a={slave_a.role}, slave_b={slave_b.role}"
                )

                # 5) Second slave leaves.
                _log(f"Step 5: {slave_b.host} leaves group")
                await slave_b.leave_group()
                await asyncio.sleep(2.0)
                await _refresh_players(trio)
                _log_players_state(trio, "After step 5:")
                assert await _roles_match(
                    trio,
                    {master.host: "master", slave_b.host: "solo", slave_a.host: "slave"},
                ), (
                    "Role convergence failed after step 5: "
                    f"master={master.role}, slave_a={slave_a.role}, slave_b={slave_b.role}"
                )

                # 6) Final slave leaves; everyone should be solo.
                _log(f"Step 6: {slave_a.host} leaves group (final)")
                await slave_a.leave_group()
                await asyncio.sleep(2.0)
                await _refresh_players(trio)
                _log_players_state(trio, "After step 6 (expect all solo):")
                assert await _roles_match(
                    trio,
                    {trio[0].host: "solo", trio[1].host: "solo", trio[2].host: "solo"},
                ), "Role convergence failed after step 6: expected all solo"

        _log(f"Completed {scenario_num} stress scenarios successfully")
