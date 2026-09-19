"""
Regression tests for the local, non-upstream `get_automation_config` feature
(commit e5fc120 on the bzaks1424/hass-mcp fork). Upstream voska/hass-mcp has
no equivalent, so these tests have no upstream counterpart to collide with.

Run these specifically before/after a rebase onto upstream/master:
    uv run pytest -m local
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.hass import get_automation_config

pytestmark = pytest.mark.local


class TestGetAutomationConfig:
    """Test app.hass.get_automation_config."""

    @pytest.mark.asyncio
    async def test_returns_raw_config_on_success(self, mock_config):
        """A successful call hits the right URL and returns the parsed config."""
        mock_automation_config = {
            "id": "1701743566556",
            "alias": "Turn on lights in the morning",
            "trigger": [{"platform": "sun", "event": "sunrise"}],
            "action": [{"service": "light.turn_on", "target": {"entity_id": "light.living_room"}}],
        }

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = mock_automation_config

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.hass.get_client", return_value=mock_client):
            with patch("app.hass.HA_URL", mock_config["hass_url"]):
                with patch("app.hass.HA_TOKEN", mock_config["hass_token"]):
                    result = await get_automation_config("1701743566556")

                    assert result == mock_automation_config

                    mock_client.get.assert_called_once()
                    called_url = mock_client.get.call_args[0][0]
                    assert called_url == (
                        f"{mock_config['hass_url']}/api/config/automation/config/1701743566556"
                    )

    @pytest.mark.asyncio
    async def test_404_on_entity_slug_returns_formatted_error(self, mock_config):
        """
        Known trap (TODO #11): list_automations hands back the entity slug
        (entity_id.split('.')[1]), but this endpoint only accepts the numeric
        attributes.id. A slug 404s. Confirm the error comes back as
        {"error": ...} rather than an unhandled exception, and stays that way
        across an upstream rebase.
        """
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "404", request=MagicMock(), response=mock_response
            )
        )

        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.hass.get_client", return_value=mock_client):
            with patch("app.hass.HA_URL", mock_config["hass_url"]):
                with patch("app.hass.HA_TOKEN", mock_config["hass_token"]):
                    result = await get_automation_config("morning_lights")

                    assert isinstance(result, dict)
                    assert "error" in result
                    assert "404" in result["error"]

    @pytest.mark.asyncio
    async def test_connect_error_returns_formatted_error(self, mock_config):
        """Connection failures go through handle_api_errors like every other call."""
        import httpx

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        with patch("app.hass.get_client", return_value=mock_client):
            with patch("app.hass.HA_URL", mock_config["hass_url"]):
                with patch("app.hass.HA_TOKEN", mock_config["hass_token"]):
                    result = await get_automation_config("1701743566556")

                    assert isinstance(result, dict)
                    assert "error" in result
                    assert "Connection error" in result["error"]


class TestGetAutomationConfigTool:
    """Test the MCP tool wrapper in app.server, which just delegates."""

    @pytest.mark.asyncio
    async def test_tool_delegates_to_hass_layer(self):
        from app.server import get_automation_config_tool

        mock_config = {"id": "1701743566556", "alias": "Test automation"}

        with patch("app.server.get_automation_config", new=AsyncMock(return_value=mock_config)) as mock_fn:
            result = await get_automation_config_tool("1701743566556")

            assert result == mock_config
            mock_fn.assert_called_once_with("1701743566556")

    def test_tool_is_registered_and_documented(self):
        import app.server

        assert hasattr(app.server, "get_automation_config_tool")
        assert callable(app.server.get_automation_config_tool)
        assert app.server.get_automation_config_tool.__doc__
        assert "automation_id" in app.server.get_automation_config_tool.__doc__
