"""Select platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN, TOPIC_SET_PITMASTER

_LOGGER = logging.getLogger(__name__)

# Assuming these are correct from API docs or user config
# Commonly: "off", "manual", "auto", "profile_name"
# But typically MQTT API allows setting profile/type
PITMASTER_PROFILE_OPTIONS = ["off", "manual", "auto"] 


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo select entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SelectEntity] = []

    if not coordinator.data:
        return

    if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
        for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
             entities.append(WLANThermoPitmasterModeSelect(coordinator, idx))

    async_add_entities(entities)


class WLANThermoPitmasterModeSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster Mode Select."""

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_mode"
        )
        self._attr_options = PITMASTER_PROFILE_OPTIONS # Should be dynamic ideally?

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1} Mode"

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        pm_data = self._get_pm_data()
        return pm_data.get("typ", "off")

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info
    
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # This implementation depends on how WLANThermo expects mode changes via MQTT
        # According to docs/search, typical payload for pitmaster might be:
        # {"id": 0, "typ": "manual"} or similar.
        
        # Placeholder logic based on common patterns:
        payload = {"id": self._pm_idx, "typ": option}
        # If typ is 'manual', maybe we need a set value? 
        
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        # self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["typ"] = option # Risky
        # self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}
