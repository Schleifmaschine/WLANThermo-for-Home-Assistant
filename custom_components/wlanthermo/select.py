"""Select platform for WLANThermo integration."""
from __future__ import annotations

import json
import logging

from homeassistant.components import mqtt
from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
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

    @callback
    def _create_entities():
        """Create entities when data is available."""
        if not coordinator.data:
            return

        entities: list[SelectEntity] = []

        if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
            for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
                entities.append(WLANThermoPitmasterModeSelect(coordinator, idx))
                entities.append(WLANThermoPitmasterChannelSelect(coordinator, idx))
                entities.append(WLANThermoPitmasterProfileSelect(coordinator, idx))

        async_add_entities(entities)

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
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Get current data to construct full payload
        pm_data = self._get_pm_data()
        
        # Default values if data missing
        current_channel = pm_data.get("channel", 1)
        current_pid = pm_data.get("pid", 0)
        current_value = pm_data.get("value", 0)
        current_set = pm_data.get("set", 0)
        # current_typ is replaced by option
        
        # specific fix: API expects "set_color" sometimes? No, user snippet uses "set". 
        
        # Construct full payload object
        payload_obj = {
            "id": self._pm_idx,
            "channel": current_channel,
            "pid": current_pid,
            "value": current_value,
            "set": current_set,
            "typ": option
        }
        
        # Wrap in list
        payload = [payload_obj]
        
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        _LOGGER.debug(f"Writing Pitmaster {self._pm_idx} Mode to {option}. Topic: {topic}, Payload: {payload}")
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
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_pitmaster_{self._pm_idx}")},
            name=f"{self.coordinator.device_name} Pitmaster {self._pm_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Pitmaster",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # Extract number from "Channel X"
        try:
            channel_num = int(option.split(" ")[1])
        except (IndexError, ValueError):
            _LOGGER.error(f"Could not parse channel number from option: {option}")
            return

        # Get current data to construct full payload
        pm_data = self._get_pm_data()
        
        current_typ = pm_data.get("typ", "off")
        current_pid = pm_data.get("pid", 0)
        current_value = pm_data.get("value", 0)
        current_set = pm_data.get("set", 0)
        # current_channel is replaced by channel_num

        # Construct full payload object
        payload_obj = {
            "id": self._pm_idx,
            "channel": channel_num,
            "pid": current_pid,
            "value": current_value,
            "set": current_set,
            "typ": current_typ
        }

        # Payload must be a list
        payload = [payload_obj]
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx} Channel to {channel_num} ({option}) on topic {topic}. Payload: {payload}")
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


class WLANThermoPitmasterProfileSelect(CoordinatorEntity, SelectEntity):
    """Representation of a WLANThermo Pitmaster Profile select."""

    _attr_icon = "mdi:face-man-profile"

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_profile"
        )
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Profile"
        # Generic profiles 0..4 (5 profiles) as fallback since we don't have names
        self._attr_options = [f"Profile {i}" for i in range(5)]

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option."""
        # API returns integer pid index
        pid = self._get_pm_data().get("pid")
        if pid is not None and 0 <= pid < 5:
            return f"Profile {pid}"
        elif pid is not None:
             # If PID is out of our 0-4 range, we should probably add it or handle it.
             # For now, return formatted string even if not in _options (HA might warn)
             # But better to stick to options.
             return None
        return None

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

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        try:
            # Extract number from "Profile X"
            pid_num = int(option.split(" ")[1])
        except (IndexError, ValueError):
            _LOGGER.error(f"Could not parse PID number from option: {option}")
            return

        # Get current data to construct full payload
        pm_data = self._get_pm_data()
        
        current_typ = pm_data.get("typ", "off")
        current_channel = pm_data.get("channel", 1)
        # current_pid replaced by pid_num
        current_value = pm_data.get("value", 0)
        current_set = pm_data.get("set", 0)

        # Construct full payload object
        payload_obj = {
            "id": self._pm_idx,
            "channel": current_channel,
            "pid": pid_num,
            "value": current_value,
            "set": current_set,
            "typ": current_typ
        }

        # Payload must be a list
        payload = [payload_obj]
        topic = f"{self.coordinator.topic_prefix}/{TOPIC_SET_PITMASTER}"
        
        _LOGGER.debug(f"Setting Pitmaster {self._pm_idx} Profile to {pid_num} ({option}) on topic {topic}. Payload: {payload}")
        await mqtt.async_publish(self.hass, topic, json.dumps(payload))
        
        # Optimistic update
        self.coordinator.data["pitmaster"]["pm"][self._pm_idx]["pid"] = pid_num
        self.async_write_ha_state()

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}