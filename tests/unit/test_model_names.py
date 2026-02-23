"""Unit tests for model name normalization helpers."""

from __future__ import annotations

from pywiim.model_names import is_known_wiim_model, to_friendly_model_name


class TestIsKnownWiiMModel:
    """Test WiiM raw model identifier detection."""

    def test_known_alias_detected(self):
        """Known raw alias should be recognized."""
        assert is_known_wiim_model("Muzo_Mini") is True

    def test_generic_wiim_prefix_detected(self):
        """Unknown WiiM project variant should still be recognized."""
        assert is_known_wiim_model("WiiM_Pro_with_gc4a") is True

    def test_non_wiim_model_not_detected(self):
        """Non-WiiM project should not be recognized."""
        assert is_known_wiim_model("Audio Pro A10") is False


class TestFriendlyModelName:
    """Test conversion from raw project model to friendly name."""

    def test_muzo_mini_maps_to_wiim_mini(self):
        """Muzo_Mini should map to branding name."""
        assert to_friendly_model_name("Muzo_Mini") == "WiiM Mini"

    def test_amp_variant_maps_to_wiim_amp(self):
        """WiiM amp project variant should map to WiiM Amp."""
        assert to_friendly_model_name("WiiM_Amp_4layer") == "WiiM Amp"

    def test_arylic_model_maps_to_branding_name(self):
        """Known Arylic model should map to friendly branding name."""
        assert to_friendly_model_name("Up2Stream") == "Arylic Up2Stream"

    def test_audio_pro_model_maps_to_branding_name(self):
        """Known Audio Pro model should map to friendly branding name."""
        assert to_friendly_model_name("A10") == "Audio Pro A10"

    def test_unmapped_value_returns_original(self):
        """Unknown model should be returned unchanged."""
        assert to_friendly_model_name("Unknown_Device_ABC") == "Unknown_Device_ABC"
