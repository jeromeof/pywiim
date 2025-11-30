"""Pytest configuration and fixtures for pywiim tests.

This module provides fixtures for both unit tests (with mocks) and
integration tests (with real devices).
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiohttp import ClientSession

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


# ============================================================================
# Environment Variables for Integration Tests
# ============================================================================


def _parse_host_list(value: str | None) -> list[str]:
    """Parse a comma/semicolon/whitespace separated list of hosts."""
    if not value:
        return []

    normalized = value.replace(";", ",").replace("\n", ",").replace("\t", ",")
    hosts: list[str] = []
    for chunk in normalized.split(","):
        host = chunk.strip()
        if host:
            hosts.append(host)
    return hosts


# Real device testing can be enabled via environment variables
# Example: WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/
WIIM_TEST_DEVICE = os.getenv("WIIM_TEST_DEVICE")
WIIM_TEST_PORT = int(os.getenv("WIIM_TEST_PORT", "80"))
WIIM_TEST_HTTPS = os.getenv("WIIM_TEST_HTTPS", "false").lower() == "true"
WIIM_TEST_GROUP_MASTER = os.getenv("WIIM_TEST_GROUP_MASTER")
WIIM_TEST_GROUP_SLAVES = _parse_host_list(os.getenv("WIIM_TEST_GROUP_SLAVES"))


# ============================================================================
# Unit Test Fixtures (Mocks)
# ============================================================================


@pytest.fixture
def mock_device_info():
    """Mock device info for testing."""
    from pywiim.models import DeviceInfo

    return DeviceInfo(
        uuid="test-uuid-123",
        name="Test Device",
        model="WiiM Pro",
        firmware="5.0.1",
        mac="AA:BB:CC:DD:EE:FF",
        ip="192.168.1.100",
    )


@pytest.fixture
def mock_player_status():
    """Mock player status for testing."""
    from pywiim.models import PlayerStatus

    return PlayerStatus(
        play_state="play",
        volume=50,
        mute=False,
        source="spotify",
        position=120,
        duration=240,
        title="Test Song",
        artist="Test Artist",
        album="Test Album",
    )


@pytest.fixture
def mock_capabilities():
    """Mock device capabilities for testing."""
    return {
        "firmware_version": "5.0.1",
        "device_type": "WiiM Pro",
        "is_wiim_device": True,
        "is_legacy_device": False,
        "vendor": "wiim",
        "supports_enhanced_grouping": True,
        "supports_audio_output": True,
        "supports_metadata": True,
        "supports_presets": True,
        "supports_eq": True,
        "response_timeout": 2.0,
        "retry_count": 2,
        "protocol_priority": ["https", "http"],
    }


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp ClientSession for testing."""
    session = MagicMock(spec=ClientSession)
    session._closed = False
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_http_response():
    """Mock aiohttp ClientResponse for testing."""
    response = MagicMock()
    response.status = 200
    response.headers = {}
    response.json = AsyncMock(return_value={"status": "ok"})
    response.text = AsyncMock(return_value='{"status": "ok"}')
    response.read = AsyncMock(return_value=b'{"status": "ok"}')
    return response


@pytest.fixture
def mock_client(mock_aiohttp_session, mock_capabilities):
    """Create a mock WiiMClient for testing.

    This fixture creates a client with mocked HTTP session and capabilities.
    """
    from pywiim.client import WiiMClient

    client = WiiMClient(
        host="192.168.1.100",
        port=80,
        session=mock_aiohttp_session,
        capabilities=mock_capabilities,
    )

    # Mock the _request method to avoid actual HTTP calls
    client._request = AsyncMock(return_value={"status": "ok"})

    return client


# ============================================================================
# Integration Test Fixtures (Real Devices)
# ============================================================================


@pytest.fixture(autouse=True, scope="function")
def restore_capabilities_after_test():
    """Restore WiiMClient.capabilities property after each test to avoid affecting other tests.

    This fixture ensures that any test that patches the capabilities property on WiiMClient
    restores it after the test completes, preventing test isolation issues.
    """
    from pywiim.client import WiiMClient

    # Store original property before tests
    original_capabilities = getattr(WiiMClient, "capabilities", None)

    yield

    # Restore original property after test if it was patched
    if hasattr(WiiMClient, "_original_capabilities_property"):
        WiiMClient.capabilities = WiiMClient._original_capabilities_property
        delattr(WiiMClient, "_original_capabilities_property")
    elif original_capabilities is not None:
        # Only restore if it was actually changed
        current_capabilities = getattr(WiiMClient, "capabilities", None)
        if current_capabilities is not original_capabilities:
            try:
                WiiMClient.capabilities = original_capabilities
            except (AttributeError, TypeError):
                pass  # Ignore if we can't restore


@pytest.fixture(autouse=True, scope="function")
def restore_player_properties_after_test():
    """Restore Player class properties after each test to avoid affecting other tests.

    This fixture ensures that any test that patches Player class properties (like volume_level,
    is_muted, play_state, etc.) restores them after the test completes, preventing test
    isolation issues.
    """
    from pywiim.player import Player

    # Store original properties before tests
    original_properties = {}
    property_names = [
        "volume_level",
        "is_muted",
        "play_state",
        "media_title",
        "media_position",
        "is_master",
        "audio_output_mode",
        "is_bluetooth_output_active",
        "source",
    ]
    for prop_name in property_names:
        original_properties[prop_name] = getattr(Player, prop_name, None)

    yield

    # Restore original properties after test if they were patched
    for prop_name, original_prop in original_properties.items():
        if hasattr(Player, f"_original_{prop_name}_property"):
            setattr(Player, prop_name, getattr(Player, f"_original_{prop_name}_property"))
            delattr(Player, f"_original_{prop_name}_property")
        elif original_prop is not None:
            # Only restore if it was actually changed (not the same descriptor)
            current_prop = getattr(Player, prop_name, None)
            if current_prop is not original_prop:
                try:
                    setattr(Player, prop_name, original_prop)
                except (AttributeError, TypeError):
                    pass  # Ignore if we can't restore


def pytest_configure(config):
    """Configure pytest for integration tests."""
    # Mark integration tests
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (requires real device)",
    )
    config.addinivalue_line(
        "markers",
        "core: marks tests as core integration tests (fast, safe)",
    )
    config.addinivalue_line(
        "markers",
        "prerelease: marks tests as pre-release integration tests (comprehensive)",
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow (may take longer to run)",
    )
    config.addinivalue_line(
        "markers",
        "destructive: marks tests that change device state (require restoration)",
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark integration tests."""
    for item in items:
        # Mark tests in integration/ directory
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        # Mark tests with "integration" in name
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session")
def real_device_available():
    """Check if a real device is available for integration testing."""
    return WIIM_TEST_DEVICE is not None


@pytest.fixture(scope="session")
def multi_device_available():
    """Check if multi-device group testing is configured."""
    return bool(WIIM_TEST_GROUP_MASTER and WIIM_TEST_GROUP_SLAVES)


@pytest.fixture
def real_device_client(real_device_available):
    """Create a real WiiMClient for integration testing.

    This fixture requires WIIM_TEST_DEVICE environment variable to be set.
    Example: WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/

    Args:
        real_device_available: Fixture that checks if device is available.

    Yields:
        WiiMClient instance connected to real device.

    Raises:
        pytest.skip: If no real device is configured.
    """
    if not real_device_available:
        pytest.skip("No real device configured. Set WIIM_TEST_DEVICE environment variable.")

    from pywiim.client import WiiMClient

    port = 443 if WIIM_TEST_HTTPS else WIIM_TEST_PORT
    client = WiiMClient(host=WIIM_TEST_DEVICE, port=port)

    yield client

    # Cleanup
    import asyncio

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, schedule cleanup
            asyncio.create_task(client.close())
        else:
            loop.run_until_complete(client.close())
    except Exception:
        pass


@pytest.fixture
def integration_test_marker(real_device_available):
    """Fixture to skip integration tests if no device is available."""
    if not real_device_available:
        pytest.skip("Integration tests require WIIM_TEST_DEVICE environment variable")


@pytest.fixture
async def real_device_player(real_device_client, integration_test_marker):
    """Create a Player instance for integration testing.

    This fixture requires WIIM_TEST_DEVICE environment variable to be set.
    Example: WIIM_TEST_DEVICE=192.168.1.100 pytest tests/integration/

    Args:
        real_device_client: Fixture that provides a WiiMClient.
        integration_test_marker: Fixture that ensures device is available.

    Yields:
        Player instance connected to real device.

    Raises:
        pytest.skip: If device is unreachable or connection fails.
    """
    from pywiim.exceptions import WiiMConnectionError, WiiMRequestError
    from pywiim.player import Player

    player = Player(real_device_client)

    # Try to refresh, but handle connection errors gracefully
    try:
        await player.refresh()
    except (WiiMConnectionError, WiiMRequestError) as e:
        error_msg = str(e)
        if "No working protocol/port found" in error_msg or "Connection" in error_msg:
            pytest.skip(
                f"Device at {real_device_client.host} is unreachable or not responding. "
                f"Error: {error_msg}. "
                "Please ensure the device is powered on and accessible on the network."
            )
        raise  # Re-raise other errors

    yield player

    # Cleanup is handled by real_device_client fixture


@pytest.fixture
async def multi_device_players(multi_device_available):
    """Create Player objects for multi-device integration tests.

    Requires:
        WIIM_TEST_GROUP_MASTER - IP/host of the device that will become master
        WIIM_TEST_GROUP_SLAVES - Comma-separated list of slave IP/host values
    """
    if not multi_device_available:
        pytest.skip(
            "Multi-device tests require WIIM_TEST_GROUP_MASTER and WIIM_TEST_GROUP_SLAVES environment variables"
        )

    from pywiim.client import WiiMClient
    from pywiim.player import Player

    def normalize_host(value: str | None) -> str | None:
        if not value:
            return None
        host_only = value.split(":")[0].strip()
        return host_only or None

    def player_finder(host: str | None) -> Player | None:
        normalized = normalize_host(host)
        if not normalized:
            return None
        return registry.get(normalized)

    hosts = [WIIM_TEST_GROUP_MASTER, *WIIM_TEST_GROUP_SLAVES]
    registry: dict[str, Player] = {}
    players: list[Player] = []

    for host in hosts:
        normalized = normalize_host(host)
        if normalized is None:
            raise RuntimeError(f"Invalid host configured for multi-device tests: {host!r}")
        client = WiiMClient(host=host)
        player = Player(client, player_finder=player_finder)
        registry[normalized] = player
        players.append(player)

    if len(players) < 2:
        pytest.skip("Multi-device tests require at least one slave device")

    yield {"master": players[0], "slaves": players[1:], "all": players}

    import asyncio

    await asyncio.gather(*(player.client.close() for player in players), return_exceptions=True)


# ============================================================================
# Helper Functions for Testing
# ============================================================================


def create_mock_response(data: dict[str, Any], status: int = 200) -> MagicMock:
    """Create a mock HTTP response with JSON data.

    Args:
        data: JSON data to return.
        status: HTTP status code.

    Returns:
        Mock ClientResponse object.
    """
    response = MagicMock()
    response.status = status
    response.headers = {"Content-Type": "application/json"}
    response.json = AsyncMock(return_value=data)
    response.text = AsyncMock(return_value=str(data))
    response.read = AsyncMock(return_value=str(data).encode())
    return response


def create_mock_error_response(status: int, message: str = "Error") -> MagicMock:
    """Create a mock HTTP error response.

    Args:
        status: HTTP status code.
        message: Error message.

    Returns:
        Mock ClientResponse object with error.
    """
    response = MagicMock()
    response.status = status
    response.headers = {}
    response.json = AsyncMock(side_effect=Exception(message))
    response.text = AsyncMock(return_value=message)
    response.read = AsyncMock(return_value=message.encode())
    return response
