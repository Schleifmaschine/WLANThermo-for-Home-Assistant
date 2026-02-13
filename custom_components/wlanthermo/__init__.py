"""The WLANThermo integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DATA_COORDINATOR,
    DATA_MQTT_UNSUBSCRIBE,
    DOMAIN,
    TOPIC_STATUS_DATA,
    TOPIC_STATUS_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.NUMBER,
    Platform.SWITCH,
    Platform.BINARY_SENSOR,
    Platform.SELECT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WLANThermo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    device_name = entry.data[CONF_DEVICE_NAME]
    topic_prefix = entry.data[CONF_TOPIC_PREFIX]

    # Create coordinator
    coordinator = WLANThermoDataCoordinator(hass, device_name, topic_prefix)

    # Subscribe to MQTT topics
    @callback
    def message_received_data(msg):
        """Handle new MQTT messages for status data."""
        try:
            payload = json.loads(msg.payload)
            coordinator.async_set_data(payload)
            _LOGGER.debug("Received data: %s", payload)
        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode MQTT payload: %s", msg.payload)

    @callback
    def message_received_settings(msg):
        """Handle new MQTT messages for settings."""
        try:
            payload = json.loads(msg.payload)
            coordinator.async_set_settings(payload)
            _LOGGER.debug("Received settings: %s", payload)
        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode MQTT payload: %s", msg.payload)

    # Subscribe to topics
    unsubscribe_data = await mqtt.async_subscribe(
        hass, f"{topic_prefix}/{TOPIC_STATUS_DATA}", message_received_data, 0
    )
    unsubscribe_settings = await mqtt.async_subscribe(
        hass, f"{topic_prefix}/{TOPIC_STATUS_SETTINGS}", message_received_settings, 0
    )

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_MQTT_UNSUBSCRIBE: [unsubscribe_data, unsubscribe_settings],
    }

    # Forward entry setup to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Unsubscribe from MQTT
        for unsubscribe in hass.data[DOMAIN][entry.entry_id][DATA_MQTT_UNSUBSCRIBE]:
            unsubscribe()

        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class WLANThermoDataCoordinator(DataUpdateCoordinator):
    """Class to manage fetching WLANThermo data."""

    def __init__(
        self, hass: HomeAssistant, device_name: str, topic_prefix: str
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
        )
        self.device_name = device_name
        self.topic_prefix = topic_prefix
        self.data: dict[str, Any] = {}
        self.settings: dict[str, Any] = {}

    @callback
    def async_set_data(self, data: dict[str, Any]) -> None:
        """Set data and notify listeners."""
        self.data = data
        self.async_set_updated_data(data)

    @callback
    def async_set_settings(self, settings: dict[str, Any]) -> None:
        """Set settings."""
        self.settings = settings

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.topic_prefix)},
            name=self.device_name,
            manufacturer="WLANThermo",
            model=self.data.get("system", {}).get("hw_version", "Unknown"),
            sw_version=self.data.get("system", {}).get("sw_version", "Unknown"),
        )
