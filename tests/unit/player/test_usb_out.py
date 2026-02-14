"""Unit tests for USB Output support.

Tests enumeration and selection of USB Output for WiiM Ultra devices.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pywiim.models import DeviceInfo, PlayerStatus
from pywiim.player import Player


class TestUSBOutput:
    """Test USB Output functionality."""

    @pytest.fixture
    def mock_player(self, mock_client):
        """Create a mock Player instance."""
        player = Player(mock_client)
        player._device_info = DeviceInfo(model="WiiM Ultra", project="WiiM Ultra")
        player._status_model = PlayerStatus()
        player._audio_output_status = None
        player._on_state_changed = MagicMock()

        # Mock capabilities to support audio output
        # capabilities is a property that reads from self._capabilities
        player.client._capabilities["supports_audio_output"] = True

        return player

    def test_available_output_modes_includes_usb_out_for_ultra(self, mock_player):
        """Test that available_output_modes includes USB Out for WiiM Ultra."""
        outputs = mock_player.available_output_modes
        assert "USB Out" in outputs
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs
        assert "Headphone Out" in outputs
        # HDMI is input-only on WiiM Ultra (not output) - confirmed via Issue #160
        assert "HDMI Out" not in outputs

    def test_available_output_modes_excludes_usb_out_for_pro(self, mock_player):
        """Test that available_output_modes excludes USB Out for WiiM Pro (non-Amp)."""
        mock_player._device_info = DeviceInfo(model="WiiM Pro", project="WiiM Pro")
        outputs = mock_player.available_output_modes
        assert "USB Out" not in outputs
        assert "Line Out" in outputs
        assert "Optical Out" in outputs
        assert "Coax Out" in outputs

    def test_available_output_modes_includes_usb_out_for_amp(self, mock_player):
        """Test that available_output_modes includes USB Out for WiiM Amp."""
        mock_player._device_info = DeviceInfo(model="WiiM Amp", project="WiiM Amp")
        outputs = mock_player.available_output_modes
        assert "USB Out" in outputs
        assert "Line Out" in outputs
        # Amp doesn't have digital outputs
        assert "Optical Out" not in outputs

    def test_available_output_modes_includes_usb_out_for_amp_pro(self, mock_player):
        """Test that available_output_modes includes USB Out for WiiM Amp Pro."""
        mock_player._device_info = DeviceInfo(model="WiiM Amp Pro", project="WiiM Amp Pro")
        outputs = mock_player.available_output_modes
        assert "USB Out" in outputs
        assert "Line Out" in outputs

    def test_available_output_modes_includes_usb_out_for_amp_ultra(self, mock_player):
        """Test that available_output_modes includes USB Out for WiiM Amp Ultra."""
        mock_player._device_info = DeviceInfo(model="WiiM Amp Ultra", project="WiiM Amp Ultra")
        outputs = mock_player.available_output_modes
        assert "USB Out" in outputs
        assert "Line Out" in outputs
        assert "HDMI Out" in outputs
        # Amp Ultra doesn't have Headphone Out (that's only on WiiM Ultra)
        assert "Headphone Out" not in outputs

    @pytest.mark.asyncio
    async def test_select_output_usb_out(self, mock_player):
        """Test selecting USB Out."""
        mock_player.client.set_audio_output_mode = AsyncMock()
        mock_player.refresh = AsyncMock()

        await mock_player.audio.select_output("USB Out")

        # Should call set_audio_output_mode with friendly name
        mock_player.client.set_audio_output_mode.assert_called_once_with("USB Out")

    def test_audio_output_mode_property_returns_usb_out_mode_8(self, mock_player):
        """Test that audio_output_mode property returns USB Out when mode 8 is active.

        Mode 8 is the confirmed USB Out mode on WiiM Ultra (Issue #160).
        """
        mock_player._audio_output_status = {"hardware": 8, "source": 0}
        assert mock_player.audio_output_mode == "USB Out"

    def test_audio_output_mode_property_returns_usb_out_mode_6_compat(self, mock_player):
        """Test that audio_output_mode property returns USB Out when mode 6 is reported.

        Mode 6 was the originally documented USB mode. Keep backward compat for
        any devices that might report it.
        """
        mock_player._audio_output_status = {"hardware": 6, "source": 0}
        assert mock_player.audio_output_mode == "USB Out"

    def test_audio_output_mode_int_returns_8(self, mock_player):
        """Test that audio_output_mode_int property returns 8 when USB Out is active."""
        mock_player._audio_output_status = {"hardware": 8, "source": 0}
        assert mock_player.audio_output_mode_int == 8
