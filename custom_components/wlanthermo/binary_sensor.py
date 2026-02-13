"""Binary sensor platform for WLANThermo integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DATA_COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[BinarySensorEntity] = []

    @callback
    def _create_entities():
        """Create entities when data is available."""
        if not coordinator.data:
            return

        entities: list[BinarySensorEntity] = []

        # Add system binary sensors
        entities.extend(
            [
                WLANThermoBinarySensor(
                    coordinator,
                    "online",
                    "Online",
                    BinarySensorDeviceClass.CONNECTIVITY,
                ),
                WLANThermoBinarySensor(
                    coordinator,
                    "charge",
                    "Charging",
                    BinarySensorDeviceClass.BATTERY_CHARGING,
                ),
            ]
        )
        
        # Add pitmaster active binary sensors (optional, if useful)
        if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
            for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
                 if pm.get("typ") != "off": # Or logic to determine if active
                     pass # Maybe not strictly a binary sensor needed if we have select/mode

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


class WLANThermoBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a WLANThermo binary sensor."""

    def __init__(
        self,
        coordinator,
        sensor_type: str,
        name: str,
        device_class: BinarySensorDeviceClass | None = None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = f"{coordinator.device_name} {name}"
        self._attr_unique_id = f"{coordinator.topic_prefix}_{sensor_type}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data or "system" not in self.coordinator.data:
            return None
        return self.coordinator.data["system"].get(self._sensor_type)

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info
