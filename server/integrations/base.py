"""Base classes for EVA integrations - plugin system for smart home, services, etc."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("eva.integrations")


class IntegrationType(Enum):
    """Types of integrations EVA can handle."""
    SMART_HOME = "smart_home"       # Home Assistant, Alexa, Google Home
    MESSAGING = "messaging"          # Telegram, WhatsApp, Slack
    EMAIL = "email"                  # Gmail, Outlook
    CALENDAR = "calendar"            # Google Calendar, Outlook
    IOT_DEVICE = "iot_device"        # Direct device control
    SERVICE = "service"              # APIs, web services
    COFFEE = "coffee"                # Coffee machines (MOMA, etc.)
    CUSTOM = "custom"                # User-defined


@dataclass
class IntegrationCapability:
    """What an integration can do."""
    name: str                        # e.g., "turn_on", "brew_coffee"
    description: str                 # Human readable
    parameters: Dict[str, str] = field(default_factory=dict)  # param_name -> type
    example_phrases: List[str] = field(default_factory=list)  # "включи свет", "завари кофе"


@dataclass
class DiscoveredDevice:
    """A device found during network scan."""
    ip: str
    hostname: str
    mac: str = ""
    device_type: str = "unknown"     # router, smart_plug, camera, etc.
    manufacturer: str = ""
    open_ports: List[int] = field(default_factory=list)
    integration_hint: str = ""       # Suggested integration type


class BaseIntegration(ABC):
    """
    Base class for all EVA integrations.

    To create a new integration:
    1. Subclass BaseIntegration
    2. Implement required methods
    3. Register with IntegrationRegistry
    """

    def __init__(self, name: str, integration_type: IntegrationType):
        self.name = name
        self.integration_type = integration_type
        self.is_connected = False
        self.credentials: Dict[str, Any] = {}
        self.capabilities: List[IntegrationCapability] = []

    @abstractmethod
    async def connect(self, credentials: Dict[str, Any]) -> bool:
        """
        Connect to the service/device.

        Args:
            credentials: Dict with required auth info (api_key, username/password, token, etc.)

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the service/device."""
        pass

    @abstractmethod
    async def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute an action.

        Args:
            action: Action name (e.g., "turn_on", "send_message")
            params: Action parameters

        Returns:
            Result dict with at least {"success": bool, "message": str}
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the integration."""
        pass

    def get_capabilities(self) -> List[IntegrationCapability]:
        """Return list of capabilities this integration provides."""
        return self.capabilities

    def matches_phrase(self, phrase: str) -> Optional[tuple]:
        """
        Check if a phrase matches any capability.

        Returns:
            Tuple of (capability_name, extracted_params) or None
        """
        phrase_lower = phrase.lower()
        for cap in self.capabilities:
            for example in cap.example_phrases:
                if example.lower() in phrase_lower:
                    return (cap.name, {})
        return None


class IntegrationRegistry:
    """
    Registry for all available integrations.

    Manages discovery, loading, and access to integrations.
    """

    def __init__(self):
        self._integrations: Dict[str, BaseIntegration] = {}
        self._integration_classes: Dict[str, type] = {}

    def register_class(self, name: str, integration_class: type):
        """Register an integration class (not instance)."""
        self._integration_classes[name] = integration_class
        logger.info(f"Registered integration class: {name}")

    def create_integration(self, name: str, **kwargs) -> Optional[BaseIntegration]:
        """Create an integration instance from registered class."""
        if name not in self._integration_classes:
            logger.warning(f"Unknown integration: {name}")
            return None

        instance = self._integration_classes[name](**kwargs)
        self._integrations[name] = instance
        return instance

    def get(self, name: str) -> Optional[BaseIntegration]:
        """Get an integration by name."""
        return self._integrations.get(name)

    def list_available(self) -> List[str]:
        """List all registered integration classes."""
        return list(self._integration_classes.keys())

    def list_connected(self) -> List[str]:
        """List all connected integrations."""
        return [name for name, integ in self._integrations.items() if integ.is_connected]

    def find_by_type(self, integration_type: IntegrationType) -> List[BaseIntegration]:
        """Find all integrations of a specific type."""
        return [
            integ for integ in self._integrations.values()
            if integ.integration_type == integration_type
        ]

    def find_by_phrase(self, phrase: str) -> List[tuple]:
        """
        Find integrations that can handle a phrase.

        Returns:
            List of (integration_name, capability_name, params)
        """
        matches = []
        for name, integ in self._integrations.items():
            if not integ.is_connected:
                continue
            match = integ.matches_phrase(phrase)
            if match:
                cap_name, params = match
                matches.append((name, cap_name, params))
        return matches


# Global registry
_registry: Optional[IntegrationRegistry] = None


def get_integration_registry() -> IntegrationRegistry:
    global _registry
    if _registry is None:
        _registry = IntegrationRegistry()
        _register_builtin_integrations(_registry)
    return _registry


def _register_builtin_integrations(registry: IntegrationRegistry):
    """Register built-in integrations."""
    try:
        from .home_assistant import HomeAssistantIntegration
        registry.register_class("home_assistant", HomeAssistantIntegration)
    except ImportError:
        pass

    # Future integrations:
    # from .alexa import AlexaIntegration
    # from .moma_coffee import MomaCoffeeIntegration
    # registry.register_class("alexa", AlexaIntegration)
    # registry.register_class("moma_coffee", MomaCoffeeIntegration)


# ============== Network Discovery ==============

async def discover_network_devices(timeout: int = 5) -> List[DiscoveredDevice]:
    """
    Scan local network for devices.

    Uses ARP scan and common port checks to identify devices.
    """
    import asyncio
    import socket

    devices = []

    # Get local network range
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_prefix = ".".join(local_ip.split(".")[:-1])
    except Exception:
        network_prefix = "192.168.1"

    logger.info(f"Scanning network: {network_prefix}.0/24")

    async def check_host(ip: str) -> Optional[DiscoveredDevice]:
        """Check if a host is alive and gather info."""
        try:
            # Try to connect to common ports
            ports_to_check = [80, 443, 8080, 8123, 1883, 5353]  # HTTP, HTTPS, alt-HTTP, Home Assistant, MQTT, mDNS
            open_ports = []

            for port in ports_to_check:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(ip, port),
                        timeout=0.5
                    )
                    open_ports.append(port)
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

            if not open_ports:
                return None

            # Try to get hostname
            try:
                hostname = socket.gethostbyaddr(ip)[0]
            except Exception:
                hostname = ip

            # Guess device type
            device_type = "unknown"
            integration_hint = ""

            if 8123 in open_ports:
                device_type = "home_assistant"
                integration_hint = "Home Assistant detected! Can control smart home devices."
            elif 1883 in open_ports:
                device_type = "mqtt_broker"
                integration_hint = "MQTT broker - IoT device hub"
            elif 80 in open_ports or 443 in open_ports:
                device_type = "web_device"
                if "camera" in hostname.lower():
                    device_type = "camera"
                elif "printer" in hostname.lower():
                    device_type = "printer"

            return DiscoveredDevice(
                ip=ip,
                hostname=hostname,
                device_type=device_type,
                open_ports=open_ports,
                integration_hint=integration_hint
            )

        except Exception:
            return None

    # Scan in parallel
    tasks = [check_host(f"{network_prefix}.{i}") for i in range(1, 255)]
    results = await asyncio.gather(*tasks)

    devices = [d for d in results if d is not None]
    logger.info(f"Found {len(devices)} devices on network")

    return devices


# ============== Dynamic Integration Loader ==============

async def suggest_integrations(devices: List[DiscoveredDevice]) -> List[Dict[str, Any]]:
    """
    Analyze discovered devices and suggest integrations.

    Returns list of suggestions with setup instructions.
    """
    suggestions = []

    for device in devices:
        if device.device_type == "home_assistant":
            suggestions.append({
                "device": device.hostname,
                "ip": device.ip,
                "integration": "home_assistant",
                "name": "Home Assistant",
                "description": "Control all your smart home devices through Home Assistant",
                "setup": {
                    "requires": ["api_token"],
                    "instructions": [
                        "1. Open Home Assistant at http://{ip}:8123",
                        "2. Go to Profile -> Long-Lived Access Tokens",
                        "3. Create new token and give it to EVA"
                    ]
                },
                "capabilities": ["turn_on", "turn_off", "set_brightness", "set_temperature"]
            })

        elif device.device_type == "mqtt_broker":
            suggestions.append({
                "device": device.hostname,
                "ip": device.ip,
                "integration": "mqtt",
                "name": "MQTT Devices",
                "description": "Connect to IoT devices via MQTT",
                "setup": {
                    "requires": ["username", "password"],
                    "optional": ["topic_prefix"]
                },
                "capabilities": ["publish", "subscribe", "device_control"]
            })

    return suggestions
