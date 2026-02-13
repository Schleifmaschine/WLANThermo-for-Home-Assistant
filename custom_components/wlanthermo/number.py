"""Number platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_CHANNELS, TOPIC_SET_PITMASTER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[NumberEntity] = []

    # Wait for first data
    if not coordinator.data:
        return

    # Add alarm temperature numbers for each channel
    if "channel" in coordinator.data:
        for idx, channel in enumerate(coordinator.data["channel"]):
            entities.append(WLANThermoAlarmMinNumber(coordinator, idx))
            entities.append(WLANThermoAlarmMaxNumber(coordinator, idx))

    # Add pitmaster set temperature and manual value
    if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
        for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
            entities.append(WLANThermoPitmasterSetTempNumber(coordinator, idx))
            entities.append(WLANThermoPitmasterManualValueNumber(coordinator, idx))

    async_add_entities(entities)


class WLANThermoAlarmMinNumber(CoordinatorEntity, NumberEntity):
    """Representation of a WLANThermo minimum alarm temperature."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 300
    _attr_native_step = 1

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_alarm_min"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        channel_data = self._get_channel_data()
        name = channel_data.get("name")
        return f"{self.coordinator.device_name} Channel {self._channel_idx + 1} Alarm Min ({name})"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._get_channel_data().get("min")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_channel_{self._channel_idx}")},
            name=f"{self.coordinator.device_name} Channel {self._channel_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Channel Sensor",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Send minimal payload: number and the specific value changed (key: "min")
        payload = {"number": self._channel_idx + 1, "min": int(value)}

        # Publish to MQTT
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        
        _LOGGER.debug(f"Setting Alarm Min for channel {self._channel_idx + 1} to {value} on topic {topic} with payload {payload}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))

        # Update coordinator data optimistically
        self.coordinator.data["channel"][self._channel_idx]["min"] = int(value)
        self.async_write_ha_state()

    def _get_channel_data(self) -> dict:
        """Get channel data from coordinator."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx].copy()
        return {}


class WLANThermoAlarmMaxNumber(CoordinatorEntity, NumberEntity):
    """Representation of a WLANThermo maximum alarm temperature."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 300
    _attr_native_step = 1

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_alarm_max"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        channel_data = self._get_channel_data()
        name = channel_data.get("name")
        return f"{self.coordinator.device_name} Channel {self._channel_idx + 1} Alarm Max ({name})"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._get_channel_data().get("max")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_channel_{self._channel_idx}")},
            name=f"{self.coordinator.device_name} Channel {self._channel_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Channel Sensor",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Send minimal payload (key: "max")
        payload = {"number": self._channel_idx + 1, "max": int(value)}

        # Publish to MQTT
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        
        _LOGGER.debug(f"Setting Alarm Max for channel {self._channel_idx + 1} to {value} on topic {topic} with payload {payload}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))

        # Update coordinator data optimistically
        self.coordinator.data["channel"][self._channel_idx]["max"] = int(value)
        self.async_write_ha_state()

    def _get_channel_data(self) -> dict:
        """Get channel data from coordinator."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx].copy()
        return {}


class WLANThermoPitmasterSetTempNumber(CoordinatorEntity, NumberEntity):
    """Representation of a WLANThermo Pitmaster Set Temperature."""

    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = 0
    _attr_native_max_value = 300 
    _attr_native_step = 1

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_set_temp"
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1} Set Temp"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._get_pm_data().get("set")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        payload = {"id": self._pm_idx + 1, "set": int(value)}
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx + 1} Set Temp to {value} on topic {topic}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["set"] = int(value)
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}


class WLANThermoPitmasterManualValueNumber(CoordinatorEntity, NumberEntity):
    """Representation of a WLANThermo Pitmaster Manual Value (0-100%)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 1

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_manual_value"
        )
        self._attr_icon = "mdi:knob"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1} Manual Value"

    @property
    def native_value(self) -> float | None:
        """Return the current value (value in % for manual setting)."""
        # We assume 'value' in API status is the current output value.
        # But for SETTING manual value, we need to know what was set?
        # Typically the device report value=set_value in manual mode.
        return self._get_pm_data().get("value")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        # Payload for manual value (assuming key 'value' from common practice)
        # 1-based ID!
        payload = {"id": self._pm_idx + 1, "value": int(value)}
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx + 1} Manual Value to {value} on topic {topic}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update (might be overwritten by next status update)
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["value"] = int(value)
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}
