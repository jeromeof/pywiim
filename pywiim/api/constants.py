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

# Default WiiM logo URL for cover art fallback
# Used when no valid cover art is available
DEFAULT_WIIM_LOGO_URL = "https://www.wiimhome.com/Content/images/logo.png"

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
