"""Unit tests for role detection.

Tests detect_role function and RoleDetectionResult.
"""

from __future__ import annotations

from pywiim.models import DeviceInfo, PlayerStatus
from pywiim.role import RoleDetectionResult, detect_role


class TestRoleDetectionResult:
    """Test RoleDetectionResult class."""

    def test_init(self):
        """Test RoleDetectionResult initialization."""
        result = RoleDetectionResult(
            role="master",
            master_host="192.168.1.100",
            master_uuid="master-uuid",
            slave_hosts=["192.168.1.101"],
            slave_count=1,
        )

        assert result.role == "master"
        assert result.master_host == "192.168.1.100"
        assert result.master_uuid == "master-uuid"
        assert result.slave_hosts == ["192.168.1.101"]
        assert result.slave_count == 1

    def test_init_minimal(self):
        """Test RoleDetectionResult with minimal args."""
        result = RoleDetectionResult(role="solo")

        assert result.role == "solo"
        assert result.master_host is None
        assert result.slave_hosts == []
        assert result.slave_count == 0


class TestDetectRoleEnhanced:
    """Test role detection for enhanced firmware (WiiM devices)."""

    def test_detect_master(self):
        """Test detecting master role."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 2, "slave_list": [{"ip": "192.168.1.101"}, {"ip": "192.168.1.102"}]}
        device_info = DeviceInfo(uuid="master-uuid", group="1")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "master"
        assert result.slave_count == 2
        assert len(result.slave_hosts) == 2

    def test_detect_slave(self):
        """Test detecting slave role."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="slave-uuid", group="1", master_uuid="master-uuid", master_ip="192.168.1.100")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "slave"
        assert result.master_uuid == "master-uuid"
        assert result.master_host == "192.168.1.100"

    def test_detect_solo(self):
        """Test detecting solo role."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="0")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "solo"
        assert result.master_host is None
        assert result.slave_count == 0

    def test_detect_follower_mode_99_playing(self):
        """Test detecting follower mode (mode=99) while playing."""
        status = PlayerStatus(play_state="play", mode="99")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="0")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "slave"  # Follower treated as slave while playing

    def test_detect_follower_mode_99_not_playing(self):
        """Test detecting follower mode (mode=99) when not playing."""
        status = PlayerStatus(play_state="stop", mode="99")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="0")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "solo"  # Follower treated as solo when not playing

    def test_detect_slave_missing_master_info(self):
        """Test detecting slave when master info is missing."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="1")  # In group but no master info

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": False})

        assert result.role == "solo"  # Treat as solo to avoid breaking controls

    def test_detect_master_slave_list_as_int(self):
        """Test detecting master when slave_list is an integer."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 2, "slave_list": 2}  # slave_list is int, not list

        result = detect_role(status, multiroom, None, capabilities={"is_legacy_device": False})

        assert result.role == "master"
        assert result.slave_count == 2


class TestDetectRoleLegacy:
    """Test role detection for legacy firmware (Audio Pro devices)."""

    def test_detect_master_legacy(self):
        """Test detecting master role on legacy device."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 1, "slave_list": [{"ip": "192.168.1.101"}]}
        device_info = DeviceInfo(uuid="master-uuid", group="1")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": True})

        assert result.role == "master"
        assert result.slave_count == 1

    def test_detect_slave_legacy(self):
        """Test detecting slave role on legacy device."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="slave-uuid", group="1", master_uuid="master-uuid")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": True})

        assert result.role == "slave"
        assert result.master_uuid == "master-uuid"

    def test_detect_solo_legacy(self):
        """Test detecting solo role on legacy device."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="0")

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": True})

        assert result.role == "solo"

    def test_detect_ambiguous_legacy(self):
        """Test detecting ambiguous state on legacy device."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="unknown")  # Invalid group value

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": True})

        assert result.role == "solo"  # Treat as solo for safety

    def test_detect_slave_legacy_no_master_uuid(self):
        """Test detecting slave on legacy device without master UUID."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="1")  # In group but no master_uuid

        result = detect_role(status, multiroom, device_info, capabilities={"is_legacy_device": True})

        assert result.role == "solo"  # Legacy requires master_uuid for slave detection


class TestDetectRoleEdgeCases:
    """Test role detection edge cases."""

    def test_detect_role_no_device_info(self):
        """Test role detection without device info."""
        status = PlayerStatus(play_state="play", group="0")
        multiroom = {"slaves": 0}

        result = detect_role(status, multiroom, None, capabilities={"is_legacy_device": False})

        assert result.role == "solo"

    def test_detect_role_no_capabilities(self):
        """Test role detection without capabilities."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": 0}
        device_info = DeviceInfo(uuid="device-uuid", group="0")

        result = detect_role(status, multiroom, device_info, capabilities=None)

        # Should default to enhanced firmware detection
        assert result.role == "solo"

    def test_detect_role_slaves_as_list(self):
        """Test role detection when slaves is a list."""
        status = PlayerStatus(play_state="play")
        multiroom = {"slaves": [{"ip": "192.168.1.101"}], "slave_list": []}

        result = detect_role(status, multiroom, None, capabilities={"is_legacy_device": False})

        assert result.role == "master"
        assert result.slave_count == 1

    def test_detect_role_slave_list_extraction(self):
        """Test extracting slave IPs from slave list."""
        status = PlayerStatus(play_state="play")
        multiroom = {
            "slaves": 2,
            "slave_list": [
                {"ip": "192.168.1.101", "name": "Slave 1"},
                {"ip": "192.168.1.102", "name": "Slave 2"},
            ],
        }

        result = detect_role(status, multiroom, None, capabilities={"is_legacy_device": False})

        assert result.role == "master"
        assert "192.168.1.101" in result.slave_hosts
        assert "192.168.1.102" in result.slave_hosts
