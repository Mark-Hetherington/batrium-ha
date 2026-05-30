"""Binary sensor platform for Batrium BMS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SIGNAL_BATRIUM_UPDATE, BatriumCoordinator
from .sensor import _build_device_info


@dataclass
class BatriumBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Extends the standard description with the coordinator state dict key."""

    state_key: str = ""


BINARY_SENSORS: tuple[BatriumBinarySensorEntityDescription, ...] = (
    BatriumBinarySensorEntityDescription(
        key="battery_ok",
        state_key="battery_ok_state",
        name="Battery OK",
        device_class=BinarySensorDeviceClass.SAFETY,
        icon="mdi:shield-check",
    ),
    BatriumBinarySensorEntityDescription(
        key="critical_battery_ok",
        state_key="critical_battery_ok",
        name="Critical Battery OK",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
    ),
    BatriumBinarySensorEntityDescription(
        key="charging_is_on",
        state_key="charging_is_on",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        icon="mdi:battery-charging",
    ),
    BatriumBinarySensorEntityDescription(
        key="discharging_is_on",
        state_key="discharging_is_on",
        name="Discharging",
        icon="mdi:battery-minus",
    ),
    BatriumBinarySensorEntityDescription(
        key="heat_on",
        state_key="heat_on",
        name="Heating",
        device_class=BinarySensorDeviceClass.HEAT,
        icon="mdi:thermometer-plus",
    ),
    BatriumBinarySensorEntityDescription(
        key="cool_on",
        state_key="cool_on",
        name="Cooling",
        icon="mdi:snowflake",
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_heat_on",
        state_key="thermal_heat_on",
        name="Thermal Heat On",
        device_class=BinarySensorDeviceClass.HEAT,
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_cool_on",
        state_key="thermal_cool_on",
        name="Thermal Cool On",
    ),
    BatriumBinarySensorEntityDescription(
        key="critical_cells_low_voltage",
        state_key="critical_has_cells_low_voltage",
        name="Cells Low Voltage Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:battery-alert",
    ),
    BatriumBinarySensorEntityDescription(
        key="critical_cells_high_voltage",
        state_key="critical_has_cells_high_voltage",
        name="Cells High Voltage Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:battery-alert-variant",
    ),
    BatriumBinarySensorEntityDescription(
        key="critical_cells_overdue",
        state_key="critical_has_cells_overdue",
        name="Cells Overdue Alert",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:timer-alert",
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_relay1",
        state_key="expansion_relay1",
        name="Expansion Relay 1",
        icon="mdi:electric-switch",
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_relay2",
        state_key="expansion_relay2",
        name="Expansion Relay 2",
        icon="mdi:electric-switch",
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_relay3",
        state_key="expansion_relay3",
        name="Expansion Relay 3",
        icon="mdi:electric-switch",
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_relay4",
        state_key="expansion_relay4",
        name="Expansion Relay 4",
        icon="mdi:electric-switch",
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_battery_on",
        state_key="expansion_battery_on",
        name="Battery Contactor",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    BatriumBinarySensorEntityDescription(
        key="expansion_load_on",
        state_key="expansion_load_on",
        name="Load Contactor",
        device_class=BinarySensorDeviceClass.POWER,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Batrium binary sensors."""
    coordinator: BatriumCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        BatriumBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSORS
    )


class BatriumBinarySensor(BinarySensorEntity):
    """Represents a boolean state from the Batrium system."""

    entity_description: BatriumBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: BatriumCoordinator,
        description: BatriumBinarySensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        self._coordinator = coordinator
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return _build_device_info(self._coordinator, self._entry)

    @property
    def available(self) -> bool:
        """Return True when the coordinator has received recent data."""
        return self._coordinator.available

    @property
    def is_on(self) -> bool | None:
        """Return the boolean state, or None if not yet received."""
        val = self._coordinator.state.get(self.entity_description.state_key)
        if val is None:
            return None
        return bool(val)

    async def async_added_to_hass(self) -> None:
        """Subscribe to coordinator update signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATRIUM_UPDATE, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
