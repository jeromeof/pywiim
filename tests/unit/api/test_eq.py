"""Unit tests for EQAPI mixin.

Tests equalizer presets, custom EQ bands, and enable/disable functionality.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pywiim.exceptions import WiiMError


class TestEQAPIPresets:
    """Test EQAPI preset methods."""

    @pytest.mark.asyncio
    async def test_set_eq_preset(self, mock_client):
        """Test setting EQ preset."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("rock")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_preset_invalid(self, mock_client):
        """Test setting invalid EQ preset."""
        with pytest.raises(ValueError, match="Invalid EQ preset"):
            await mock_client.set_eq_preset("invalid_preset")

    @pytest.mark.asyncio
    async def test_set_eq_preset_normalization_spaces(self, mock_client):
        """Test setting EQ preset with spaces (e.g., 'bass reducer')."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("bass reducer")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]
        assert "Bass Reducer" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_preset_normalization_typo(self, mock_client):
        """Test setting EQ preset with typo (e.g., 'base reducer' -> 'bass reducer')."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("base reducer")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]
        assert "Bass Reducer" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_preset_normalization_display_name(self, mock_client):
        """Test setting EQ preset with display name (e.g., 'Bass Reducer')."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("Bass Reducer")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]
        assert "Bass Reducer" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_preset_normalization_underscore(self, mock_client):
        """Test setting EQ preset with underscore (e.g., 'bass_reducer')."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("bass_reducer")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]
        assert "Bass Reducer" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_preset_normalization_hyphen(self, mock_client):
        """Test setting EQ preset with hyphen (e.g., 'bass-reducer')."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_preset("bass-reducer")

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQLoad:" in call_args[0]
        assert "Bass Reducer" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_eq_presets(self, mock_client):
        """Test getting EQ presets list."""
        mock_presets = ["flat", "rock", "pop", "jazz", "classical"]
        mock_client._request = AsyncMock(return_value=mock_presets)

        result = await mock_client.get_eq_presets()

        assert result == mock_presets

    @pytest.mark.asyncio
    async def test_get_eq_presets_non_list(self, mock_client):
        """Test getting presets when response is not a list."""
        mock_client._request = AsyncMock(return_value={"error": "not found"})

        result = await mock_client.get_eq_presets()

        assert result == []


class TestEQAPICustom:
    """Test EQAPI custom EQ band methods."""

    @pytest.mark.asyncio
    async def test_set_eq_custom(self, mock_client):
        """Test setting custom 10-band EQ."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})
        eq_values = [0, 2, 4, 6, 8, 10, 8, 6, 4, 2]

        await mock_client.set_eq_custom(eq_values)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "0,2,4,6,8,10,8,6,4,2" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_custom_wrong_length(self, mock_client):
        """Test setting custom EQ with wrong number of bands."""
        with pytest.raises(ValueError, match="EQ must have exactly 10 bands"):
            await mock_client.set_eq_custom([1, 2, 3])  # Too few

        with pytest.raises(ValueError, match="EQ must have exactly 10 bands"):
            await mock_client.set_eq_custom([1] * 15)  # Too many

    @pytest.mark.asyncio
    async def test_get_eq(self, mock_client):
        """Test getting current EQ band values."""
        mock_eq = {
            "band1": 0,
            "band2": 2,
            "band3": 4,
            "band4": 6,
            "band5": 8,
            "band6": 10,
            "band7": 8,
            "band8": 6,
            "band9": 4,
            "band10": 2,
        }
        mock_client._request = AsyncMock(return_value=mock_eq)

        result = await mock_client.get_eq()

        assert result == mock_eq


class TestEQAPIEnableDisable:
    """Test EQAPI enable/disable methods."""

    @pytest.mark.asyncio
    async def test_set_eq_enabled_true(self, mock_client):
        """Test enabling EQ."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_enabled(True)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQOn" in call_args[0]

    @pytest.mark.asyncio
    async def test_set_eq_enabled_false(self, mock_client):
        """Test disabling EQ."""
        mock_client._request = AsyncMock(return_value={"raw": "OK"})

        await mock_client.set_eq_enabled(False)

        mock_client._request.assert_called_once()
        call_args = mock_client._request.call_args[0]
        assert "/httpapi.asp?command=EQOff" in call_args[0]

    @pytest.mark.asyncio
    async def test_get_eq_status_enabled(self, mock_client):
        """Test getting EQ status when enabled."""
        mock_client._request = AsyncMock(return_value={"EQStat": "on"})

        result = await mock_client.get_eq_status()

        assert result is True

    @pytest.mark.asyncio
    async def test_get_eq_status_disabled(self, mock_client):
        """Test getting EQ status when disabled."""
        mock_client._request = AsyncMock(return_value={"EQStat": "off"})

        result = await mock_client.get_eq_status()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_eq_status_fallback_to_get(self, mock_client):
        """Test EQ status fallback to get_eq when status endpoint fails."""
        # First call fails, second succeeds
        mock_client._request = AsyncMock(
            side_effect=[
                {"status": "failed"},  # EQStatus returns failed
                {"status": "OK", "band1": 0},  # EQGet succeeds
            ]
        )

        result = await mock_client.get_eq_status()

        assert result is True
        assert mock_client._request.call_count == 2

    @pytest.mark.asyncio
    async def test_get_eq_status_fallback_fails(self, mock_client):
        """Test EQ status when both status and get fail."""
        mock_client._request = AsyncMock(side_effect=WiiMError("Failed"))

        result = await mock_client.get_eq_status()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_eq_status_fallback_invalid_response(self, mock_client):
        """Test EQ status when fallback returns invalid response."""
        mock_client._request = AsyncMock(
            side_effect=[
                {"status": "failed"},
                {"status": "error"},  # Not "OK"
            ]
        )

        result = await mock_client.get_eq_status()

        assert result is False

    @pytest.mark.asyncio
    async def test_get_eq_status_exception_in_fallback(self, mock_client):
        """Test EQ status when exception occurs in fallback."""
        mock_client._request = AsyncMock(
            side_effect=[
                {"status": "failed"},
                Exception("Error"),  # Exception in fallback
            ]
        )

        result = await mock_client.get_eq_status()

        assert result is False
