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
    """Extends the standard description with state dict key and optional inversion."""

    state_key: str = ""
    invert: bool = False


# Always-created sensors — core system state present on every WatchMon.
BINARY_SENSORS: tuple[BatriumBinarySensorEntityDescription, ...] = (
    # battery_ok_state is True when the battery IS OK, so invert for PROBLEM semantics.
    BatriumBinarySensorEntityDescription(
        key="battery_ok",
        state_key="battery_ok_state",
        name="Battery Problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:shield-alert",
        invert=True,
    ),
    # critical_battery_ok is True when OK, so invert for PROBLEM semantics.
    BatriumBinarySensorEntityDescription(
        key="critical_battery_ok",
        state_key="critical_battery_ok",
        name="Critical Battery Problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        icon="mdi:alert-circle",
        invert=True,
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
    # ── Thermal Setup (0x5233) — monitor-enable flags ─────────────────
    BatriumBinarySensorEntityDescription(
        key="thermal_heat_monitor_cell_temp",
        state_key="thermal_heat_monitor_cell_temp",
        name="Heat Monitors Cell Temp",
        icon="mdi:thermometer-alert",
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_heat_monitor_ambient",
        state_key="thermal_heat_monitor_ambient",
        name="Heat Monitors Ambient Temp",
        icon="mdi:thermometer-alert",
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_cool_monitor_cell_temp",
        state_key="thermal_cool_monitor_cell_temp",
        name="Cool Monitors Cell Temp",
        icon="mdi:snowflake-thermometer",
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_cool_monitor_ambient",
        state_key="thermal_cool_monitor_ambient",
        name="Cool Monitors Ambient Temp",
        icon="mdi:snowflake-thermometer",
    ),
    BatriumBinarySensorEntityDescription(
        key="thermal_cool_monitor_bypass",
        state_key="thermal_cool_monitor_bypass",
        name="Cool Monitors Bypass",
        icon="mdi:electric-switch",
    ),
)

# Expansion-board sensors — only created the first time a True value is observed,
# so systems without expansion hardware never get these entities.
EXPANSION_BINARY_SENSORS: tuple[BatriumBinarySensorEntityDescription, ...] = (
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

    expansion_entities_added: set[str] = set()

    @callback
    def _handle_expansion_check() -> None:
        new_entities = []
        for description in EXPANSION_BINARY_SENSORS:
            if (
                description.key not in expansion_entities_added
                and coordinator.state.get(description.state_key)
            ):
                expansion_entities_added.add(description.key)
                new_entities.append(
                    BatriumBinarySensor(coordinator, description, entry)
                )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_BATRIUM_UPDATE, _handle_expansion_check)
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
        """Return True when the coordinator is live and this key has been populated."""
        return (
            self._coordinator.available
            and self.entity_description.state_key in self._coordinator.state
        )

    @property
    def is_on(self) -> bool | None:
        """Return the boolean state, optionally inverted, or None if absent."""
        val = self._coordinator.state.get(self.entity_description.state_key)
        if val is None:
            return None
        result = bool(val)
        return not result if self.entity_description.invert else result

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
