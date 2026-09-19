"""Fork-local: read an automation's raw config by its numeric id.

Not in upstream voska/hass-mcp. Lives in its own module, with no import of
app.server, so a catch-up never merges inside upstream's files: app/server.py
registers the tool through register() in two lines at its end.
"""
import logging
from typing import Any, Dict

from app import hass

logger = logging.getLogger(__name__)


@hass.handle_api_errors
async def get_automation_config(automation_id: str) -> Dict[str, Any]:
    """Get the raw configuration of a specific automation"""
    client = await hass.get_client()
    response = await client.get(
        f"{hass.HA_URL}/api/config/automation/config/{automation_id}",
        headers=hass.get_ha_headers(),
    )
    response.raise_for_status()
    return response.json()


def register(mcp, async_handler):
    """Register the MCP tool on the server's FastMCP instance; returns the tool."""

    @mcp.tool()
    @async_handler("get_automation_config")
    async def get_automation_config_tool(automation_id: str) -> Dict[str, Any]:
        """
        Get the raw configuration for a specific automation

        Args:
            automation_id: The ID of the automation (e.g. '1701743566556')

        Returns:
            The raw configuration dictionary
        """
        logger.info(f"Getting automation config for: {automation_id}")
        return await get_automation_config(automation_id)

    return get_automation_config_tool
