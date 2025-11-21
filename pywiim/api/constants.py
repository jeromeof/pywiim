"""WiiM API constants and mappings.

This module contains all API endpoint paths, field mappings, and SSL certificates
used for communicating with WiiM and LinkPlay devices.
"""

from __future__ import annotations

# SSL Certificate for WiiM devices (self-signed CA certificate)
WIIM_CA_CERT = """-----BEGIN CERTIFICATE-----
MIIDmDCCAoACAQEwDQYJKoZIhvcNAQELBQAwgZExCzAJBgNVBAYTAkNOMREwDwYD
VQQIDAhTaGFuZ2hhaTERMA8GA1UEBwwIU2hhbmdoYWkxETAPBgNVBAoMCExpbmtw
bGF5MQwwCgYDVQQLDANpbmMxGTAXBgNVBAMMEHd3dy5saW5rcGxheS5jb20xIDAe
BgkqhkiG9w0BCQEWEW1haWxAbGlua3BsYXkuY29tMB4XDTE4MTExNTAzMzI1OVoX
DTQ2MDQwMTAzMzI1OVowgZExCzAJBgNVBAYTAkNOMREwDwYDVQQIDAhTaGFuZ2hh
aTERMA8GA1UEBwwIU2hhbmdoYWkxETAPBgNVBAoMCExpbmtwbGF5MQwwCgYDVQQL
DANpbmMxGTAXBgNVBAMMEHd3dy5saW5rcGxheS5jb20xIDAeBgkqhkiG9w0BCQEW
EW1haWxAbGlua3BsYXkuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEApP7trR9C8Ajr/CZqi70HYzQHZMX0gj8K3RzO0k5aucWiRkHtvcnfJIz+4dMB
EZHjv/STutsFBwbtD1iLEv48Cxvht6AFPuwTX45gYQ18hyEUC8wFhG7cW7Ek5HtZ
aLH75UFxrpl6zKn/Vy3SGL2wOd5qfBiJkGyZGgg78JxHVBZLidFuU6H6+fIyanwr
ejj8B5pz+KAui6T7SWA8u69UPbC4AmBLQxMPzIX/pirgtKZ7LedntanHlY7wrlAa
HroZOpKZxG6UnRCmw23RPHD6FUZq49f/zyxTFbTQe5NmjzG9wnKCf3R8Wgl8JPW9
4yAbOgslosTfdgrmjkPfFIP2JQIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQARmy6f
esrifhW5NM9i3xsEVp945iSXhqHgrtIROgrC7F1EIAyoIiBdaOvitZVtsYc7Ivys
QtyVmEGscyjuYTdfigvwTVVj2oCeFv1Xjf+t/kSuk6X3XYzaxPPnFG4nAe2VwghE
rbZG0K5l8iXM7Lm+ZdqQaAYVWsQDBG8lbczgkB9q5ed4zbDPf6Fsrsynxji/+xa4
9ARfyHlkCDBThGNnnl+QITtfOWxm/+eReILUQjhwX+UwbY07q/nUxLlK6yrzyjnn
wi2B2GovofQ/4icVZ3ecTqYK3q9gEtJi72V+dVHM9kSA4Upy28Y0U1v56uoqeWQ6
uc2m8y8O/hXPSfKd
-----END CERTIFICATE-----"""

# Audio Pro Client Certificate for Audio Pro MkII mutual TLS authentication
# Required for Audio Pro MkII/W-Series devices on port 4443
# Source: https://github.com/ramikg/linkplay-cli/blob/master/linkplay_cli/certs/linkplay_client.pem
# Original source: https://github.com/osk2/yamaha-soundbar/blob/master/custom_components/yamaha_soundbar/client.pem
#
# This certificate enables mutual TLS (mTLS) authentication with Audio Pro MkII devices
# Certificate issued by LinkPlay (www.linkplay.com) for client authentication
AUDIO_PRO_CLIENT_CERT = """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQCk/u2tH0LwCOv8
JmqLvQdjNAdkxfSCPwrdHM7STlq5xaJGQe29yd8kjP7h0wERkeO/9JO62wUHBu0P
WIsS/jwLG+G3oAU+7BNfjmBhDXyHIRQLzAWEbtxbsSTke1losfvlQXGumXrMqf9X
LdIYvbA53mp8GImQbJkaCDvwnEdUFkuJ0W5Tofr58jJqfCt6OPwHmnP4oC6LpPtJ
YDy7r1Q9sLgCYEtDEw/Mhf+mKuC0pnst52e1qceVjvCuUBoeuhk6kpnEbpSdEKbD
bdE8cPoVRmrj1//PLFMVtNB7k2aPMb3CcoJ/dHxaCXwk9b3jIBs6CyWixN92CuaO
Q98Ug/YlAgMBAAECggEAHyCpHlwjeL12J9/nge1rk1+hdXWTJ29VUVm5+xslKp8K
ek6912xaWL7w5xGzxejMGs69gCcJz8WSu65srmygT0g3UTkzRCetj/2AWU7+C1BG
Q+N9tvpjQDkvSJusxn+tkhbCp7n03N/FeGEAngJLWN+JH1hRu5mBWNPs2vvgyRAO
Cv95G7uENavCUXcyYsKPoAfz3ebD/idwwWW2RKAd0ufYeafiFC0ImTLcpEjBvCTW
UoAniBSVx1PHK4IAUb3pMdPtIv1uBlIMotHS/GdEyHU6qOsX5ijHqncHHneaytmL
+wJukPqASEBl3F2UnzryBUgGqr1wyH9vtPGjklnngQKBgQDZv3oxZWul//2LV+jo
ZipbnP6nwG3J6pOWPDD3dHoZ6Q2DRyJXN5ty40PS393GVvrSJSdRGeD9+ox5sFoj
iUMgd6kHG4ME7Fre57zUkqy1Ln1K1fkP5tBUD0hviigHBWih2/Nyl2vrdvX5Wpxx
5r42UQa9nOzrNB03DTOhDrUszQKBgQDB+xdMRNSFfCatQj+y2KehcH9kaANPvT0l
l9vgb72qks01h05GSPBZnT1qfndh/Myno9KuVPhJ0HrVwRAjZTd4T69fAH3imW+R
7HP+RgDen4SRTxj6UTJh2KZ8fdPeCby1xTwxYNjq8HqpiO6FHZpE+l4FE8FalZK+
Z3GhE7DuuQKBgDq7b+0U6xVKWAwWuSa+L9yoGvQKblKRKB/Uumx0iV6lwtRPAo89
23sAm9GsOnh+C4dVKCay8UHwK6XDEH0XT/jY7cmR/SP90IDhRsibi2QPVxIxZs2I
N1cFDEexnxxNtCw8VIzrFNvdKXmJnDsIvvONpWDNjAXg96RatjtR6UJdAoGBAIAx
HU5r1j54s16gf1QD1ZPcsnN6QWX622PynX4OmjsVVMPhLRtJrHysax/rf52j4OOQ
YfSPdp3hRqvoMHATvbqmfnC79HVBjPfUWTtaq8xzgro8mXcjHbaH5E41IUSFDs7Z
D1Raej+YuJc9RNN3orGe+29DhO4GFrn5xp/6UV0RAoGBAKUdRgryWzaN4auzWaRD
lxoMhlwQdCXzBI1YLH2QUL8elJOHMNfmja5G9iW07ZrhhvQBGNDXFbFrX4hI3c/0
JC3SPhaaedIjOe9Qd3tn5KgYxbBnWnCTt0kxgro+OM3ORgJseSWbKdRrjOkUxkab
/NDvel7IF63U4UEkrVVt1bYg
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDmDCCAoACAQEwDQYJKoZIhvcNAQELBQAwgZExCzAJBgNVBAYTAkNOMREwDwYD
VQQIDAhTaGFuZ2hhaTERMA8GA1UEBwwIU2hhbmdoYWkxETAPBgNVBAoMCExpbmtw
bGF5MQwwCgYDVQQLDANpbmMxGTAXBgNVBAMMEHd3dy5saW5rcGxheS5jb20xIDAe
BgkqhkiG9w0BCQEWEW1haWxAbGlua3BsYXkuY29tMB4XDTE4MTExNTAzMzI1OVoX
DTQ2MDQwMTAzMzI1OVowgZExCzAJBgNVBAYTAkNOMREwDwYDVQQIDAhTaGFuZ2hh
aTERMA8GA1UEBwwIU2hhbmdoYWkxETAPBgNVBAoMCExpbmtwbGF5MQwwCgYDVQQL
DANpbmMxGTAXBgNVBAMMEHd3dy5saW5rcGxheS5jb20xIDAeBgkqhkiG9w0BCQEW
EW1haWxAbGlua3BsYXkuY29tMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKC
AQEApP7trR9C8Ajr/CZqi70HYzQHZMX0gj8K3RzO0k5aucWiRkHtvcnfJIz+4dMB
EZHjv/STutsFBwbtD1iLEv48Cxvht6AFPuwTX45gYQ18hyEUC8wFhG7cW7Ek5HtZ
aLH75UFxrpl6zKn/Vy3SGL2wOd5qfBiJkGyZGgg78JxHVBZLidFuU6H6+fIyanwr
ejj8B5pz+KAui6T7SWA8u69UPbC4AmBLQxMPzIX/pirgtKZ7LedntanHlY7wrlAa
HroZOpKZxG6UnRCmw23RPHD6FUZq49f/zyxTFbTQe5NmjzG9wnKCf3R8Wgl8JPW9
4yAbOgslosTfdgrmjkPfFIP2JQIDAQABMA0GCSqGSIb3DQEBCwUAA4IBAQARmy6f
esrifhW5NM9i3xsEVp945iSXhqHgrtIROgrC7F1EIAyoIiBdaOvitZVtsYc7Ivys
QtyVmEGscyjuYTdfigvwTVVj2oCeFv1Xjf+t/kSuk6X3XYzaxPPnFG4nAe2VwghE
rbZG0K5l8iXM7Lm+ZdqQaAYVWsQDBG8lbczgkB9q5ed4zbDPf6Fsrsynxji/+xa4
9ARfyHlkCDBThGNnnl+QITtfOWxm/+eReILUQjhwX+UwbY07q/nUxLlK6yrzyjnn
wi2B2GovofQ/4icVZ3ecTqYK3q9gEtJi72V+dVHM9kSA4Upy28Y0U1v56uoqeWQ6
uc2m8y8O/hXPSfKd
-----END CERTIFICATE-----"""

# Status field mapping for parser
# Maps API response keys to model field names
STATUS_MAP: dict[str, str] = {
    "status": "play_status",
    "state": "play_status",
    "player_state": "play_status",
    "vol": "volume",
    "mute": "mute",
    "eq": "eq_preset",
    "EQ": "eq_preset",
    "eq_mode": "eq_preset",
    "loop": "loop_mode",
    "curpos": "position_ms",
    "totlen": "duration_ms",
    "Title": "title_hex",
    "Artist": "artist_hex",
    "Album": "album_hex",
    "DeviceName": "device_name",
    "uuid": "uuid",
    "ssid": "ssid",
    "MAC": "mac_address",
    "firmware": "firmware",
    "project": "project",
    "WifiChannel": "wifi_channel",
    "RSSI": "wifi_rssi",
}

# Mode value mapping
# Maps numeric mode values to source names
MODE_MAP: dict[str, str] = {
    "0": "idle",
    "1": "airplay",
    "2": "dlna",
    "3": "wifi",
    "4": "line_in",
    "5": "bluetooth",
    "6": "optical",
    "10": "wifi",
    "11": "usb",
    "20": "wifi",
    "31": "spotify",
    "36": "qobuz",
    "40": "line_in",
    "41": "bluetooth",
    "43": "optical",
    "47": "line_in_2",
    "49": "hdmi",
    "51": "usb",
    "99": "follower",
}

# Embedded PyWiim logo (PNG format) - used as fallback when no cover art is available
# Size: 7977 bytes (7.79 KB) - Original WiiM logo from mjcumming/wiim integration
# This is returned directly as bytes when fetch_cover_art() is called with no artwork
# No URL fetching needed - just decode base64 and serve the embedded image
EMBEDDED_LOGO_BASE64 = (
    "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"
)

# For backward compatibility - can be set to None or empty string since we serve bytes directly
DEFAULT_WIIM_LOGO_URL = None  # No URL needed - logo is embedded

# EQ preset numeric mapping
# Maps numeric EQ preset values to preset names
# EQ Preset names
EQ_PRESET_FLAT = "flat"
EQ_PRESET_ACOUSTIC = "acoustic"
EQ_PRESET_BASS = "bass"
EQ_PRESET_BASSBOOST = "bassboost"
EQ_PRESET_BASSREDUCER = "bassreducer"
EQ_PRESET_CLASSICAL = "classical"
EQ_PRESET_DANCE = "dance"
EQ_PRESET_DEEP = "deep"
EQ_PRESET_ELECTRONIC = "electronic"
EQ_PRESET_HIPHOP = "hiphop"
EQ_PRESET_JAZZ = "jazz"
EQ_PRESET_LOUDNESS = "loudness"
EQ_PRESET_POP = "pop"
EQ_PRESET_ROCK = "rock"
EQ_PRESET_TREBLE = "treble"
EQ_PRESET_VOCAL = "vocal"
EQ_PRESET_CUSTOM = "custom"

# EQ Preset mapping (preset name -> display name)
EQ_PRESET_MAP: dict[str, str] = {
    EQ_PRESET_FLAT: "Flat",
    EQ_PRESET_ACOUSTIC: "Acoustic",
    EQ_PRESET_BASS: "Bass",
    EQ_PRESET_BASSBOOST: "Bass Booster",
    EQ_PRESET_BASSREDUCER: "Bass Reducer",
    EQ_PRESET_CLASSICAL: "Classical",
    EQ_PRESET_DANCE: "Dance",
    EQ_PRESET_DEEP: "Deep",
    EQ_PRESET_ELECTRONIC: "Electronic",
    EQ_PRESET_HIPHOP: "Hip-Hop",
    EQ_PRESET_JAZZ: "Jazz",
    EQ_PRESET_LOUDNESS: "Loudness",
    EQ_PRESET_POP: "Pop",
    EQ_PRESET_ROCK: "Rock",
    EQ_PRESET_TREBLE: "Treble",
    EQ_PRESET_VOCAL: "Vocal",
    EQ_PRESET_CUSTOM: "Custom",
}

EQ_NUMERIC_MAP: dict[str, str] = {
    "0": "flat",
    "1": "pop",
    "2": "rock",
    "3": "jazz",
    "4": "classical",
    "5": "bass",
    "6": "treble",
    "7": "vocal",
    "8": "loudness",
    "9": "dance",
    "10": "acoustic",
    "11": "electronic",
    "12": "deep",
}

# Vendor identifiers
VENDOR_WIIM = "wiim"
VENDOR_ARYLIC = "arylic"
VENDOR_AUDIO_PRO = "audio_pro"
VENDOR_LINKPLAY_GENERIC = "linkplay_generic"

# Default connection settings
DEFAULT_PORT = 443  # HTTPS port
DEFAULT_TIMEOUT = 5.0  # seconds

# Play mode constants
PLAY_MODE_NORMAL = "normal"
PLAY_MODE_REPEAT_ALL = "repeat_all"
PLAY_MODE_REPEAT_ONE = "repeat_one"
PLAY_MODE_SHUFFLE = "shuffle"
PLAY_MODE_SHUFFLE_REPEAT_ALL = "shuffle_repeat_all"

# API endpoint paths
# All endpoints use the /httpapi.asp base path with command parameter
API_ENDPOINT_STATUS = "/httpapi.asp?command=getStatusEx"
API_ENDPOINT_PLAYER_STATUS = "/httpapi.asp?command=getPlayerStatusEx"
API_ENDPOINT_METADATA = "/httpapi.asp?command=getMetaInfo"

# Player control endpoints
API_ENDPOINT_PLAY = "/httpapi.asp?command=setPlayerCmd:play"
API_ENDPOINT_PAUSE = "/httpapi.asp?command=setPlayerCmd:pause"
API_ENDPOINT_STOP = "/httpapi.asp?command=setPlayerCmd:stop"
API_ENDPOINT_NEXT = "/httpapi.asp?command=setPlayerCmd:next"
API_ENDPOINT_PREV = "/httpapi.asp?command=setPlayerCmd:prev"
API_ENDPOINT_VOLUME = "/httpapi.asp?command=setPlayerCmd:vol:"
API_ENDPOINT_MUTE = "/httpapi.asp?command=setPlayerCmd:mute:"
API_ENDPOINT_SEEK = "/httpapi.asp?command=setPlayerCmd:seek:"
API_ENDPOINT_LOOPMODE = "/httpapi.asp?command=setLoopMode:"
API_ENDPOINT_SOURCE = "/httpapi.asp?command=switchmode:"

# Device info endpoints
API_ENDPOINT_DEVICE_INFO = "/httpapi.asp?command=getDeviceInfo"
API_ENDPOINT_FIRMWARE = "/httpapi.asp?command=getFirmwareVersion"

# Multiroom endpoints
API_ENDPOINT_GROUP_SLAVES = "/httpapi.asp?command=multiroom:getSlaveList"
API_ENDPOINT_GROUP_EXIT = "/httpapi.asp?command=multiroom:Ungroup"
API_ENDPOINT_GROUP_KICK = "/httpapi.asp?command=multiroom:SlaveKickout:"
API_ENDPOINT_GROUP_SLAVE_MUTE = "/httpapi.asp?command=multiroom:SlaveMute:"
API_ENDPOINT_GROUP_SLAVE_VOLUME = "/httpapi.asp?command=multiroom:SlaveVolume:"

# EQ endpoints
API_ENDPOINT_EQ_GET = "/httpapi.asp?command=EQGetBand"
API_ENDPOINT_EQ_STATUS = "/httpapi.asp?command=EQGetStat"
API_ENDPOINT_EQ_LIST = "/httpapi.asp?command=EQGetList"
API_ENDPOINT_EQ_PRESET = "/httpapi.asp?command=EQLoad:"
API_ENDPOINT_EQ_CUSTOM = "/httpapi.asp?command=EQSetBand:"
API_ENDPOINT_EQ_ON = "/httpapi.asp?command=EQOn"
API_ENDPOINT_EQ_OFF = "/httpapi.asp?command=EQOff"

# Preset endpoints
API_ENDPOINT_PRESET_INFO = "/httpapi.asp?command=getPresetInfo"
API_ENDPOINT_PRESET = "/httpapi.asp?command=MCUKeyShortClick:"

# Device info endpoints
API_ENDPOINT_MAC = "/httpapi.asp?command=getMAC"

# Playback control endpoints
API_ENDPOINT_RESUME = "/httpapi.asp?command=setPlayerCmd:resume"
API_ENDPOINT_CLEAR_PLAYLIST = "/httpapi.asp?command=setPlayerCmd:clear_playlist"
API_ENDPOINT_PLAY_URL = "/httpapi.asp?command=setPlayerCmd:play:"
API_ENDPOINT_PLAY_M3U = "/httpapi.asp?command=setPlayerCmd:playlist:"
API_ENDPOINT_PLAY_PROMPT_URL = "/httpapi.asp?command=playPromptUrl:"

# Audio settings endpoints
API_ENDPOINT_GET_SPDIF_SAMPLE_RATE = "/httpapi.asp?command=getSpdifOutSampleRate"
API_ENDPOINT_SET_SPDIF_SWITCH_DELAY = "/httpapi.asp?command=setSpdifOutSwitchDelayMs:"
API_ENDPOINT_GET_CHANNEL_BALANCE = "/httpapi.asp?command=getChannelBalance"
API_ENDPOINT_SET_CHANNEL_BALANCE = "/httpapi.asp?command=setChannelBalance:"

# Miscellaneous endpoints
API_ENDPOINT_SET_LED = "/httpapi.asp?command=LED_SWITCH_SET:"
API_ENDPOINT_SET_BUTTONS = "/httpapi.asp?command=Button_Enable_SET:"

# Bluetooth endpoints
API_ENDPOINT_START_BT_DISCOVERY = "/httpapi.asp?command=startbtdiscovery:"
API_ENDPOINT_GET_BT_DISCOVERY_RESULT = "/httpapi.asp?command=getbtdiscoveryresult"
API_ENDPOINT_CONNECT_BT_A2DP = "/httpapi.asp?command=connectbta2dpsynk:"
API_ENDPOINT_DISCONNECT_BT_A2DP = "/httpapi.asp?command=disconnectbta2dpsynk"
API_ENDPOINT_GET_BT_PAIR_STATUS = "/httpapi.asp?command=getbtpairstatus"
API_ENDPOINT_GET_BT_HISTORY = "/httpapi.asp?command=getbthistory"
API_ENDPOINT_CLEAR_BT_DISCOVERY = "/httpapi.asp?command=clearbtdiscoveryresult"

# LMS/Squeezelite endpoints
API_ENDPOINT_SQUEEZELITE_STATE = "/httpapi.asp?command=Squeezelite:getState"
API_ENDPOINT_SQUEEZELITE_DISCOVER = "/httpapi.asp?command=Squeezelite:discover"
API_ENDPOINT_SQUEEZELITE_AUTO_CONNECT = "/httpapi.asp?command=Squeezelite:autoConnectEnable:"
API_ENDPOINT_SQUEEZELITE_CONNECT_SERVER = "/httpapi.asp?command=Squeezelite:connectServer:"

# Audio output endpoints
API_ENDPOINT_AUDIO_OUTPUT_STATUS = "/httpapi.asp?command=getNewAudioOutputHardwareMode"
API_ENDPOINT_AUDIO_OUTPUT_SET = "/httpapi.asp?command=setAudioOutputHardwareMode:"

# Timer and alarm endpoints (WiiM devices only)
API_ENDPOINT_SET_ALARM = "/httpapi.asp?command=setAlarmClock:"
API_ENDPOINT_GET_ALARM = "/httpapi.asp?command=getAlarmClock:"
API_ENDPOINT_ALARM_STOP = "/httpapi.asp?command=alarmStop"
API_ENDPOINT_TIME_SYNC = "/httpapi.asp?command=timeSync:"
API_ENDPOINT_SET_SHUTDOWN = "/httpapi.asp?command=setShutdown:"
API_ENDPOINT_GET_SHUTDOWN = "/httpapi.asp?command=getShutdown"

# Audio output mode constants
AUDIO_OUTPUT_MODE_LINE_OUT = 0
AUDIO_OUTPUT_MODE_OPTICAL_OUT = 1
AUDIO_OUTPUT_MODE_LINE_OUT_2 = 2  # Some devices have multiple line out modes
AUDIO_OUTPUT_MODE_COAX_OUT = 3
AUDIO_OUTPUT_MODE_BLUETOOTH_OUT = 4

# Audio output mode mapping (mode integer -> friendly name)
AUDIO_OUTPUT_MODE_MAP: dict[int, str] = {
    AUDIO_OUTPUT_MODE_LINE_OUT: "Line Out",
    AUDIO_OUTPUT_MODE_OPTICAL_OUT: "Optical Out",
    AUDIO_OUTPUT_MODE_LINE_OUT_2: "Line Out",  # Treat as Line Out for display
    AUDIO_OUTPUT_MODE_COAX_OUT: "Coax Out",
    AUDIO_OUTPUT_MODE_BLUETOOTH_OUT: "Bluetooth Out",
}

# Reverse mapping (friendly name -> mode integer)
AUDIO_OUTPUT_MODE_NAME_TO_INT: dict[str, int] = {
    "line out": AUDIO_OUTPUT_MODE_LINE_OUT,
    "lineout": AUDIO_OUTPUT_MODE_LINE_OUT,
    "optical out": AUDIO_OUTPUT_MODE_OPTICAL_OUT,
    "optical": AUDIO_OUTPUT_MODE_OPTICAL_OUT,
    "coax out": AUDIO_OUTPUT_MODE_COAX_OUT,
    "coax": AUDIO_OUTPUT_MODE_COAX_OUT,
    "coaxial": AUDIO_OUTPUT_MODE_COAX_OUT,
    "bluetooth out": AUDIO_OUTPUT_MODE_BLUETOOTH_OUT,
    "bluetooth": AUDIO_OUTPUT_MODE_BLUETOOTH_OUT,
}

# Alarm trigger types (WiiM devices only)
ALARM_TRIGGER_CANCEL = 0
ALARM_TRIGGER_ONCE = 1
ALARM_TRIGGER_DAILY = 2
ALARM_TRIGGER_WEEKLY = 3
ALARM_TRIGGER_WEEKLY_BITMASK = 4
ALARM_TRIGGER_MONTHLY = 5

# Alarm operations (WiiM devices only)
ALARM_OP_SHELL = 0
ALARM_OP_PLAYBACK = 1
ALARM_OP_STOP = 2

# LED Control endpoints
API_ENDPOINT_LED = "/httpapi.asp?command=setLED:"
API_ENDPOINT_LED_BRIGHTNESS = "/httpapi.asp?command=setLEDBrightness:"

# Arylic-specific LED commands (experimental - based on user research)
# Arylic devices use different LED command format: MCU+PAS+RAKOIT:LED:
# Documentation: https://github.com/mjcumming/wiim/issues/55
API_ENDPOINT_ARYLIC_LED = "/httpapi.asp?command=MCU+PAS+RAKOIT:LED:"
API_ENDPOINT_ARYLIC_LED_BRIGHTNESS = "/httpapi.asp?command=MCU+PAS+RAKOIT:LEDBRIGHTNESS:"

__all__ = [
    "AUDIO_OUTPUT_MODE_LINE_OUT",
    "AUDIO_OUTPUT_MODE_OPTICAL_OUT",
    "AUDIO_OUTPUT_MODE_LINE_OUT_2",
    "AUDIO_OUTPUT_MODE_COAX_OUT",
    "AUDIO_OUTPUT_MODE_BLUETOOTH_OUT",
    "AUDIO_OUTPUT_MODE_MAP",
    "AUDIO_OUTPUT_MODE_NAME_TO_INT",
    "WIIM_CA_CERT",
    "AUDIO_PRO_CLIENT_CERT",
    "VENDOR_WIIM",
    "VENDOR_ARYLIC",
    "VENDOR_AUDIO_PRO",
    "VENDOR_LINKPLAY_GENERIC",
    "STATUS_MAP",
    "MODE_MAP",
    "EQ_NUMERIC_MAP",
    "DEFAULT_PORT",
    "DEFAULT_TIMEOUT",
    "API_ENDPOINT_STATUS",
    "API_ENDPOINT_PLAYER_STATUS",
    "API_ENDPOINT_METADATA",
    "API_ENDPOINT_PLAY",
    "API_ENDPOINT_PAUSE",
    "API_ENDPOINT_STOP",
    "API_ENDPOINT_NEXT",
    "API_ENDPOINT_PREV",
    "API_ENDPOINT_VOLUME",
    "API_ENDPOINT_MUTE",
    "API_ENDPOINT_SEEK",
    "API_ENDPOINT_DEVICE_INFO",
    "API_ENDPOINT_FIRMWARE",
    "API_ENDPOINT_GROUP_SLAVES",
    "API_ENDPOINT_GROUP_EXIT",
    "API_ENDPOINT_EQ_GET",
    "API_ENDPOINT_EQ_STATUS",
    "API_ENDPOINT_EQ_LIST",
    "API_ENDPOINT_EQ_PRESET",
    "API_ENDPOINT_EQ_CUSTOM",
    "API_ENDPOINT_EQ_ON",
    "API_ENDPOINT_EQ_OFF",
    "API_ENDPOINT_GROUP_KICK",
    "API_ENDPOINT_GROUP_SLAVE_MUTE",
    "API_ENDPOINT_GROUP_SLAVE_VOLUME",
    "EQ_PRESET_MAP",
    "EQ_NUMERIC_MAP",
    "API_ENDPOINT_PRESET_INFO",
    "API_ENDPOINT_PRESET",
    "API_ENDPOINT_AUDIO_OUTPUT_STATUS",
    "API_ENDPOINT_AUDIO_OUTPUT_SET",
    "API_ENDPOINT_LED",
    "API_ENDPOINT_LED_BRIGHTNESS",
    "API_ENDPOINT_ARYLIC_LED",
    "API_ENDPOINT_ARYLIC_LED_BRIGHTNESS",
    "API_ENDPOINT_SET_ALARM",
    "API_ENDPOINT_GET_ALARM",
    "API_ENDPOINT_ALARM_STOP",
    "API_ENDPOINT_TIME_SYNC",
    "API_ENDPOINT_SET_SHUTDOWN",
    "API_ENDPOINT_GET_SHUTDOWN",
    "ALARM_TRIGGER_CANCEL",
    "ALARM_TRIGGER_ONCE",
    "ALARM_TRIGGER_DAILY",
    "ALARM_TRIGGER_WEEKLY",
    "ALARM_TRIGGER_WEEKLY_BITMASK",
    "ALARM_TRIGGER_MONTHLY",
    "ALARM_OP_SHELL",
    "ALARM_OP_PLAYBACK",
    "ALARM_OP_STOP",
    "PLAY_MODE_NORMAL",
    "PLAY_MODE_REPEAT_ALL",
    "PLAY_MODE_REPEAT_ONE",
    "PLAY_MODE_SHUFFLE",
    "PLAY_MODE_SHUFFLE_REPEAT_ALL",
]
