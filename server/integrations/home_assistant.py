"""Home Assistant integration for EVA."""

import aiohttp
import logging
from typing import Dict, Any, List, Optional

from .base import (
    BaseIntegration,
    IntegrationType,
    IntegrationCapability,
    get_integration_registry
)

logger = logging.getLogger("eva.integrations.hass")


class HomeAssistantIntegration(BaseIntegration):
    """
    Integration with Home Assistant.

    Allows EVA to control smart home devices through HA API.
    """

    def __init__(self):
        super().__init__("home_assistant", IntegrationType.SMART_HOME)

        self.url: str = ""
        self.token: str = ""
        self._session: Optional[aiohttp.ClientSession] = None

        # Define capabilities
        self.capabilities = [
            IntegrationCapability(
                name="turn_on",
                description="Turn on a device",
                parameters={"entity_id": "string"},
                example_phrases=["включи свет", "turn on", "включи", "врубай"]
            ),
            IntegrationCapability(
                name="turn_off",
                description="Turn off a device",
                parameters={"entity_id": "string"},
                example_phrases=["выключи свет", "turn off", "выруби", "погаси"]
            ),
            IntegrationCapability(
                name="toggle",
                description="Toggle a device state",
                parameters={"entity_id": "string"},
                example_phrases=["переключи", "toggle"]
            ),
            IntegrationCapability(
                name="set_brightness",
                description="Set light brightness",
                parameters={"entity_id": "string", "brightness": "int"},
                example_phrases=["сделай ярче", "сделай темнее", "яркость"]
            ),
            IntegrationCapability(
                name="set_temperature",
                description="Set thermostat temperature",
                parameters={"entity_id": "string", "temperature": "float"},
                example_phrases=["установи температуру", "сделай теплее", "охлади"]
            ),
            IntegrationCapability(
                name="get_state",
                description="Get device state",
                parameters={"entity_id": "string"},
                example_phrases=["какой статус", "состояние", "что с"]
            ),
            IntegrationCapability(
                name="list_devices",
                description="List all devices",
                parameters={},
                example_phrases=["список устройств", "какие устройства", "что есть"]
            )
        ]

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to Home Assistant."""
        self.url = credentials.get("url", "").rstrip("/")
        self.token = credentials.get("api_token", "") or credentials.get("token", "")

        if not self.url or not self.token:
            logger.error("Missing url or token for Home Assistant")
            return False

        # Create session
        self._session = aiohttp.ClientSession(
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
        )

        # Test connection
        try:
            async with self._session.get(f"{self.url}/api/") as response:
                if response.status == 200:
                    self.is_connected = True
                    logger.info(f"Connected to Home Assistant at {self.url}")
                    return True
                else:
                    logger.error(f"HA connection failed: {response.status}")
                    return False

        except Exception as e:
            logger.error(f"Failed to connect to Home Assistant: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Home Assistant."""
        if self._session:
            await self._session.close()
            self._session = None
        self.is_connected = False
        logger.info("Disconnected from Home Assistant")

    async def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute an action on Home Assistant."""
        if not self.is_connected or not self._session:
            return {"success": False, "message": "Not connected to Home Assistant"}

        params = params or {}

        try:
            if action == "turn_on":
                return await self._call_service("homeassistant", "turn_on", params)

            elif action == "turn_off":
                return await self._call_service("homeassistant", "turn_off", params)

            elif action == "toggle":
                return await self._call_service("homeassistant", "toggle", params)

            elif action == "set_brightness":
                entity_id = params.get("entity_id")
                brightness = params.get("brightness", 255)
                return await self._call_service("light", "turn_on", {
                    "entity_id": entity_id,
                    "brightness": brightness
                })

            elif action == "set_temperature":
                entity_id = params.get("entity_id")
                temperature = params.get("temperature")
                return await self._call_service("climate", "set_temperature", {
                    "entity_id": entity_id,
                    "temperature": temperature
                })

            elif action == "get_state":
                entity_id = params.get("entity_id")
                return await self._get_state(entity_id)

            elif action == "list_devices":
                return await self._list_devices()

            else:
                return {"success": False, "message": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"HA action failed: {e}")
            return {"success": False, "message": str(e)}

    async def _call_service(self, domain: str, service: str, data: Dict) -> Dict:
        """Call a Home Assistant service."""
        url = f"{self.url}/api/services/{domain}/{service}"

        async with self._session.post(url, json=data) as response:
            if response.status in [200, 201]:
                return {
                    "success": True,
                    "message": f"Executed {domain}.{service}",
                    "entity": data.get("entity_id", "unknown")
                }
            else:
                error = await response.text()
                return {"success": False, "message": f"Error: {error}"}

    async def _get_state(self, entity_id: str) -> Dict:
        """Get state of an entity."""
        url = f"{self.url}/api/states/{entity_id}"

        async with self._session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "entity_id": entity_id,
                    "state": data.get("state"),
                    "attributes": data.get("attributes", {}),
                    "friendly_name": data.get("attributes", {}).get("friendly_name", entity_id)
                }
            else:
                return {"success": False, "message": f"Entity not found: {entity_id}"}

    async def _list_devices(self) -> Dict:
        """List all devices/entities."""
        url = f"{self.url}/api/states"

        async with self._session.get(url) as response:
            if response.status == 200:
                states = await response.json()

                # Group by domain
                devices = {}
                for state in states:
                    entity_id = state.get("entity_id", "")
                    domain = entity_id.split(".")[0] if "." in entity_id else "unknown"

                    if domain not in devices:
                        devices[domain] = []

                    devices[domain].append({
                        "entity_id": entity_id,
                        "state": state.get("state"),
                        "name": state.get("attributes", {}).get("friendly_name", entity_id)
                    })

                return {
                    "success": True,
                    "total": len(states),
                    "domains": list(devices.keys()),
                    "devices": devices
                }
            else:
                return {"success": False, "message": "Failed to list devices"}

    def get_status(self) -> Dict[str, Any]:
        """Get integration status."""
        return {
            "connected": self.is_connected,
            "url": self.url,
            "has_token": bool(self.token)
        }


# Register on import
def register():
    registry = get_integration_registry()
    registry.register_class("home_assistant", HomeAssistantIntegration)
