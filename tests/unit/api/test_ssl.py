"""Unit tests for SSL context management."""

import ssl

import pytest

from pywiim.api.ssl import create_wiim_ssl_context


class TestCreateWiiMSSLContext:
    """Test create_wiim_ssl_context function."""

    @pytest.mark.asyncio
    async def test_create_ssl_context(self):
        """Test creating SSL context."""
        ctx = await create_wiim_ssl_context()

        assert isinstance(ctx, ssl.SSLContext)
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE

    @pytest.mark.asyncio
    async def test_create_ssl_context_custom(self):
        """Test creating SSL context with custom context."""
        custom_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        custom_ctx.check_hostname = True

        ctx = await create_wiim_ssl_context(custom_context=custom_ctx)

        assert ctx == custom_ctx
        assert ctx.check_hostname is True

    @pytest.mark.asyncio
    async def test_create_ssl_context_properties(self):
        """Test SSL context properties."""
        ctx = await create_wiim_ssl_context()

        # Check that context is configured for permissive SSL
        assert ctx.check_hostname is False
        assert ctx.verify_mode == ssl.CERT_NONE
        assert ctx.minimum_version == ssl.TLSVersion.TLSv1
