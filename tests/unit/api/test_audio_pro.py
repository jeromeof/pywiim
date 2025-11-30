"""Unit tests for Audio Pro response handling and normalization.

Tests Audio Pro-specific response variations, string parsing, and field normalization.
"""

from __future__ import annotations

from pywiim.api.audio_pro import (
    _get_audio_pro_defaults,
    normalize_audio_pro_fields,
    normalize_audio_pro_string_response,
    parse_audio_pro_status_string,
    validate_audio_pro_response,
)


class TestValidateAudioProResponse:
    """Test validate_audio_pro_response function."""

    def test_empty_response(self):
        """Test empty response returns defaults."""
        result = validate_audio_pro_response({}, "/httpapi.asp?command=getStatus", "192.168.1.100")
        assert result == _get_audio_pro_defaults("/httpapi.asp?command=getStatus")

    def test_empty_dict_response(self):
        """Test empty dict response returns defaults."""
        result = validate_audio_pro_response({}, "/httpapi.asp?command=getPlayerStatus", "192.168.1.100")
        assert result == _get_audio_pro_defaults("/httpapi.asp?command=getPlayerStatus")

    def test_string_response(self):
        """Test string response is normalized."""
        result = validate_audio_pro_response("OK", "/httpapi.asp?command=setPlayerCmd:play", "192.168.1.100")
        assert result == {"raw": "OK"}

    def test_string_response_with_capabilities(self):
        """Test string response with capabilities includes generation info."""
        capabilities = {"audio_pro_generation": "mkii"}
        result = validate_audio_pro_response(
            "state:play", "/httpapi.asp?command=getStatus", "192.168.1.100", capabilities
        )
        assert "state" in result

    def test_malformed_response(self):
        """Test non-dict, non-string response is handled."""
        result = validate_audio_pro_response(123, "/httpapi.asp?command=getStatus", "192.168.1.100")
        assert result == {"raw": "123"}

    def test_dict_response_normalized(self):
        """Test dict response is normalized."""
        response = {"player_state": "play", "vol": 50, "muted": "1"}
        result = validate_audio_pro_response(response, "/httpapi.asp?command=getStatus", "192.168.1.100")
        assert result["state"] == "play"
        assert result["volume"] == 50
        assert result["mute"] is True

    def test_dict_response_no_changes(self):
        """Test dict response with no normalization needed."""
        response = {"state": "play", "volume": 50, "mute": False}
        result = validate_audio_pro_response(response, "/httpapi.asp?command=getStatus", "192.168.1.100")
        # normalize_audio_pro_fields always adds volume_level
        assert result["state"] == response["state"]
        assert result["volume"] == response["volume"]
        assert result["mute"] == response["mute"]
        assert "volume_level" in result


class TestNormalizeAudioProStringResponse:
    """Test normalize_audio_pro_string_response function."""

    def test_ok_response(self):
        """Test OK response."""
        result = normalize_audio_pro_string_response("OK", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"raw": "OK"}

    def test_ok_lowercase(self):
        """Test ok lowercase response."""
        result = normalize_audio_pro_string_response("ok", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"raw": "OK"}

    def test_error_response(self):
        """Test error response."""
        result = normalize_audio_pro_string_response("error", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"error": "error"}

    def test_failed_response(self):
        """Test failed response."""
        result = normalize_audio_pro_string_response("failed", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"error": "failed"}

    def test_error_in_response(self):
        """Test response containing error."""
        result = normalize_audio_pro_string_response("Command error occurred", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"error": "Command error occurred"}

    def test_not_supported_response(self):
        """Test not supported response."""
        result = normalize_audio_pro_string_response("not supported", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"error": "unsupported_command", "raw": "not supported"}

    def test_unknown_command_response(self):
        """Test unknown command response."""
        result = normalize_audio_pro_string_response("unknown command", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"error": "unsupported_command", "raw": "unknown command"}

    def test_status_endpoint_parses(self):
        """Test status endpoint triggers parsing."""
        result = normalize_audio_pro_string_response("state:play", "/httpapi.asp?command=getStatus")
        assert result["state"] == "play"

    def test_player_status_endpoint_parses(self):
        """Test player status endpoint triggers parsing."""
        result = normalize_audio_pro_string_response("vol:50", "/httpapi.asp?command=getPlayerStatus")
        assert "volume" in result

    def test_non_status_endpoint_raw(self):
        """Test non-status endpoint returns raw."""
        result = normalize_audio_pro_string_response("some response", "/httpapi.asp?command=other")
        assert result == {"raw": "some response"}

    def test_stripped_whitespace(self):
        """Test whitespace is stripped."""
        result = normalize_audio_pro_string_response("  OK  ", "/httpapi.asp?command=setPlayerCmd:play")
        assert result == {"raw": "OK"}


class TestParseAudioProStatusString:
    """Test parse_audio_pro_status_string function."""

    def test_state_field(self):
        """Test state field parsing."""
        result = parse_audio_pro_status_string("state:play")
        assert result["state"] == "play"

    def test_status_field(self):
        """Test status field parsing."""
        result = parse_audio_pro_status_string("status:pause")
        assert result["state"] == "pause"

    def test_player_state_field(self):
        """Test player_state field parsing."""
        result = parse_audio_pro_status_string("player_state:stop")
        assert result["state"] == "stop"

    def test_volume_field(self):
        """Test volume field parsing."""
        result = parse_audio_pro_status_string("vol:75")
        assert result["volume"] == 75
        assert result["volume_level"] == 0.75

    def test_volume_field_name(self):
        """Test volume field name parsing."""
        result = parse_audio_pro_status_string("volume:50")
        assert result["volume"] == 50
        assert result["volume_level"] == 0.5

    def test_volume_invalid_value(self):
        """Test volume with invalid value."""
        result = parse_audio_pro_status_string("vol:invalid")
        assert result["volume"] == "invalid"

    def test_mute_field(self):
        """Test mute field parsing."""
        result = parse_audio_pro_status_string("mute:1")
        assert result["mute"] is True

    def test_muted_field(self):
        """Test muted field parsing."""
        result = parse_audio_pro_status_string("muted:true")
        assert result["mute"] is True

    def test_mute_false(self):
        """Test mute false values."""
        result = parse_audio_pro_status_string("mute:0")
        assert result["mute"] is False

    def test_title_field(self):
        """Test title field parsing."""
        result = parse_audio_pro_status_string("title:Test Song")
        assert result["title"] == "Test Song"

    def test_artist_field(self):
        """Test artist field parsing."""
        result = parse_audio_pro_status_string("artist:Test Artist")
        assert result["artist"] == "Test Artist"

    def test_album_field(self):
        """Test album field parsing."""
        result = parse_audio_pro_status_string("album:Test Album")
        assert result["album"] == "Test Album"

    def test_unknown_field(self):
        """Test unknown field is preserved."""
        result = parse_audio_pro_status_string("custom:value")
        assert result["custom"] == "value"

    def test_colon_in_value(self):
        """Test colon in value is preserved."""
        result = parse_audio_pro_status_string("title:Artist - Title")
        assert result["title"] == "Artist - Title"

    def test_no_colon(self):
        """Test response without colon returns default."""
        result = parse_audio_pro_status_string("no colon here")
        assert result["state"] == "unknown"
        assert result["raw"] == "no colon here"

    def test_empty_string(self):
        """Test empty string returns default."""
        result = parse_audio_pro_status_string("")
        assert result["state"] == "unknown"
        assert result["raw"] == ""


class TestNormalizeAudioProFields:
    """Test normalize_audio_pro_fields function."""

    def test_player_state_mapping(self):
        """Test player_state maps to state."""
        result = normalize_audio_pro_fields({"player_state": "play"}, "/httpapi.asp?command=getStatus")
        assert result["state"] == "play"
        assert "player_state" not in result

    def test_play_status_mapping(self):
        """Test play_status maps to state."""
        result = normalize_audio_pro_fields({"play_status": "pause"}, "/httpapi.asp?command=getStatus")
        assert result["state"] == "pause"

    def test_vol_mapping(self):
        """Test vol maps to volume."""
        result = normalize_audio_pro_fields({"vol": 50}, "/httpapi.asp?command=getStatus")
        assert result["volume"] == 50

    def test_muted_mapping(self):
        """Test muted maps to mute."""
        result = normalize_audio_pro_fields({"muted": "1"}, "/httpapi.asp?command=getStatus")
        assert result["mute"] is True

    def test_device_name_mapping(self):
        """Test device_name maps to DeviceName."""
        result = normalize_audio_pro_fields({"device_name": "Test Device"}, "/httpapi.asp?command=getStatus")
        assert result["DeviceName"] == "Test Device"

    def test_friendly_name_mapping(self):
        """Test friendly_name maps to DeviceName."""
        result = normalize_audio_pro_fields({"friendly_name": "Test Device"}, "/httpapi.asp?command=getStatus")
        assert result["DeviceName"] == "Test Device"

    def test_volume_normalization_0_100(self):
        """Test volume > 1 is normalized to 0-1 range."""
        result = normalize_audio_pro_fields({"volume": 75}, "/httpapi.asp?command=getStatus")
        assert result["volume"] == 75
        assert result["volume_level"] == 0.75

    def test_volume_normalization_0_1(self):
        """Test volume <= 1 stays as is."""
        result = normalize_audio_pro_fields({"volume": 0.5}, "/httpapi.asp?command=getStatus")
        assert result["volume"] == 0.5
        assert result["volume_level"] == 0.5

    def test_mute_string_true(self):
        """Test mute string true values."""
        for value in ["1", "true", "on", "yes"]:
            result = normalize_audio_pro_fields({"mute": value}, "/httpapi.asp?command=getStatus")
            assert result["mute"] is True

    def test_mute_string_false(self):
        """Test mute string false values."""
        for value in ["0", "false", "off", "no"]:
            result = normalize_audio_pro_fields({"mute": value}, "/httpapi.asp?command=getStatus")
            assert result["mute"] is False

    def test_mute_int(self):
        """Test mute integer values."""
        result = normalize_audio_pro_fields({"mute": 1}, "/httpapi.asp?command=getStatus")
        assert result["mute"] is True

        result = normalize_audio_pro_fields({"mute": 0}, "/httpapi.asp?command=getStatus")
        assert result["mute"] is False

    def test_no_changes_needed(self):
        """Test response with no changes needed."""
        response = {"state": "play", "volume": 50, "mute": False}
        result = normalize_audio_pro_fields(response, "/httpapi.asp?command=getStatus")
        # normalize_audio_pro_fields always adds volume_level
        assert result["state"] == response["state"]
        assert result["volume"] == response["volume"]
        assert result["mute"] == response["mute"]
        assert "volume_level" in result


class TestGetAudioProDefaults:
    """Test _get_audio_pro_defaults function."""

    def test_getslavelist_endpoint(self):
        """Test getSlaveList endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=multiroom:getSlaveList")
        assert result == {"slaves": 0, "slave_list": []}

    def test_getstatus_endpoint(self):
        """Test getStatus endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=getStatus")
        assert result["group"] == "0"
        assert result["state"] == "stop"
        assert result["volume"] == 30
        assert result["volume_level"] == 0.3
        assert result["mute"] is False

    def test_getplayerstatus_endpoint(self):
        """Test getPlayerStatus endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=getPlayerStatus")
        assert result["state"] == "stop"
        assert result["volume"] == 30

    def test_getmetainfo_endpoint(self):
        """Test getMetaInfo endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=getMetaInfo")
        assert result == {"title": "", "artist": "", "album": ""}

    def test_getdeviceinfo_endpoint(self):
        """Test getDeviceInfo endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=getDeviceInfo")
        assert result["DeviceName"] == "Audio Pro Speaker"
        assert result["state"] == "stop"

    def test_getstatusex_endpoint(self):
        """Test getStatusEx endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=getStatusEx")
        # getStatusEx uses same defaults as getDeviceInfo
        assert "DeviceName" in result or "state" in result
        if "DeviceName" in result:
            assert result["DeviceName"] == "Audio Pro Speaker"
        if "state" in result:
            assert result["state"] == "stop"

    def test_other_endpoint(self):
        """Test other endpoint defaults."""
        result = _get_audio_pro_defaults("/httpapi.asp?command=other")
        assert result == {"raw": "OK"}
