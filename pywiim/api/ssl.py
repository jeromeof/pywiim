"""SSL/TLS context management for WiiM device communication.

This module handles SSL context creation and client certificate loading
for devices that require mutual TLS authentication (Audio Pro MkII).
"""

from __future__ import annotations

import asyncio
import logging
import os
import ssl
import tempfile

from .constants import AUDIO_PRO_CLIENT_CERT, WIIM_CA_CERT

_LOGGER = logging.getLogger(__name__)


async def create_wiim_ssl_context(
    custom_context: ssl.SSLContext | None = None,
) -> ssl.SSLContext:
    """Create a permissive SSL context for WiiM device communication.

    For Audio Pro MkII devices, also loads client certificate for mutual TLS authentication.
    Uses executor for blocking SSL operations to avoid blocking the event loop.

    Args:
        custom_context: Optional custom SSL context (for tests/advanced use-cases)

    Returns:
        Configured SSL context ready for use with aiohttp
    """
    if custom_context is not None:
        return custom_context

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = ssl.TLSVersion.TLSv1
    ctx.maximum_version = ssl.TLSVersion.TLSv1_3
    ctx.set_ciphers("ALL:@SECLEVEL=0")

    try:
        ctx.load_verify_locations(cadata=WIIM_CA_CERT)
    except Exception as exc:  # noqa: BLE001
        _LOGGER.debug("Failed loading WiiM CA cert: %s", exc)

    # Attempt to load client certificate for mutual TLS authentication when supported.
    # Many Audio Pro MkII/W devices accept client auth on 4443; servers that don't
    # require a client certificate will simply ignore it.
    try:
        # Create temporary files from the embedded PEM string since load_cert_chain() requires file paths
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".pem") as cert_file:
            cert_file.write(AUDIO_PRO_CLIENT_CERT)
            cert_temp_path = cert_file.name

        # Load certificate from temporary file using executor to avoid blocking event loop
        # See: https://developers.home-assistant.io/docs/asyncio_blocking_operations/#load_cert_chain
        await asyncio.to_thread(ctx.load_cert_chain, cert_temp_path)
        _LOGGER.debug("Client certificate loaded for mutual TLS authentication (Audio Pro devices)")

        # Clean up temporary file
        try:
            os.unlink(cert_temp_path)
        except Exception:  # noqa: BLE001
            pass  # Ignore cleanup errors

    except Exception as exc:  # noqa: BLE001
        _LOGGER.warning("Failed to load client certificate for mTLS: %s", exc)
        # Continue without client cert - connection may still work on other ports

    return ctx
