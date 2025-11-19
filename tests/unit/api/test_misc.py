"""Unit tests for Misc API."""

import pytest

from pywiim.exceptions import WiiMError


class TestMiscAPI:
    """Test MiscAPI mixin."""

    @pytest.mark.asyncio
    async def test_set_buttons_enabled(self, mock_client):
        """Test setting buttons enabled."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def _request(self, endpoint):
                return {"status": "ok"}

        client = TestClient()
        await client.set_buttons_enabled(True)
        await client.set_buttons_enabled(False)

    @pytest.mark.asyncio
    async def test_enable_touch_buttons(self, mock_client):
        """Test enabling touch buttons."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def set_buttons_enabled(self, enabled):
                pass

        client = TestClient()
        await client.enable_touch_buttons()

    @pytest.mark.asyncio
    async def test_disable_touch_buttons(self, mock_client):
        """Test disabling touch buttons."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def set_buttons_enabled(self, enabled):
                pass

        client = TestClient()
        await client.disable_touch_buttons()

    @pytest.mark.asyncio
    async def test_set_led_switch(self, mock_client):
        """Test setting LED switch."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def _request(self, endpoint):
                return {"status": "ok"}

        client = TestClient()
        await client.set_led_switch(True)
        await client.set_led_switch(False)

    @pytest.mark.asyncio
    async def test_get_device_capabilities(self, mock_client):
        """Test getting device capabilities."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def set_buttons_enabled(self, enabled):
                pass

            async def set_led_switch(self, enabled):
                pass

        client = TestClient()
        capabilities = await client.get_device_capabilities()

        assert isinstance(capabilities, dict)
        assert "touch_buttons" in capabilities
        assert "alternative_led" in capabilities

    @pytest.mark.asyncio
    async def test_get_device_capabilities_with_errors(self, mock_client):
        """Test getting device capabilities when some fail."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def set_buttons_enabled(self, enabled):
                raise WiiMError("Not supported")

            async def set_led_switch(self, enabled):
                pass

        client = TestClient()
        capabilities = await client.get_device_capabilities()

        assert capabilities["touch_buttons"] is False
        assert capabilities["alternative_led"] is True

    @pytest.mark.asyncio
    async def test_are_touch_buttons_enabled(self, mock_client):
        """Test checking if touch buttons are enabled."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def enable_touch_buttons(self):
                pass

        client = TestClient()
        result = await client.are_touch_buttons_enabled()

        assert result is True

    @pytest.mark.asyncio
    async def test_are_touch_buttons_enabled_error(self, mock_client):
        """Test checking touch buttons when request fails."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def enable_touch_buttons(self):
                raise WiiMError("Not supported")

        client = TestClient()
        result = await client.are_touch_buttons_enabled()

        assert result is False

    @pytest.mark.asyncio
    async def test_test_misc_functionality(self, mock_client):
        """Test testing misc functionality."""
        from pywiim.api.misc import MiscAPI

        class TestClient(MiscAPI):
            async def set_buttons_enabled(self, enabled):
                pass

            async def set_led_switch(self, enabled):
                pass

        client = TestClient()
        results = await client.test_misc_functionality()

        assert results["touch_buttons"] is True
        assert results["alternative_led"] is True
