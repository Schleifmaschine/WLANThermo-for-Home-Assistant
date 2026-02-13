"""Switch platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
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
    """Set up WLANThermo switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SwitchEntity] = []

    # Wait for first data
    if not coordinator.data:
        return

    # Add channel enable switches
    if "channel" in coordinator.data:
        for idx, channel in enumerate(coordinator.data["channel"]):
            entities.append(WLANThermoChannelSwitch(coordinator, idx))

    async_add_entities(entities)


class WLANThermoChannelSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a WLANThermo channel enable switch."""

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_enabled"
        )

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        channel_name = self._get_channel_data().get("name", f"Channel {self._channel_idx}")
        return f"{self.coordinator.device_name} {channel_name} Enabled"

    @property
    def is_on(self) -> bool:
        """Return true if the channel is enabled."""
        return self._get_channel_data().get("enabled", False)

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the channel on."""
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the channel off."""
        await self._set_enabled(False)

    async def _set_enabled(self, enabled: bool) -> None:
        """Set the enabled state."""
        channel_data = self._get_channel_data()
        channel_data["enabled"] = enabled

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
