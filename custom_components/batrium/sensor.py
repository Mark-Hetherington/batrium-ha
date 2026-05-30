"""Sensor platform for Batrium BMS."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SENSOR_CTRL_CHARGE_POWER_RATE, SENSOR_CTRL_DISCHG_POWER_RATE
from .coordinator import (
    SIGNAL_BATRIUM_CELL_UPDATE,
    SIGNAL_BATRIUM_UPDATE,
    BatriumCoordinator,
)

_LOGGER = logging.getLogger(__name__)

UNIT_MILLIVOLT = "mV"
UNIT_MILLIAMP = "mA"
UNIT_MILLIAMPHOUR = "mAh"


@dataclass
class BatriumSensorEntityDescription(SensorEntityDescription):
    """Describes a Batrium sensor."""

    state_key: str = ""
    value_fn: Any = None  # optional callable(raw_value) -> display_value


SYSTEM_SENSORS: tuple[BatriumSensorEntityDescription, ...] = (
    # ── Cell voltages ──────────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="min_cell_voltage",
        state_key="min_cell_voltage_mv",
        name="Min Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-minus",
    ),
    BatriumSensorEntityDescription(
        key="max_cell_voltage",
        state_key="max_cell_voltage_mv",
        name="Max Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-plus",
    ),
    BatriumSensorEntityDescription(
        key="avg_cell_voltage",
        state_key="avg_cell_voltage_mv",
        name="Avg Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery",
    ),
    # ── Cell temperatures ──────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="min_cell_temp",
        state_key="min_cell_temp_c",
        name="Min Cell Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="max_cell_temp",
        state_key="max_cell_temp_c",
        name="Max Cell Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="avg_cell_temp",
        state_key="avg_cell_temp_c",
        name="Avg Cell Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Shunt / Battery ───────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="shunt_soc",
        state_key="shunt_state_of_charge_pct",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="shunt_current",
        state_key="shunt_current_ma",
        name="Shunt Current",
        native_unit_of_measurement=UNIT_MILLIAMP,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
    ),
    BatriumSensorEntityDescription(
        key="shunt_temp",
        state_key="shunt_temp_c",
        name="Shunt Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="shunt_cap_full",
        state_key="shunt_capacity_to_full_mah",
        name="Capacity to Full",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-up",
    ),
    BatriumSensorEntityDescription(
        key="shunt_cap_empty",
        state_key="shunt_capacity_to_empty_mah",
        name="Capacity to Empty",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-arrow-down",
    ),
    BatriumSensorEntityDescription(
        key="shunt_status_text",
        state_key="shunt_status_text",
        name="Shunt Status",
        icon="mdi:battery-sync",
    ),
    # ── System ────────────────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="system_op_status",
        state_key="system_op_status_text",
        name="System Status",
        icon="mdi:battery-heart-variant",
    ),
    BatriumSensorEntityDescription(
        key="system_supply_voltage",
        state_key="system_supply_voltage_mv",
        name="System Supply Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:sine-wave",
    ),
    BatriumSensorEntityDescription(
        key="system_ambient_temp",
        state_key="system_ambient_temp_c",
        name="Ambient Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Cell counts ───────────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="cells_in_system",
        state_key="cells_in_system",
        name="Cells in System",
        icon="mdi:counter",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="cells_active",
        state_key="cells_active",
        name="Active Cells",
        icon="mdi:check-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="cells_in_bypass",
        state_key="cells_in_bypass",
        name="Cells in Bypass",
        icon="mdi:call-split",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="cells_overdue",
        state_key="cells_overdue",
        name="Cells Overdue",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Duration estimates ────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="duration_to_full",
        state_key="estimated_duration_to_full_min",
        name="Time to Full",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-outline",
    ),
    BatriumSensorEntityDescription(
        key="duration_to_empty",
        state_key="estimated_duration_to_empty_min",
        name="Time to Empty",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:timer-off-outline",
    ),
    # ── Recent session mAh ───────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="recent_charge",
        state_key="recent_charge_mah",
        name="Recent Charge",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging",
    ),
    BatriumSensorEntityDescription(
        key="recent_discharge",
        state_key="recent_discharge_mah",
        name="Recent Discharge",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-minus-variant",
    ),
    # ── Daily session ─────────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="daily_cumulative_charge",
        state_key="daily_cumulative_charge_mah",
        name="Daily Charge",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-charging-100",
    ),
    BatriumSensorEntityDescription(
        key="daily_cumulative_discharge",
        state_key="daily_cumulative_discharge_mah",
        name="Daily Discharge",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-minus-outline",
    ),
    BatriumSensorEntityDescription(
        key="daily_critical_events",
        state_key="daily_critical_events",
        name="Daily Critical Events",
        icon="mdi:alert",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Device info ───────────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="system_code",
        state_key="system_code",
        name="System Code",
        icon="mdi:identifier",
    ),
    BatriumSensorEntityDescription(
        key="firmware_version",
        state_key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
    ),
    # ── Status Control Logic (0x4733) ─────────────────────────────────
    BatriumSensorEntityDescription(
        key="ctrl_charge_power_rate",
        state_key=SENSOR_CTRL_CHARGE_POWER_RATE,
        name="Charge Power Rate",
        icon="mdi:battery-charging-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="ctrl_dischg_power_rate",
        state_key=SENSOR_CTRL_DISCHG_POWER_RATE,
        name="Discharge Power Rate",
        icon="mdi:battery-minus-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Batrium sensors."""
    coordinator: BatriumCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        BatriumSensor(coordinator, description, entry) for description in SYSTEM_SENSORS
    ]
    async_add_entities(entities)

    # Cell sensors are added dynamically once cells are discovered
    cell_entities_added: set[int] = set()

    @callback
    def _handle_cell_update() -> None:
        new_entities = []
        for node_id in coordinator.cells:
            if node_id not in cell_entities_added:
                cell_entities_added.add(node_id)
                new_entities.append(BatriumCellSensor(coordinator, node_id, entry))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_BATRIUM_CELL_UPDATE, _handle_cell_update)
    )


def _build_device_info(
    coordinator: BatriumCoordinator, entry: ConfigEntry
) -> DeviceInfo:
    fw = coordinator.device_info.get("firmware_version", "")
    hw = coordinator.device_info.get("hardware_version", "")
    name = coordinator.device_info.get("system_name") or entry.title

    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=name,
        manufacturer="Batrium",
        model="WatchMon",
        sw_version=str(fw) if fw else None,
        hw_version=str(hw) if hw else None,
    )


class BatriumSensor(SensorEntity):
    """A system-level Batrium sensor."""

    entity_description: BatriumSensorEntityDescription

    def __init__(
        self,
        coordinator: BatriumCoordinator,
        description: BatriumSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the sensor value, applying value_fn if defined."""
        raw = self._coordinator.state.get(self.entity_description.state_key)
        if raw is None:
            return None
        fn = self.entity_description.value_fn
        return fn(raw) if fn else raw

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


class BatriumCellSensor(SensorEntity):
    """Per-cell voltage/temperature/status sensor."""

    def __init__(
        self,
        coordinator: BatriumCoordinator,
        node_id: int,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the cell sensor for the given node ID."""
        self._coordinator = coordinator
        self._node_id = node_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_cell_{node_id}"
        self._attr_name = f"Cell {node_id}"
        self._attr_icon = "mdi:battery-outline"
        self._attr_has_entity_name = False

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for this entity."""
        return _build_device_info(self._coordinator, self._entry)

    @property
    def available(self) -> bool:
        """Return True when coordinator is available and this cell has been seen."""
        return self._coordinator.available and self._node_id in self._coordinator.cells

    @property
    def native_value(self) -> str | None:
        """Return cell status text as the primary state."""
        cell = self._coordinator.cells.get(self._node_id, {})
        return cell.get("status_text") or cell.get("operating_status_text")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed cell metrics as extra state attributes."""
        cell = self._coordinator.cells.get(self._node_id, {})
        return {
            "node_id": self._node_id,
            "min_cell_voltage_mv": cell.get("min_cell_voltage_mv"),
            "max_cell_voltage_mv": cell.get("max_cell_voltage_mv"),
            "max_cell_temp_c": cell.get("max_cell_temp_c"),
            "bypass_temp_c": cell.get("bypass_temp_c"),
            "bypass_current_ma": cell.get("bypass_current_ma"),
            "bypass_session_mah": cell.get("bypass_session_mah"),
            "is_overdue": cell.get("is_overdue"),
            "firmware_version": cell.get("firmware_version"),
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to cell update signals."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_BATRIUM_CELL_UPDATE, self._handle_update
            )
        )

    @callback
    def _handle_update(self) -> None:
        self.async_write_ha_state()
