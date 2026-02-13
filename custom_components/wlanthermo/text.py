"""Text platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_CHANNELS

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo text entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[TextEntity] = []

    # Wait for first data
    if not coordinator.data:
        return

    # Add channel name text entities
    if "channel" in coordinator.data:
        for idx, channel in enumerate(coordinator.data["channel"]):
            entities.append(WLANThermoChannelNameText(coordinator, idx))

    async_add_entities(entities)


class WLANThermoChannelNameText(CoordinatorEntity, TextEntity):
    """Representation of a WLANThermo channel name text entity."""

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the text entity."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_name"
        )
        self._attr_icon = "mdi:rename-box"

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        # This is the name of the INPUT field itself
        return f"{self.coordinator.device_name} Channel {self._channel_idx + 1} Name"

    @property
    def native_value(self) -> str | None:
        """Return the current value."""
        return self._get_channel_data().get("name")

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

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        # Publish to MQTT
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        # Payload with "number" and "name"
        payload = {"number": self._channel_idx + 1, "name": value}
        
        _LOGGER.debug(f"Setting Name for channel {self._channel_idx + 1} to '{value}' on topic {topic}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))

        # Optimistic update
        self.coordinator.data["channel"][self._channel_idx]["name"] = value
        self.async_write_ha_state()

    def _get_channel_data(self) -> dict:
        """Get channel data from coordinator."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx].copy()
        return {}
