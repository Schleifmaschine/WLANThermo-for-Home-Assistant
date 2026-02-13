"""Number platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_CHANNELS

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
        channel_name = self._get_channel_data().get("name", f"Channel {self._channel_idx}")
        return f"{self.coordinator.device_name} {channel_name} Alarm Min"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._get_channel_data().get("alarm_min")

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        channel_data = self._get_channel_data()
        channel_data["alarm_min"] = int(value)

        # Publish to MQTT
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        payload = json.dumps({"number": self._channel_idx, **channel_data})
        await mqtt.async_publish(self.hass, topic, payload)

        # Update coordinator data
        self.coordinator.data["channel"][self._channel_idx] = channel_data
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
        channel_name = self._get_channel_data().get("name", f"Channel {self._channel_idx}")
        return f"{self.coordinator.device_name} {channel_name} Alarm Max"

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        return self._get_channel_data().get("alarm_max")

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        channel_data = self._get_channel_data()
        channel_data["alarm_max"] = int(value)

        # Publish to MQTT
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        payload = json.dumps({"number": self._channel_idx, **channel_data})
        await mqtt.async_publish(self.hass, topic, payload)

        # Update coordinator data
        self.coordinator.data["channel"][self._channel_idx] = channel_data
        self.async_write_ha_state()

    def _get_channel_data(self) -> dict:
        """Get channel data from coordinator."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx].copy()
        return {}
