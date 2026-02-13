"""Select platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_PITMASTER

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SelectEntity] = []

    # Wait for first data
    if not coordinator.data:
        return

    if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
        for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
            entities.append(WLANThermoPitmasterModeSelect(coordinator, idx))
            entities.append(WLANThermoPitmasterChannelSelect(coordinator, idx))

    async_add_entities(entities)


class WLANThermoPitmasterModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster mode select."""

    _attr_options = ["off", "manual", "auto"]
    _attr_translation_key = "mode"

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_mode"
        )
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Mode"
        self._attr_icon = "mdi:list-status"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        typ = self._get_pm_data().get("typ")
        if typ in self._attr_options:
            return typ
        return None
        
    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        payload = {"id": self._pm_idx + 1, "typ": option}
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx + 1} Mode to {option} on topic {topic}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["typ"] = option
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}


class WLANThermoPitmasterChannelSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster channel select."""
    
    # Options: 1 to 8 (assuming 8 channels max for now, or dynamic?)
    # Ideally dynamic, but SelectEntity options must be list of strings.
    # We provide 8 channels. using "Channel 1", "Channel 2" etc might be nicer for UI, 
    # but internal API uses integer index (1-based?).
    # Let's use simple numbers "1", "2"... 
    # Or "Channel 1", "Channel 2". Let's use "Channel X".
    
    _attr_options = [f"Channel {i}" for i in range(1, 9)] # Channel 1 to 8
    
    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_channel"
        )
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Channel"
        self._attr_icon = "mdi:thermometer-lines"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        # API returns integer channel index (probably 1-based, check automation snippet)
        # Snippet: "channel": {{ ... + 1 }} -> implies API uses 1-based.
        channel_idx = self._get_pm_data().get("channel") # e.g. 1
        if channel_idx:
            return f"Channel {channel_idx}"
        return None

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Extract number from "Channel X"
        try:
            channel_num = int(option.split(" ")[1])
        except (IndexError, ValueError):
            _LOGGER.error(f"Could not parse channel number from option: {option}")
            return

        payload = {"id": self._pm_idx + 1, "channel": channel_num}
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx + 1} Channel to {channel_num} ({option}) on topic {topic}")
        # Note: If API requires array for Pitmaster, this single object might fail. 
        # But we agreed to try single object first as per v1.1.5 strategy.
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["channel"] = channel_num
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}
