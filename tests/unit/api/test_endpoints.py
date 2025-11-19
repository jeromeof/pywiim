"""Unit tests for endpoint resolver."""

from pywiim.api.constants import (
    VENDOR_ARYLIC,
    VENDOR_AUDIO_PRO,
    VENDOR_LINKPLAY_GENERIC,
    VENDOR_WIIM,
)
from pywiim.api.endpoints import ENDPOINT_PLAYER_STATUS, EndpointResolver


class TestEndpointResolver:
    """Test EndpointResolver class."""

    def test_init(self):
        """Test EndpointResolver initialization."""
        capabilities = {"vendor": "wiim"}
        resolver = EndpointResolver(capabilities)

        assert resolver.vendor == "wiim"
        assert resolver.capabilities == capabilities

    def test_get_endpoint_chain_default(self):
        """Test getting endpoint chain for default vendor."""
        capabilities = {"vendor": VENDOR_WIIM}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain(ENDPOINT_PLAYER_STATUS)

        assert len(chain) > 0
        assert isinstance(chain, list)

    def test_get_endpoint_chain_audio_pro_mkii(self):
        """Test getting endpoint chain for Audio Pro MkII."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "mkii"}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain(ENDPOINT_PLAYER_STATUS)

        assert len(chain) > 0

    def test_get_endpoint_chain_audio_pro_w_generation(self):
        """Test getting endpoint chain for Audio Pro W-Generation."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "w_generation"}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain(ENDPOINT_PLAYER_STATUS)

        assert len(chain) > 0

    def test_get_endpoint_chain_audio_pro_original(self):
        """Test getting endpoint chain for Audio Pro Original."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "original"}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain(ENDPOINT_PLAYER_STATUS)

        assert len(chain) > 0

    def test_get_endpoint_chain_arylic(self):
        """Test getting endpoint chain for Arylic."""
        capabilities = {"vendor": VENDOR_ARYLIC}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain(ENDPOINT_PLAYER_STATUS)

        assert len(chain) > 0

    def test_get_endpoint_chain_unsupported(self):
        """Test getting endpoint chain for unsupported endpoint."""
        from pywiim.api.endpoints import ENDPOINT_METADATA

        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "mkii"}
        resolver = EndpointResolver(capabilities)

        # Metadata is not supported on Audio Pro MkII (empty list in registry)
        # But it falls back to default, so we get the default chain
        chain = resolver.get_endpoint_chain(ENDPOINT_METADATA)

        # The resolver falls back to default when variant has empty list
        # So we get the default chain, not empty
        assert len(chain) > 0  # Falls back to default

    def test_get_endpoint_chain_unknown(self):
        """Test getting endpoint chain for unknown endpoint."""
        capabilities = {"vendor": VENDOR_WIIM}
        resolver = EndpointResolver(capabilities)

        chain = resolver.get_endpoint_chain("unknown_endpoint")

        assert len(chain) == 0

    def test_is_endpoint_supported(self):
        """Test checking if endpoint is supported."""
        capabilities = {"vendor": VENDOR_WIIM}
        resolver = EndpointResolver(capabilities)

        assert resolver.is_endpoint_supported(ENDPOINT_PLAYER_STATUS) is True
        assert resolver.is_endpoint_supported("unknown_endpoint") is False

    def test_is_endpoint_supported_unsupported(self):
        """Test checking if unsupported endpoint."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "mkii"}
        resolver = EndpointResolver(capabilities)

        # Metadata is not supported on Audio Pro MkII (empty list in registry)
        # But it falls back to default, so it appears supported
        from pywiim.api.endpoints import ENDPOINT_METADATA

        # The resolver falls back to default when variant has empty list
        assert resolver.is_endpoint_supported(ENDPOINT_METADATA) is True  # Falls back to default

    def test_get_variant_key_wiim(self):
        """Test getting variant key for WiiM."""
        capabilities = {"vendor": VENDOR_WIIM}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "default"

    def test_get_variant_key_arylic(self):
        """Test getting variant key for Arylic."""
        capabilities = {"vendor": VENDOR_ARYLIC}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "arylic"

    def test_get_variant_key_audio_pro_mkii(self):
        """Test getting variant key for Audio Pro MkII."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "mkii"}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "audio_pro_mkii"

    def test_get_variant_key_audio_pro_w_generation(self):
        """Test getting variant key for Audio Pro W-Generation."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "w_generation"}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "audio_pro_w_generation"

    def test_get_variant_key_audio_pro_original(self):
        """Test getting variant key for Audio Pro Original."""
        capabilities = {"vendor": VENDOR_AUDIO_PRO, "audio_pro_generation": "original"}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "audio_pro_original"

    def test_get_variant_key_linkplay_generic(self):
        """Test getting variant key for LinkPlay generic."""
        capabilities = {"vendor": VENDOR_LINKPLAY_GENERIC}
        resolver = EndpointResolver(capabilities)

        variant = resolver._get_variant_key()

        assert variant == "default"
