"""Switch platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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
    """Set up WLANThermo switch entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SwitchEntity] = []

    @callback
    def _create_entities():
        """Create entities when data is available."""
        if not coordinator.data:
            return

        entities: list[SwitchEntity] = []

        # Switch platform is deprecated as of v1.11.0
        # Alarm is now a Select entity.
        # Push is part of Alarm Select.
        # Functionality moved to select.py
        
        async_add_entities([])

    if coordinator.data:
        _create_entities()
    else:
        # Wait for data
        unsub = None
        @callback
        def _data_received():
            """Handle first data."""
            nonlocal unsub
            if unsub:
                unsub()
                unsub = None
            _create_entities()

        unsub = coordinator.async_add_listener(_data_received)


class WLANThermoChannelAlarmSwitch(CoordinatorEntity, SwitchEntity):
    """Representation of a WLANThermo Channel Alarm (Piepser) switch."""

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the switch."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_alarm"
        )
        self._attr_icon = "mdi:bell-ring"

    @property
    def name(self) -> str:
        """Return the name of the switch."""
        return f"{self.coordinator.device_name} Channel {self._channel_idx + 1} Push Notification"

    @property
    def is_on(self) -> bool | None:
        """Return true if switch is on."""
        return self._get_channel_data().get("alarm")

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

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._async_set_alarm(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._async_set_alarm(False)

    async def _async_set_alarm(self, state: bool) -> None:
        """Set the alarm state."""
        payload = {"number": self._channel_idx + 1, "alarm": state}
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_CHANNELS}"
        
        _LOGGER.debug(f"Setting Alarm for channel {self._channel_idx + 1} to {state} on topic {topic}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))

        # Optimistic update
        self.coordinator.data["channel"][self._channel_idx]["alarm"] = state
        self.async_write_ha_state()

    def _get_channel_data(self) -> dict:
        """Get channel data."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx].copy()
        return {}
