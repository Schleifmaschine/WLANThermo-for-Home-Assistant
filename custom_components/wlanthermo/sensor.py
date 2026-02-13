"""Sensor platform for WLANThermo integration."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_ALARM_MAX,
    ATTR_ALARM_MIN,
    ATTR_CHANNEL,
    ATTR_COLOR,
    ATTR_MAX_TEMP,
    ATTR_MIN_TEMP,
    ATTR_SENSOR_TYPE,
    DATA_COORDINATOR,
    DOMAIN,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WLANThermo sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]

    entities: list[SensorEntity] = []

    # Wait for first data
    if not coordinator.data:
        return

    # Add channel temperature sensors
    if "channel" in coordinator.data:
        for idx, channel in enumerate(coordinator.data["channel"]):
            entities.append(WLANThermoTemperatureSensor(coordinator, idx))

    # Add system sensors
    entities.extend(
        [
            WLANThermoSystemSensor(coordinator, "cpu", "CPU Temperature"),
            WLANThermoSystemSensor(coordinator, "soc", "Battery"),
            WLANThermoSystemSensor(coordinator, "rssi", "WiFi Signal"),
        ]
    )

    async_add_entities(entities)


class WLANThermoTemperatureSensor(CoordinatorEntity, SensorEntity):
    """Representation of a WLANThermo temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, channel_idx: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._channel_idx = channel_idx
        self._attr_unique_id = (
            f"{coordinator.topic_prefix}_channel_{channel_idx}_temp"
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        channel_name = self._get_channel_data().get("name", f"Channel {self._channel_idx}")
        return f"{self.coordinator.device_name} {channel_name}"

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        temp = self._get_channel_data().get("temp")
        if temp is None or temp == 999:  # 999 = sensor not connected
            return None
        return temp

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self._get_channel_data().get("temp") != 999

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        channel = self._get_channel_data()
        return {
            ATTR_CHANNEL: self._channel_idx,
            ATTR_MIN_TEMP: channel.get("min"),
            ATTR_MAX_TEMP: channel.get("max"),
            ATTR_ALARM_MIN: channel.get("alarm_min"),
            ATTR_ALARM_MAX: channel.get("alarm_max"),
            ATTR_SENSOR_TYPE: channel.get("typ"),
            ATTR_COLOR: channel.get("color"),
        }

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    def _get_channel_data(self) -> dict:
        """Get channel data from coordinator."""
        if not self.coordinator.data or "channel" not in self.coordinator.data:
            return {}
        channels = self.coordinator.data["channel"]
        if self._channel_idx < len(channels):
            return channels[self._channel_idx]
        return {}


class WLANThermoSystemSensor(CoordinatorEntity, SensorEntity):
    """Representation of a WLANThermo system sensor."""

    def __init__(self, coordinator, sensor_type: str, name: str) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = f"{coordinator.device_name} {name}"
        self._attr_unique_id = f"{coordinator.topic_prefix}_{sensor_type}"

        # Set device class and unit based on sensor type
        if sensor_type == "cpu":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "soc":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_type == "rssi":
            self._attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
            self._attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
            self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if not self.coordinator.data or "system" not in self.coordinator.data:
            return None
        return self.coordinator.data["system"].get(self._sensor_type)

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info
