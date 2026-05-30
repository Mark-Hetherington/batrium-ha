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
    UnitOfElectricCurrent,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    SENSOR_CELL_SETUP_BYPASS_AMP,
    SENSOR_CELL_SETUP_BYPASS_VOLT,
    SENSOR_CELL_SETUP_HI_VOLT,
    SENSOR_CELL_SETUP_LO_VOLT,
    SENSOR_CELL_SETUP_NOM_CELLS,
    SENSOR_CELL_SETUP_NOM_VOLT,
    SENSOR_CHARGE_CELL_VOLT_HI,
    SENSOR_CHARGE_CELL_VOLT_RESUME,
    SENSOR_CHARGE_SOC_HI,
    SENSOR_CHARGE_SOC_RESUME,
    SENSOR_COMMS_CANBUS,
    SENSOR_COMMS_CMU,
    SENSOR_COMMS_WIFI_RSSI,
    SENSOR_COMMS_WIFI_STATE,
    SENSOR_CTRL_CHARGE_POWER_RATE,
    SENSOR_CTRL_DISCHG_POWER_RATE,
    SENSOR_DAILY_CHARGE_KWH,
    SENSOR_DAILY_DISCHG_KWH,
    SENSOR_DAILY_SESSION_MAX_RECORDS,
    SENSOR_DAILY_SESSION_NUM_RECORDS,
    SENSOR_LIFE_COUNT_ALT_CHARGE,
    SENSOR_LIFE_COUNT_ALT_DISCHG,
    SENSOR_LIFE_COUNT_CHARGE_LIMP,
    SENSOR_LIFE_COUNT_CHARGE_ON,
    SENSOR_LIFE_COUNT_COOL_ON,
    SENSOR_LIFE_COUNT_CRIT_OK,
    SENSOR_LIFE_COUNT_DAILY,
    SENSOR_LIFE_COUNT_DISCHG_LIMP,
    SENSOR_LIFE_COUNT_DISCHG_ON,
    SENSOR_LIFE_COUNT_HEAT_ON,
    SENSOR_LIFE_COUNT_SOC_LIMIT1,
    SENSOR_LIFE_COUNT_SOC_LIMIT2,
    SENSOR_LIFE_COUNT_SOC_LIMIT3,
    SENSOR_LIFE_COUNT_SOC_LIMIT4,
    SENSOR_CRITICAL_CELL_TEMP_HI,
    SENSOR_CRITICAL_CELL_TEMP_LO,
    SENSOR_CRITICAL_CELL_VOLT_HI,
    SENSOR_CRITICAL_CELL_VOLT_LO,
    SENSOR_CRITICAL_SHUNT_PEAK_CHG,
    SENSOR_CRITICAL_SHUNT_PEAK_DCH,
    SENSOR_CRITICAL_SUPPLY_VOLT_HI,
    SENSOR_CRITICAL_SUPPLY_VOLT_LO,
    SENSOR_DISCHG_CELL_VOLT_LO,
    SENSOR_DISCHG_CELL_VOLT_RESUME,
    SENSOR_DISCHG_SOC_LO,
    SENSOR_DISCHG_SOC_RESUME,
    SENSOR_LIFE_COUNT_STARTUP,
    SENSOR_MAX_BYPASS_SESSION,
    SENSOR_SHUNT_SETUP_NOM_CAP,
    SENSOR_MAX_CELL_VOLT_NODE,
    SENSOR_MIN_BYPASS_SESSION,
    SENSOR_MIN_CELL_VOLT_NODE,
    SENSOR_QUICK_SESSION_INTERVAL,
    SENSOR_QUICK_SESSION_MAX_RECORDS,
    SENSOR_QUICK_SESSION_NUM_RECORDS,
    SENSOR_SHUNT_AVG_CHARGE_A,
    SENSOR_SHUNT_AVG_DISCHG_A,
    SENSOR_SHUNT_CUMUL_CHARGE_KWH,
    SENSOR_SHUNT_CUMUL_DISCHG_KWH,
    SENSOR_SHUNT_POWER_W,
    SENSOR_THERMAL_COOL_HI_AMBIENT,
    SENSOR_THERMAL_COOL_HI_AMBIENT_CUTOUT,
    SENSOR_THERMAL_COOL_HI_CELL_CUTOUT,
    SENSOR_THERMAL_COOL_HI_CELL_TEMP,
    SENSOR_THERMAL_COOL_MODE,
    SENSOR_THERMAL_HEAT_LO_AMBIENT,
    SENSOR_THERMAL_HEAT_LO_AMBIENT_CUTOUT,
    SENSOR_THERMAL_HEAT_LO_CELL_CUTOUT,
    SENSOR_THERMAL_HEAT_LO_CELL_TEMP,
    SENSOR_THERMAL_HEAT_MODE,
)
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
    # ── Network Setup (0x5A32) ────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="ntp_timezone",
        state_key="ntp_timezone",
        name="NTP Timezone",
        icon="mdi:map-clock-outline",
    ),
    BatriumSensorEntityDescription(
        key="ntp_server",
        state_key="ntp_server",
        name="NTP Server",
        icon="mdi:server-network",
    ),
    BatriumSensorEntityDescription(
        key="ntp_update_interval",
        state_key="ntp_update_interval",
        name="NTP Update Interval",
        icon="mdi:timer-sync-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Integration Setup (0x5335) ────────────────────────────────────
    BatriumSensorEntityDescription(
        key="integration_wifi_broadcast_mode",
        state_key="integration_wifi_broadcast_mode",
        name="WiFi Broadcast Mode",
        icon="mdi:wifi-settings",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="integration_canbus_mode",
        state_key="integration_canbus_mode",
        name="CAN Bus Mode",
        icon="mdi:can",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="integration_canbus_remote_addr",
        state_key="integration_canbus_remote_addr",
        name="CAN Bus Remote Address",
        icon="mdi:can",
    ),
    BatriumSensorEntityDescription(
        key="integration_canbus_base_addr",
        state_key="integration_canbus_base_addr",
        name="CAN Bus Base Address",
        icon="mdi:can",
    ),
    BatriumSensorEntityDescription(
        key="integration_canbus_group_addr",
        state_key="integration_canbus_group_addr",
        name="CAN Bus Group Address",
        icon="mdi:can",
    ),
    BatriumSensorEntityDescription(
        key="integration_mqtt_broadcast_mode",
        state_key="integration_mqtt_broadcast_mode",
        name="MQTT Broadcast Mode",
        icon="mdi:message-cog-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    # ── Remote Setup (0x4E33) ─────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="remote_template_no",
        state_key="remote_template_no",
        name="Remote Template",
        icon="mdi:file-outline",
    ),
    BatriumSensorEntityDescription(
        key="remote_charge_target_norm_volt",
        state_key="remote_charge_target_norm_volt",
        name="Charge Target Voltage (Normal)",
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_charge_target_norm_amp",
        state_key="remote_charge_target_norm_amp",
        name="Charge Target Current (Normal)",
        icon="mdi:current-dc",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_charge_target_limp_volt",
        state_key="remote_charge_target_limp_volt",
        name="Charge Target Voltage (Limp)",
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_charge_target_limp_amp",
        state_key="remote_charge_target_limp_amp",
        name="Charge Target Current (Limp)",
        icon="mdi:current-dc",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_charge_limp_soc",
        state_key="remote_charge_limp_soc_pct",
        name="Charge Limp Mode SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
    ),
    BatriumSensorEntityDescription(
        key="remote_dischg_target_norm_volt",
        state_key="remote_dischg_target_norm_volt",
        name="Discharge Target Voltage (Normal)",
        icon="mdi:lightning-bolt",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_dischg_target_norm_amp",
        state_key="remote_dischg_target_norm_amp",
        name="Discharge Target Current (Normal)",
        icon="mdi:current-dc",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_dischg_target_limp_volt",
        state_key="remote_dischg_target_limp_volt",
        name="Discharge Target Voltage (Limp)",
        icon="mdi:lightning-bolt-outline",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_dischg_target_limp_amp",
        state_key="remote_dischg_target_limp_amp",
        name="Discharge Target Current (Limp)",
        icon="mdi:current-dc",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="remote_dischg_limp_soc",
        state_key="remote_dischg_limp_soc_pct",
        name="Discharge Limp Mode SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
    ),
    # ── HW System Setup Full (0x4A36) ─────────────────────────────────
    BatriumSensorEntityDescription(
        key="quick_session_interval",
        state_key=SENSOR_QUICK_SESSION_INTERVAL,
        name="Quick Session Interval",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:timer-outline",
    ),
    # ── Thermal Setup (0x5233) ────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="thermal_heat_mode",
        state_key=SENSOR_THERMAL_HEAT_MODE,
        name="Heat Mode",
        icon="mdi:heat-wave",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="thermal_heat_lo_cell_temp",
        state_key=SENSOR_THERMAL_HEAT_LO_CELL_TEMP,
        name="Heat Activation Cell Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_heat_lo_ambient",
        state_key=SENSOR_THERMAL_HEAT_LO_AMBIENT,
        name="Heat Activation Ambient Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_heat_lo_cell_cutout",
        state_key=SENSOR_THERMAL_HEAT_LO_CELL_CUTOUT,
        name="Heat Cutout Cell Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_heat_lo_ambient_cutout",
        state_key=SENSOR_THERMAL_HEAT_LO_AMBIENT_CUTOUT,
        name="Heat Cutout Ambient Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_cool_mode",
        state_key=SENSOR_THERMAL_COOL_MODE,
        name="Cool Mode",
        icon="mdi:snowflake",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="thermal_cool_hi_cell_temp",
        state_key=SENSOR_THERMAL_COOL_HI_CELL_TEMP,
        name="Cool Activation Cell Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_cool_hi_ambient",
        state_key=SENSOR_THERMAL_COOL_HI_AMBIENT,
        name="Cool Activation Ambient Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_cool_hi_cell_cutout",
        state_key=SENSOR_THERMAL_COOL_HI_CELL_CUTOUT,
        name="Cool Cutout Cell Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="thermal_cool_hi_ambient_cutout",
        state_key=SENSOR_THERMAL_COOL_HI_AMBIENT_CUTOUT,
        name="Cool Cutout Ambient Temp",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    # ── Live Display (0x3233) ─────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="shunt_cumul_charge_kwh",
        state_key=SENSOR_SHUNT_CUMUL_CHARGE_KWH,
        name="Cumulative Charge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="shunt_cumul_dischg_kwh",
        state_key=SENSOR_SHUNT_CUMUL_DISCHG_KWH,
        name="Cumulative Discharge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Cell Stats (0x3E33) ────────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="min_cell_voltage_node",
        state_key=SENSOR_MIN_CELL_VOLT_NODE,
        name="Min Cell Voltage Node",
        icon="mdi:numeric",
    ),
    BatriumSensorEntityDescription(
        key="max_cell_voltage_node",
        state_key=SENSOR_MAX_CELL_VOLT_NODE,
        name="Max Cell Voltage Node",
        icon="mdi:numeric",
    ),
    BatriumSensorEntityDescription(
        key="min_bypass_session",
        state_key=SENSOR_MIN_BYPASS_SESSION,
        name="Min Bypass Session",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lightning-bolt-outline",
    ),
    BatriumSensorEntityDescription(
        key="max_bypass_session",
        state_key=SENSOR_MAX_BYPASS_SESSION,
        name="Max Bypass Session",
        native_unit_of_measurement=UNIT_MILLIAMPHOUR,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:lightning-bolt",
    ),
    # ── Shunt Status (0x3F34) ──────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="shunt_power",
        state_key=SENSOR_SHUNT_POWER_W,
        name="Shunt Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="shunt_avg_charge_current",
        state_key=SENSOR_SHUNT_AVG_CHARGE_A,
        name="Avg Charge Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
    ),
    BatriumSensorEntityDescription(
        key="shunt_avg_dischg_current",
        state_key=SENSOR_SHUNT_AVG_DISCHG_A,
        name="Avg Discharge Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:current-dc",
    ),
    # ── Daily Session Full (0x5432) ────────────────────────────────────
    BatriumSensorEntityDescription(
        key="daily_cumulative_charge_kwh",
        state_key=SENSOR_DAILY_CHARGE_KWH,
        name="Daily Charge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="daily_cumulative_discharge_kwh",
        state_key=SENSOR_DAILY_DISCHG_KWH,
        name="Daily Discharge Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Comms Status (0x6131) ──────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="comms_wifi_state",
        state_key=SENSOR_COMMS_WIFI_STATE,
        name="WiFi State",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="comms_canbus_op_status",
        state_key=SENSOR_COMMS_CANBUS,
        name="CAN Bus Status",
        icon="mdi:can",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="comms_cmu_op_status",
        state_key=SENSOR_COMMS_CMU,
        name="CMU Op Status",
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="comms_wifi_rssi",
        state_key=SENSOR_COMMS_WIFI_RSSI,
        name="WiFi RSSI",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:wifi-strength-2",
    ),
    # ── Life Metric (0x5632 base) ──────────────────────────────────────
    BatriumSensorEntityDescription(
        key="lifetime_count_startup",
        state_key=SENSOR_LIFE_COUNT_STARTUP,
        name="Lifetime Startups",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_critical_ok",
        state_key=SENSOR_LIFE_COUNT_CRIT_OK,
        name="Lifetime Critical Events",
        icon="mdi:alert-circle-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_charge_on",
        state_key=SENSOR_LIFE_COUNT_CHARGE_ON,
        name="Lifetime Charge Cycles",
        icon="mdi:battery-charging",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_discharge_on",
        state_key=SENSOR_LIFE_COUNT_DISCHG_ON,
        name="Lifetime Discharge Cycles",
        icon="mdi:battery-minus",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_daily_sessions",
        state_key=SENSOR_LIFE_COUNT_DAILY,
        name="Lifetime Daily Sessions",
        icon="mdi:calendar-check",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Life Metric v3/A (0x5633/0x5635) ──────────────────────────────
    BatriumSensorEntityDescription(
        key="lifetime_count_charge_limp",
        state_key=SENSOR_LIFE_COUNT_CHARGE_LIMP,
        name="Lifetime Charge Limp Events",
        icon="mdi:battery-charging-low",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_discharge_limp",
        state_key=SENSOR_LIFE_COUNT_DISCHG_LIMP,
        name="Lifetime Discharge Limp Events",
        icon="mdi:battery-alert-variant-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_heat_on",
        state_key=SENSOR_LIFE_COUNT_HEAT_ON,
        name="Lifetime Heat Activations",
        icon="mdi:heat-wave",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_cool_on",
        state_key=SENSOR_LIFE_COUNT_COOL_ON,
        name="Lifetime Cool Activations",
        icon="mdi:snowflake",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Life Metric B (0x5634) ─────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="lifetime_count_soc_limit1",
        state_key=SENSOR_LIFE_COUNT_SOC_LIMIT1,
        name="Lifetime SoC Limit 1 Events",
        icon="mdi:battery-low",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_soc_limit2",
        state_key=SENSOR_LIFE_COUNT_SOC_LIMIT2,
        name="Lifetime SoC Limit 2 Events",
        icon="mdi:battery-low",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_soc_limit3",
        state_key=SENSOR_LIFE_COUNT_SOC_LIMIT3,
        name="Lifetime SoC Limit 3 Events",
        icon="mdi:battery-low",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_soc_limit4",
        state_key=SENSOR_LIFE_COUNT_SOC_LIMIT4,
        name="Lifetime SoC Limit 4 Events",
        icon="mdi:battery-low",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_alt_charge_on",
        state_key=SENSOR_LIFE_COUNT_ALT_CHARGE,
        name="Lifetime Alt Charge Activations",
        icon="mdi:battery-charging-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    BatriumSensorEntityDescription(
        key="lifetime_count_alt_dischg_on",
        state_key=SENSOR_LIFE_COUNT_ALT_DISCHG,
        name="Lifetime Alt Discharge Activations",
        icon="mdi:battery-minus-outline",
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    # ── Session Metrics (0x5431) ───────────────────────────────────────
    BatriumSensorEntityDescription(
        key="quick_session_num_records",
        state_key=SENSOR_QUICK_SESSION_NUM_RECORDS,
        name="Quick Session Record Count",
        icon="mdi:history",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="quick_session_max_records",
        state_key=SENSOR_QUICK_SESSION_MAX_RECORDS,
        name="Quick Session Max Records",
        icon="mdi:history",
    ),
    BatriumSensorEntityDescription(
        key="daily_session_num_records",
        state_key=SENSOR_DAILY_SESSION_NUM_RECORDS,
        name="Daily Session Record Count",
        icon="mdi:calendar-clock",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    BatriumSensorEntityDescription(
        key="daily_session_max_records",
        state_key=SENSOR_DAILY_SESSION_MAX_RECORDS,
        name="Daily Session Max Records",
        icon="mdi:calendar-clock",
    ),
    # ── Cell Group Setup (0x4B34/35/36) ───────────────────────────────
    BatriumSensorEntityDescription(
        key="cell_setup_nom_volt",
        state_key=SENSOR_CELL_SETUP_NOM_VOLT,
        name="Nominal Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-medium",
    ),
    BatriumSensorEntityDescription(
        key="cell_setup_lo_volt",
        state_key=SENSOR_CELL_SETUP_LO_VOLT,
        name="Cell Low Voltage Threshold",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-low",
    ),
    BatriumSensorEntityDescription(
        key="cell_setup_hi_volt",
        state_key=SENSOR_CELL_SETUP_HI_VOLT,
        name="Cell High Voltage Threshold",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-high",
    ),
    BatriumSensorEntityDescription(
        key="cell_setup_bypass_volt",
        state_key=SENSOR_CELL_SETUP_BYPASS_VOLT,
        name="Bypass Activation Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:call-split",
    ),
    BatriumSensorEntityDescription(
        key="cell_setup_bypass_amp",
        state_key=SENSOR_CELL_SETUP_BYPASS_AMP,
        name="Bypass Current Limit",
        native_unit_of_measurement=UNIT_MILLIAMP,
        device_class=SensorDeviceClass.CURRENT,
        icon="mdi:current-dc",
    ),
    BatriumSensorEntityDescription(
        key="cell_setup_nom_cells",
        state_key=SENSOR_CELL_SETUP_NOM_CELLS,
        name="Nominal Cells in Series",
        icon="mdi:counter",
    ),
    # ── Shunt Setup (0x4C33/34/58) ─────────────────────────────────────
    BatriumSensorEntityDescription(
        key="shunt_setup_nom_capacity",
        state_key=SENSOR_SHUNT_SETUP_NOM_CAP,
        name="Nominal Battery Capacity",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-charging-100",
    ),
    # ── Critical Setup (0x4F33) ────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="critical_setup_cell_volt_lo",
        state_key=SENSOR_CRITICAL_CELL_VOLT_LO,
        name="Critical Cell Low Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-alert",
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_cell_volt_hi",
        state_key=SENSOR_CRITICAL_CELL_VOLT_HI,
        name="Critical Cell High Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-alert",
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_cell_temp_lo",
        state_key=SENSOR_CRITICAL_CELL_TEMP_LO,
        name="Critical Cell Low Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_cell_temp_hi",
        state_key=SENSOR_CRITICAL_CELL_TEMP_HI,
        name="Critical Cell High Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_supply_volt_lo",
        state_key=SENSOR_CRITICAL_SUPPLY_VOLT_LO,
        name="Critical Supply Low Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:sine-wave",
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_supply_volt_hi",
        state_key=SENSOR_CRITICAL_SUPPLY_VOLT_HI,
        name="Critical Supply High Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:sine-wave",
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_shunt_peak_charge",
        state_key=SENSOR_CRITICAL_SHUNT_PEAK_CHG,
        name="Critical Peak Charge Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        icon="mdi:current-dc",
    ),
    BatriumSensorEntityDescription(
        key="critical_setup_shunt_peak_dischg",
        state_key=SENSOR_CRITICAL_SHUNT_PEAK_DCH,
        name="Critical Peak Discharge Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        icon="mdi:current-dc",
    ),
    # ── Charge Setup (0x5033) ──────────────────────────────────────────
    BatriumSensorEntityDescription(
        key="charge_setup_cell_volt_hi",
        state_key=SENSOR_CHARGE_CELL_VOLT_HI,
        name="Charge Stop Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-charging-high",
    ),
    BatriumSensorEntityDescription(
        key="charge_setup_cell_volt_resume",
        state_key=SENSOR_CHARGE_CELL_VOLT_RESUME,
        name="Charge Resume Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-charging",
    ),
    BatriumSensorEntityDescription(
        key="charge_setup_soc_hi",
        state_key=SENSOR_CHARGE_SOC_HI,
        name="Charge Stop SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery-charging-high",
    ),
    BatriumSensorEntityDescription(
        key="charge_setup_soc_resume",
        state_key=SENSOR_CHARGE_SOC_RESUME,
        name="Charge Resume SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery-charging",
    ),
    # ── Discharge Setup (0x5158) ───────────────────────────────────────
    BatriumSensorEntityDescription(
        key="discharge_setup_cell_volt_lo",
        state_key=SENSOR_DISCHG_CELL_VOLT_LO,
        name="Discharge Stop Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-alert-variant-outline",
    ),
    BatriumSensorEntityDescription(
        key="discharge_setup_cell_volt_resume",
        state_key=SENSOR_DISCHG_CELL_VOLT_RESUME,
        name="Discharge Resume Cell Voltage",
        native_unit_of_measurement=UNIT_MILLIVOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:battery-minus",
    ),
    BatriumSensorEntityDescription(
        key="discharge_setup_soc_lo",
        state_key=SENSOR_DISCHG_SOC_LO,
        name="Discharge Stop SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery-alert-variant-outline",
    ),
    BatriumSensorEntityDescription(
        key="discharge_setup_soc_resume",
        state_key=SENSOR_DISCHG_SOC_RESUME,
        name="Discharge Resume SoC",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        icon="mdi:battery-minus",
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
