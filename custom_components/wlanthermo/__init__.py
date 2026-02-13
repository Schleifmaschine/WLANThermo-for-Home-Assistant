"""The WLANThermo integration."""
from __future__ import annotations

import asyncio
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
    Platform.SWITCH,  # Re-enabled for Alarm Switch
    Platform.BINARY_SENSOR,
    Platform.SELECT,
    Platform.TEXT,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up WLANThermo from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    device_name = entry.data[CONF_DEVICE_NAME]
    topic_prefix = entry.data[CONF_TOPIC_PREFIX]

    # Create coordinator
    coordinator = WLANThermoDataCoordinator(hass, device_name, topic_prefix)

    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_MQTT_UNSUBSCRIBE: [],
    }

    # Future for waiting for first data
    first_data_event = asyncio.Event()

    # Subscribe to MQTT topics
    @callback
    def message_received_data(msg):
        """Handle new MQTT messages for status data."""
        try:
            payload = json.loads(msg.payload)
            coordinator.async_set_data(payload)
            if not first_data_event.is_set():
                first_data_event.set()
                _LOGGER.debug("First data received, unblocking setup")
            _LOGGER.debug("Received data: %s", payload)
        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode MQTT payload: %s", msg.payload)

    @callback
    def message_received_settings(msg):
        """Handle new MQTT messages for settings."""
        try:
            payload = json.loads(msg.payload)
            coordinator.async_set_settings(payload)
            if not first_data_event.is_set():
                first_data_event.set()
                _LOGGER.debug("First settings received, unblocking setup")
            _LOGGER.debug("Received settings: %s", payload)
        except json.JSONDecodeError:
            _LOGGER.error("Failed to decode MQTT payload: %s", msg.payload)

    # Subscribe to topics
    sub_data = await mqtt.async_subscribe(
        hass, f"{topic_prefix}/{TOPIC_STATUS_DATA}", message_received_data, 0
    )
    sub_settings = await mqtt.async_subscribe(
        hass, f"{topic_prefix}/{TOPIC_STATUS_SETTINGS}", message_received_settings, 0
    )
    
    hass.data[DOMAIN][entry.entry_id][DATA_MQTT_UNSUBSCRIBE] = [sub_data, sub_settings]

    # Wait for first data with timeout (to avoid hanging forever)
    # If we have data, we proceed. If not, we might proceed with empty data 
    # but the platforms need to handle it.
    # ideally we want to show it as "loaded" but maybe unavailable entities.
    
    # We create a task to forward setup once data is received
    entry.async_create_background_task(
        hass, 
        _async_finish_startup(hass, entry, first_data_event),
        "wlanthermo_finish_startup"
    )

    return True

async def _async_finish_startup(hass: HomeAssistant, entry: ConfigEntry, event: asyncio.Event):
    """Wait for data and then load platforms."""
    try:
        # Wait up to 10 seconds for data
        await asyncio.wait_for(event.wait(), timeout=10)
    except asyncio.TimeoutError:
        _LOGGER.warning("Timed out waiting for initial data from WLANThermo. Entites might be missing until data is received.")
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Unsubscribe from MQTT
        if entry.entry_id in hass.data[DOMAIN]:
             for unsubscribe in hass.data[DOMAIN][entry.entry_id].get(DATA_MQTT_UNSUBSCRIBE, []):
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
        self._merge_data(data)
        self.async_set_updated_data(self.data)

    @callback
    def async_set_settings(self, settings: dict[str, Any]) -> None:
        """Set settings."""
        self._merge_data(settings)
        self.async_set_updated_data(self.data)

    def _merge_data(self, new_data: dict[str, Any]) -> None:
        """Deep merge new_data into self.data."""
        if not self.data:
            self.data = new_data
            return

        # System
        if "system" in new_data:
            if "system" not in self.data:
                self.data["system"] = {}
            self.data["system"].update(new_data["system"])

        # Channel (Array match by index)
        if "channel" in new_data:
            if "channel" not in self.data:
                self.data["channel"] = []
            
            # Ensure enough slots
            while len(self.data["channel"]) < len(new_data["channel"]):
                self.data["channel"].append({})

            for idx, channel_data in enumerate(new_data["channel"]):
                self.data["channel"][idx].update(channel_data)

        # Pitmaster
        if "pitmaster" in new_data:
            if "pitmaster" not in self.data:
                 self.data["pitmaster"] = {}
            
            # If it has "pm" array
            if "pm" in new_data["pitmaster"]:
                if "pm" not in self.data["pitmaster"]:
                    self.data["pitmaster"]["pm"] = []
                
                # Ensure slots
                while len(self.data["pitmaster"]["pm"]) < len(new_data["pitmaster"]["pm"]):
                    self.data["pitmaster"]["pm"].append({})
                
                for idx, pm_data in enumerate(new_data["pitmaster"]["pm"]):
                     self.data["pitmaster"]["pm"][idx].update(pm_data)
            
            # Merge other keys in pitmaster
            for key, val in new_data["pitmaster"].items():
                if key != "pm":
                    self.data["pitmaster"][key] = val

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.topic_prefix)},
            name=self.device_name,
            manufacturer="WLANThermo",
            model=self.data.get("system", {}).get("hw_version", "WLANThermo Device"),
            sw_version=self.data.get("system", {}).get("sw_version"),
        )
