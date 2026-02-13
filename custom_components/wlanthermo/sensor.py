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
from homeassistant.helpers.device_registry import DeviceInfo
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

    # Add Pitmaster sensors
    if "pitmaster" in coordinator.data and "pm" in coordinator.data["pitmaster"]:
        for idx, pm in enumerate(coordinator.data["pitmaster"]["pm"]):
            entities.append(WLANThermoPitmasterValueSensor(coordinator, idx))

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
        channel_name = self._get_channel_data().get("name")
        return f"{self.coordinator.device_name} Channel {self._channel_idx + 1} ({channel_name})"

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
            ATTR_CHANNEL: self._channel_idx + 1,
            # WLANThermo API data keys: "min", "max" serve as alarm limits
            ATTR_MIN_TEMP: channel.get("min"), 
            ATTR_MAX_TEMP: channel.get("max"),
            ATTR_ALARM_MIN: channel.get("min"), # Deprecated in our logic, but kept for compatibility mapping if needed
            ATTR_ALARM_MAX: channel.get("max"),
            ATTR_SENSOR_TYPE: channel.get("typ"),
            ATTR_COLOR: channel.get("color"),
        }

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.coordinator.topic_prefix}_channel_{self._channel_idx}")},
            name=f"{self.coordinator.device_name} Channel {self._channel_idx + 1}",
            via_device=(DOMAIN, self.coordinator.topic_prefix),
            manufacturer="WLANThermo",
            model="Channel Sensor",
            sw_version=self.coordinator.data.get("system", {}).get("sw_version", "Unknown"),
            configuration_url=f"http://{self.coordinator.data.get('system', {}).get('ip', '')}" 
            if self.coordinator.data.get("system", {}).get("ip") else None,
        )

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

class WLANThermoPitmasterValueSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Pitmaster Value Sensor (%)."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, pm_idx: int) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._pm_idx = pm_idx
        self._attr_unique_id = f"{coordinator.topic_prefix}_pitmaster_{pm_idx}_value"
        self._attr_name = f"{coordinator.device_name} Pitmaster {pm_idx + 1} Value"
        self._attr_icon = "mdi:fan"

    @property
    def native_value(self) -> float | None:
        """Return value."""
        return self._get_pm_data().get("value")

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Attributes."""
        pm = self._get_pm_data()
        return {
            "pid": pm.get("pid"),
            "set": pm.get("set"),
            "typ": pm.get("typ"),
            "channel": pm.get("channel"),
        }

    @property
    def device_info(self):
        """Return device info."""
        return self.coordinator.device_info

    def _get_pm_data(self) -> dict:
        """Get pitmaster data."""
        if not self.coordinator.data or "pitmaster" not in self.coordinator.data:
            return {}
        pms = self.coordinator.data["pitmaster"].get("pm", [])
        if self._pm_idx < len(pms):
            return pms[self._pm_idx]
        return {}
