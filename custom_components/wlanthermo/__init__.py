import time
from datetime import timedelta
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.components import mqtt
from homeassistant.core import callback

# ... (imports)
import logging
import json
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import Platform

from .const import (
    CONF_DEVICE_NAME,
    CONF_TOPIC_PREFIX,
    DATA_COORDINATOR,
    DATA_MQTT_UNSUBSCRIBE,
    DOMAIN,
    TOPIC_STATUS_DATA,
    TOPIC_STATUS_SETTINGS,
    TOPIC_SET,
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
    _LOGGER.info("Starting WLANThermo Integration version 1.14.0")
    hass.data.setdefault(DOMAIN, {})

    device_name = entry.data[CONF_DEVICE_NAME]
    topic_prefix = entry.data[CONF_TOPIC_PREFIX]

    # Create coordinator
    coordinator = WLANThermoDataCoordinator(hass, device_name, topic_prefix)

    # ... (setup)

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

    # ... (message_received_settings similar)

    # ... (subscriptions)

    # Setup offline detection (check every 30s)
    @callback
    def check_offline_status(_):
        """Check if device is offline."""
        coordinator.check_offline()

    unsub_timer = async_track_time_interval(hass, check_offline_status, timedelta(seconds=30))
    
    hass.data[DOMAIN][entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
    }
    hass.data[DOMAIN][entry.entry_id][DATA_MQTT_UNSUBSCRIBE] = [sub_data, sub_settings, unsub_timer]

    # Send "get" command to trigger settings update from device
    # Many WLANThermo devices respond to {"get": "all"} or just an update on connection
    try:
        payload = json.dumps({"get": "all"})
        topic = f"{topic_prefix}/{TOPIC_SET}"
        _LOGGER.debug(f"Sending discovery command to {topic}: {payload}")
        await mqtt.async_publish(hass, topic, payload)
    except Exception as e:
        _LOGGER.warning(f"Could not send discovery command: {e}")

    # Force update by sending current time to set/system and set
    # Strategy: Try multiple formats to hit the right one
    try:
        ts = str(int(time.time()))
        
        # 1. Nesting: {"system": {"time": ...}} to .../set
        payload_nested = json.dumps({"system": {"time": ts}})
        topic_set = f"{topic_prefix}/{TOPIC_SET}"
        await mqtt.async_publish(hass, topic_set, payload_nested)

        # 2. Flat: {"time": ...} to .../set/system
        payload_flat = json.dumps({"time": ts})
        topic_system = f"{topic_prefix}/set/system"
        await mqtt.async_publish(hass, topic_system, payload_flat)

        _LOGGER.debug(f"Sent discovery shotgun: {payload_nested} to {topic_set} and {payload_flat} to {topic_system}")
    except Exception as e:
        _LOGGER.warning(f"Could not send time sync: {e}")

    # Wait for first data with timeout (to avoid hanging forever)

    # ... (rest of setup)

# ...

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
        self.last_update_time = 0.0

    @callback
    def async_set_data(self, data: dict[str, Any]) -> None:
        """Set data and notify listeners."""
        self.last_update_time = time.time()
        self._merge_data(data)
        # Force online status if we receive data
        if "system" in self.data:
            self.data["system"]["online"] = True
            
        self.async_set_updated_data(self.data)

    @callback
    def async_set_settings(self, settings: dict[str, Any]) -> None:
        """Set settings."""
        self.last_update_time = time.time()
        self._merge_data(settings)
        self.async_set_updated_data(self.data)
        
    @callback
    def check_offline(self) -> None:
        """Check if data is stale (offline)."""
        if self.last_update_time == 0.0:
            return

        # Determine timeout dynamically
        # Default: 600s (safe fallback)
        timeout = 600
        
        # Try to read interval from settings (iot.PMQint)
        if "iot" in self.data and "PMQint" in self.data["iot"]:
            try:
                interval = int(self.data["iot"]["PMQint"])
                # Use 2.5x interval to be safe, but at least 60s
                # Example: 30s -> 75s timeout
                # Example: 300s -> 750s timeout
                timeout = max(60, interval * 2 + 15)
            except (ValueError, TypeError):
                pass
        
        if time.time() - self.last_update_time > timeout:
            if "system" in self.data and self.data["system"].get("online") != False:
                _LOGGER.warning(f"WLANThermo {self.device_name} offline (no data for >{timeout}s)")
                self.data["system"]["online"] = False
                self.async_set_updated_data(self.data)

    # ... (rest of class)

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

        # PID Profiles (from settings)
        if "pid" in new_data:
            self.data["pid"] = new_data["pid"]

        # Sensors (from settings) - definitions of sensor types
        if "sensors" in new_data:
            self.data["sensors"] = new_data["sensors"]

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
