"""MQTT integration for EVA - connect to IoT devices."""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field

from .base import (
    BaseIntegration,
    IntegrationType,
    IntegrationCapability
)

logger = logging.getLogger("eva.integrations.mqtt")

# Try to import aiomqtt (async MQTT client)
try:
    import aiomqtt
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    logger.warning("aiomqtt not installed. MQTT integration disabled.")


@dataclass
class MQTTDevice:
    """Represents a discovered MQTT device."""
    topic: str
    name: str
    device_type: str = "unknown"  # switch, sensor, light, etc.
    state_topic: str = ""
    command_topic: str = ""
    last_state: Any = None


class MQTTIntegration(BaseIntegration):
    """
    MQTT Integration for IoT devices.

    Supports:
    - Publishing to topics (control devices)
    - Subscribing to topics (receive states)
    - Auto-discovery of devices (Home Assistant MQTT Discovery)
    - Common device patterns (Tasmota, Zigbee2MQTT, etc.)
    """

    def __init__(self):
        super().__init__("mqtt", IntegrationType.IOT_DEVICE)

        self.host: str = ""
        self.port: int = 1883
        self.username: str = ""
        self.password: str = ""
        self.topic_prefix: str = ""

        self._client: Optional[aiomqtt.Client] = None
        self._devices: Dict[str, MQTTDevice] = {}
        self._subscriptions: Dict[str, Callable] = {}
        self._listener_task: Optional[asyncio.Task] = None

        self.capabilities = [
            IntegrationCapability(
                name="publish",
                description="Publish message to MQTT topic",
                parameters={"topic": "string", "payload": "string"},
                example_phrases=["отправь mqtt", "publish to"]
            ),
            IntegrationCapability(
                name="subscribe",
                description="Subscribe to MQTT topic",
                parameters={"topic": "string"},
                example_phrases=["подпишись на", "subscribe to"]
            ),
            IntegrationCapability(
                name="turn_on",
                description="Turn on MQTT device",
                parameters={"device": "string"},
                example_phrases=["включи", "turn on"]
            ),
            IntegrationCapability(
                name="turn_off",
                description="Turn off MQTT device",
                parameters={"device": "string"},
                example_phrases=["выключи", "turn off"]
            ),
            IntegrationCapability(
                name="get_state",
                description="Get device state",
                parameters={"device": "string"},
                example_phrases=["статус", "состояние", "state of"]
            ),
            IntegrationCapability(
                name="list_devices",
                description="List discovered devices",
                parameters={},
                example_phrases=["список устройств", "mqtt устройства"]
            )
        ]

    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """Connect to MQTT broker."""
        if not MQTT_AVAILABLE:
            logger.error("aiomqtt not installed")
            return False

        self.host = credentials.get("host", "localhost")
        self.port = credentials.get("port", 1883)
        self.username = credentials.get("username", "")
        self.password = credentials.get("password", "")
        self.topic_prefix = credentials.get("topic_prefix", "")

        try:
            # Test connection
            async with aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                username=self.username if self.username else None,
                password=self.password if self.password else None
            ) as client:
                # Connection successful
                self.is_connected = True
                logger.info(f"Connected to MQTT broker at {self.host}:{self.port}")

            # Start persistent connection for subscriptions
            self._start_listener()

            return True

        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            return False

    def _start_listener(self):
        """Start background listener for subscriptions."""
        if self._listener_task and not self._listener_task.done():
            return

        self._listener_task = asyncio.create_task(self._listen_loop())

    async def _listen_loop(self):
        """Background loop to listen for MQTT messages."""
        while self.is_connected:
            try:
                async with aiomqtt.Client(
                    hostname=self.host,
                    port=self.port,
                    username=self.username if self.username else None,
                    password=self.password if self.password else None
                ) as client:
                    # Subscribe to discovery topics
                    await client.subscribe("homeassistant/#")
                    await client.subscribe("zigbee2mqtt/#")
                    await client.subscribe("tasmota/#")

                    if self.topic_prefix:
                        await client.subscribe(f"{self.topic_prefix}/#")

                    async for message in client.messages:
                        await self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MQTT listener error: {e}")
                await asyncio.sleep(5)  # Reconnect delay

    async def _handle_message(self, message):
        """Handle incoming MQTT message."""
        topic = str(message.topic)
        try:
            payload = message.payload.decode()
        except Exception:
            payload = str(message.payload)

        # Try to parse JSON
        try:
            data = json.loads(payload)
        except Exception:
            data = payload

        # Handle Home Assistant discovery
        if topic.startswith("homeassistant/") and "/config" in topic:
            await self._handle_ha_discovery(topic, data)

        # Handle Zigbee2MQTT
        elif topic.startswith("zigbee2mqtt/") and not topic.endswith("/set"):
            await self._handle_z2m_message(topic, data)

        # Update device state
        for device in self._devices.values():
            if device.state_topic == topic:
                device.last_state = data
                logger.debug(f"Updated state for {device.name}: {data}")

        # Call subscription handlers
        if topic in self._subscriptions:
            try:
                await self._subscriptions[topic](topic, data)
            except Exception as e:
                logger.error(f"Subscription handler error: {e}")

    async def _handle_ha_discovery(self, topic: str, config: dict):
        """Handle Home Assistant MQTT Discovery message."""
        if not isinstance(config, dict):
            return

        # Parse topic: homeassistant/{component}/{node_id}/{object_id}/config
        parts = topic.split("/")
        if len(parts) < 4:
            return

        component = parts[1]  # switch, light, sensor, etc.
        device_id = config.get("unique_id", parts[3] if len(parts) > 3 else "unknown")
        name = config.get("name", device_id)

        device = MQTTDevice(
            topic=topic,
            name=name,
            device_type=component,
            state_topic=config.get("state_topic", ""),
            command_topic=config.get("command_topic", "")
        )

        self._devices[device_id] = device
        logger.info(f"Discovered MQTT device: {name} ({component})")

    async def _handle_z2m_message(self, topic: str, data):
        """Handle Zigbee2MQTT message."""
        # Topic format: zigbee2mqtt/{device_name}
        parts = topic.split("/")
        if len(parts) < 2:
            return

        device_name = parts[1]
        if device_name in ["bridge", "group"]:
            return

        device_id = f"z2m_{device_name}"

        if device_id not in self._devices:
            self._devices[device_id] = MQTTDevice(
                topic=topic,
                name=device_name,
                device_type="zigbee",
                state_topic=topic,
                command_topic=f"{topic}/set"
            )
            logger.info(f"Discovered Zigbee device: {device_name}")

        self._devices[device_id].last_state = data

    async def disconnect(self) -> None:
        """Disconnect from MQTT broker."""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        self._client = None
        self.is_connected = False
        logger.info("Disconnected from MQTT broker")

    async def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute MQTT action."""
        if not self.is_connected:
            return {"success": False, "message": "Not connected to MQTT"}

        params = params or {}

        try:
            if action == "publish":
                return await self._publish(
                    params.get("topic", ""),
                    params.get("payload", "")
                )

            elif action == "turn_on":
                device = self._find_device(params.get("device", ""))
                if device and device.command_topic:
                    return await self._publish(device.command_topic, "ON")
                return {"success": False, "message": "Device not found"}

            elif action == "turn_off":
                device = self._find_device(params.get("device", ""))
                if device and device.command_topic:
                    return await self._publish(device.command_topic, "OFF")
                return {"success": False, "message": "Device not found"}

            elif action == "get_state":
                device = self._find_device(params.get("device", ""))
                if device:
                    return {
                        "success": True,
                        "device": device.name,
                        "state": device.last_state,
                        "type": device.device_type
                    }
                return {"success": False, "message": "Device not found"}

            elif action == "list_devices":
                return {
                    "success": True,
                    "count": len(self._devices),
                    "devices": [
                        {
                            "id": did,
                            "name": d.name,
                            "type": d.device_type,
                            "state": d.last_state
                        }
                        for did, d in self._devices.items()
                    ]
                }

            else:
                return {"success": False, "message": f"Unknown action: {action}"}

        except Exception as e:
            logger.error(f"MQTT action failed: {e}")
            return {"success": False, "message": str(e)}

    async def _publish(self, topic: str, payload: str) -> Dict[str, Any]:
        """Publish message to MQTT topic."""
        if not topic:
            return {"success": False, "message": "No topic specified"}

        try:
            async with aiomqtt.Client(
                hostname=self.host,
                port=self.port,
                username=self.username if self.username else None,
                password=self.password if self.password else None
            ) as client:
                await client.publish(topic, payload)

            logger.info(f"Published to {topic}: {payload}")
            return {"success": True, "topic": topic, "payload": payload}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def _find_device(self, query: str) -> Optional[MQTTDevice]:
        """Find device by name or ID."""
        query_lower = query.lower()

        # Exact match
        if query in self._devices:
            return self._devices[query]

        # Name match
        for device in self._devices.values():
            if device.name.lower() == query_lower:
                return device
            if query_lower in device.name.lower():
                return device

        return None

    def get_status(self) -> Dict[str, Any]:
        """Get MQTT integration status."""
        return {
            "connected": self.is_connected,
            "broker": f"{self.host}:{self.port}",
            "devices_count": len(self._devices),
            "has_listener": self._listener_task is not None and not self._listener_task.done()
        }


# Register on module load
def register():
    from .base import get_integration_registry
    registry = get_integration_registry()
    registry.register_class("mqtt", MQTTIntegration)
