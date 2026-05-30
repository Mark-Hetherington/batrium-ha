"""Constants for the Batrium BMS integration."""

DOMAIN = "batrium"

# UDP configuration
BATRIUM_UDP_PORT = 18542
BATRIUM_BROADCAST_IP = "255.255.255.255"

# Header byte
UDP_START_HEADER = 0x3A  # ':'
UDP_SEPARATOR = 0x2C  # ','

# Packet offsets
OFFSET_MSG_TYPE = 1  # UInt16 at pos 1..2
OFFSET_SYSTEM_ID = 4  # UInt16 at pos 4..5
OFFSET_HUB_ID = 6  # UInt16 at pos 6..7
OFFSET_PAYLOAD = 8  # Data begins at byte 8

# Message type identifiers
MSG_CELL_BASIC_STATUS = 0x415A  # Freq A: 147ms
MSG_CELL_FULL_INFO = 0x4232  # Freq A: 147ms
MSG_LIVE_DISPLAY = 0x3233  # Freq C: 2 s, compact live overview
MSG_CELL_STATS = 0x3E33  # Freq B: 300 ms, cell aggregate stats + node IDs
MSG_STATUS_RAPID = 0x3E32  # Freq B: 300 ms, rapid status v2 (adds shunt power)
MSG_TELEMETRY_RAPID = 0x3E5A  # Freq B: 294ms
MSG_SHUNT_STATUS = 0x3F34  # Freq B: 300 ms, shunt power + precision SoC
MSG_TELEMETRY_FAST = 0x3F33  # Freq C: 1.55s
MSG_SYSTEM_DISCO = 0x5732  # Freq C: 1.55s
MSG_HW_SYSTEM_SETUP_FULL = 0x4A36  # Freq D: 30 s, system setup v6 + quick session
MSG_REMOTE_SETUP_FULL = 0x4E33  # Freq D: 40 s, remote charge/discharge targets
MSG_LOGIC_CONTROL = 0x4732  # Freq C: 1.55s
MSG_STATUS_CONTROL_LOGIC = 0x4733  # Freq C: ~2s, compact logic status
MSG_REMOTE_STATUS = 0x4932  # Freq C: 1.55s
MSG_STATUS_SLOW_V2 = 0x4032  # Freq D: 30 s, slow status v2 (setup versions + duration)
MSG_STATUS_SLOW_V3 = 0x4033  # Freq D: 30 s, slow status v3 (session records + shunt info)
MSG_TELEMETRY_SLOW = 0x405A  # Freq D: 22s
MSG_SYSTEM_SETUP = 0x4A33  # Freq D: 22s
MSG_HW_SYSTEM_SETUP_V4 = 0x4A34  # Freq D, HW system setup v4
MSG_HW_SYSTEM_SETUP_V5 = 0x4A35  # Freq D, HW system setup v5
MSG_CELL_GROUP_SETUP = 0x4B33  # Freq D: 22s (no upstream payload, kept for reference)
MSG_CELL_GROUP_SETUP_V4 = 0x4B34  # Freq D, cell group setup v4
MSG_CELL_GROUP_SETUP_V5 = 0x4B35  # Freq D, cell group setup v5
MSG_CELL_GROUP_SETUP_V6 = 0x4B36  # Freq D, cell group setup v6
MSG_SHUNT_SETUP_V3 = 0x4C33  # Freq D, shunt setup v3
MSG_SHUNT_SETUP_V4 = 0x4C34  # Freq D, shunt setup v4
MSG_SHUNT_SETUP = 0x4C58  # Freq D: 22s
MSG_EXPANSION_SETUP_V3 = 0x4D33  # Freq D, expansion setup v3
MSG_EXPANSION_SETUP_V4 = 0x4D34  # Freq D, expansion setup v4
MSG_EXPANSION_SETUP = 0x4D58  # Freq D: 22s (no upstream payload, kept for reference)
MSG_REMOTE_SETUP = 0x4E58  # Freq D: 22s
MSG_CRITICAL_SETUP = 0x4F33  # Freq D, critical protection setup
MSG_CHARGE_SETUP = 0x5033  # Freq D: 22s
MSG_DISCHARGE_SETUP = 0x5158  # Freq D: 22s
MSG_THERMAL_SETUP = 0x5258  # Freq D: 22s
MSG_INTEGRATION_SETUP = 0x5333  # Freq D: 22s (no upstream payload, kept for reference)
MSG_INTEGRATION_SETUP_V4 = 0x5334  # Freq D, integration setup v4 (no MQTT)
MSG_DAILY_SESSION = 0x5457  # Freq D: 22s
MSG_THERMAL_SETUP_FULL = 0x5233  # Freq D: 22 s, thermal control configuration
MSG_DAILY_SESSION_FULL = 0x5432  # Freq D: 20 s, daily session with kWh
MSG_SESSION_METRICS = 0x5431  # Freq D: 30 s, quick/daily session record metadata
MSG_DAILY_SESSION_HIST = 0x5831  # Freq D: ~30 s, historical daily session record (ID-indexed)
MSG_QUICK_SESSION_HIST = 0x6831  # Freq D: ~30 s, historical quick session record (ID-indexed)
MSG_HW_SHUNT_METRIC = 0x7832  # Freq D: 30 s, shunt metrics v2 with SoC recal timestamps
MSG_SHUNT_METRIC = 0x7857  # Freq D: 22s
MSG_INTEGRATION_SETUP_FULL = 0x5335  # Freq D: 30 s, integration bus config
MSG_NETWORK_SETUP = 0x5A32  # Freq D: ~30 s, NTP + timezone config (undocumented)
MSG_LIFE_METRIC = 0x5632  # Freq D: 22s
MSG_LIFE_METRIC_V3 = 0x5633  # Freq D: 30 s, lifetime event counts v3
MSG_LIFE_METRIC_B = 0x5634  # Freq D: 30 s, lifetime bypass/SoC limit metrics
MSG_LIFE_METRIC_A = (
    0x5635  # Freq D: 30 s, lifetime event counts v5 (superset of 0x5633)
)
MSG_COMMS_STATUS = 0x6131  # Freq C: 2 s, comms link health
MSG_COMMS_STATUS_V1 = 0x6132  # Freq C: 2 s, comms link health (legacy v1)
MSG_COMMS_STATUS_FULL = 0x6133  # Freq B: 300 ms, detailed comms + WiFi RSSI

# Legacy message types (also handled)
MSG_LEGACY_FAST = 0x3F5A
MSG_LEGACY_DISCO = 0x5775
MSG_LEGACY_LOGIC = 0x475A
MSG_LEGACY_REMOTE = 0x495A
MSG_LEGACY_CELL_FULL = 0x4258

# System Op Status codes
SYSTEM_OP_STATUS = {
    0: "Timeout",
    1: "Idle",
    2: "Charging",
    3: "Discharging",
    4: "Full",
    5: "Empty",
    6: "Simulator",
    7: "CriticalPending",
    8: "CriticalOffline",
    9: "MqttOffline",
    10: "AuthSetup",
}

# Shunt Status codes
SHUNT_STATUS = {
    0: "Timeout",
    1: "Discharging",
    2: "Idle",
    4: "Charging",
}

# Cell Node Status codes
CELL_NODE_STATUS = {
    0: "None",
    1: "HighVolt",
    2: "HighTemp",
    3: "Ok",
    4: "Timeout",
    5: "LowVolt",
    6: "Disabled",
    7: "InBypass",
    8: "InitialBypass",
    9: "FinalBypass",
    10: "MissingSetup",
    11: "NoConfig",
    12: "CellOutLimits",
    255: "Undefined",
}

# Sensor keys
# --- Rapid (0x3E5A) ---
SENSOR_MIN_CELL_VOLT = "min_cell_voltage_mv"
SENSOR_MAX_CELL_VOLT = "max_cell_voltage_mv"
SENSOR_AVG_CELL_VOLT = "avg_cell_voltage_mv"
SENSOR_MIN_CELL_TEMP = "min_cell_temp_c"
SENSOR_MAX_CELL_TEMP = "max_cell_temp_c"  # from fast msg
SENSOR_AVG_CELL_TEMP = "avg_cell_temp_c"
SENSOR_MIN_BYPASS_CURRENT = "min_bypass_current_ma"
SENSOR_MAX_BYPASS_CURRENT = "max_bypass_current_ma"
SENSOR_CELLS_ABOVE_INIT_BP = "cells_above_initial_bypass"
SENSOR_CELLS_ABOVE_FINAL_BP = "cells_above_final_bypass"
SENSOR_CELLS_IN_BYPASS = "cells_in_bypass"
SENSOR_CELLS_OVERDUE = "cells_overdue"
SENSOR_CELLS_ACTIVE = "cells_active"
SENSOR_CELLS_IN_SYSTEM = "cells_in_system"
SENSOR_SHUNT_VOLTAGE = "shunt_voltage"
SENSOR_SHUNT_CURRENT_MA = "shunt_current_ma"

# --- Fast (0x3F33) ---
SENSOR_SYSTEM_OP_STATUS = "system_op_status"
SENSOR_SYSTEM_SUPPLY_VOLT = "system_supply_voltage_mv"
SENSOR_SYSTEM_AMBIENT_TEMP = "system_ambient_temp_c"
SENSOR_SHUNT_SOC = "shunt_state_of_charge_pct"
SENSOR_SHUNT_CELSIUS = "shunt_temp_c"
SENSOR_SHUNT_CAP_FULL = "shunt_capacity_to_full_mah"
SENSOR_SHUNT_CAP_EMPTY = "shunt_capacity_to_empty_mah"
SENSOR_SHUNT_STATUS = "shunt_status"

# --- Discovery (0x5732) ---
SENSOR_SYSTEM_CODE = "system_code"
SENSOR_FIRMWARE_VERSION = "firmware_version"
SENSOR_HARDWARE_VERSION = "hardware_version"
SENSOR_CHARGE_POWER_RATE = "charge_power_rate"
SENSOR_DISCHARGE_POWER_RATE = "discharge_power_rate"
SENSOR_BATT_OK_STATE = "battery_ok_state"

# --- Slow (0x405A) ---
SENSOR_DURATION_TO_FULL = "estimated_duration_to_full_min"
SENSOR_DURATION_TO_EMPTY = "estimated_duration_to_empty_min"
SENSOR_RECENT_CHARGE_MAH = "recent_charge_mah"
SENSOR_RECENT_DISCHARGE_MAH = "recent_discharge_mah"
SENSOR_RECENT_NETT_MAH = "recent_nett_mah"

# --- HW System Setup Full (0x4A36) ---
SENSOR_QUICK_SESSION_INTERVAL = "quick_session_interval_s"

# --- Thermal Setup (0x5233) ---
SENSOR_THERMAL_HEAT_MODE = "thermal_heat_mode"
SENSOR_THERMAL_HEAT_LO_CELL_TEMP = "thermal_heat_lo_cell_temp_c"
SENSOR_THERMAL_HEAT_LO_AMBIENT = "thermal_heat_lo_ambient_c"
SENSOR_THERMAL_HEAT_LO_CELL_CUTOUT = "thermal_heat_lo_cell_cutout_c"
SENSOR_THERMAL_HEAT_LO_AMBIENT_CUTOUT = "thermal_heat_lo_ambient_cutout_c"
SENSOR_THERMAL_COOL_MODE = "thermal_cool_mode"
SENSOR_THERMAL_COOL_HI_CELL_TEMP = "thermal_cool_hi_cell_temp_c"
SENSOR_THERMAL_COOL_HI_AMBIENT = "thermal_cool_hi_ambient_c"
SENSOR_THERMAL_COOL_HI_CELL_CUTOUT = "thermal_cool_hi_cell_cutout_c"
SENSOR_THERMAL_COOL_HI_AMBIENT_CUTOUT = "thermal_cool_hi_ambient_cutout_c"

# --- Live Display (0x3233) ---
SENSOR_SHUNT_CUMUL_CHARGE_KWH = "shunt_cumul_charge_kwh"
SENSOR_SHUNT_CUMUL_DISCHG_KWH = "shunt_cumul_dischg_kwh"

# --- Cell Stats (0x3E33) ---
SENSOR_MIN_CELL_VOLT_NODE = "min_cell_voltage_node_id"
SENSOR_MAX_CELL_VOLT_NODE = "max_cell_voltage_node_id"
SENSOR_MIN_BYPASS_SESSION = "min_bypass_session_mah"
SENSOR_MAX_BYPASS_SESSION = "max_bypass_session_mah"

# --- Shunt Status (0x3F34) ---
SENSOR_SHUNT_POWER_W = "shunt_power_w"
SENSOR_SHUNT_AVG_CHARGE_A = "shunt_accum_avg_charge_a"
SENSOR_SHUNT_AVG_DISCHG_A = "shunt_accum_avg_dischg_a"

# --- Daily Session Full (0x5432) ---
SENSOR_DAILY_CHARGE_KWH = "daily_cumulative_charge_kwh"
SENSOR_DAILY_DISCHG_KWH = "daily_cumulative_discharge_kwh"

# --- Comms Status (0x6131 / 0x6133) ---
SENSOR_COMMS_WIFI_STATE = "comms_wifi_state"
SENSOR_COMMS_WIFI_RSSI = "comms_wifi_rssi"
SENSOR_COMMS_CANBUS = "comms_canbus_op_status"
SENSOR_COMMS_CMU = "comms_cmu_op_status"

# --- Status Control Logic (0x4733) ---
SENSOR_CTRL_CHARGE_POWER_RATE = "ctrl_charge_power_rate_state"
SENSOR_CTRL_DISCHG_POWER_RATE = "ctrl_dischg_power_rate_state"

# --- Life Metric (0x5632 base) ---
SENSOR_LIFE_COUNT_STARTUP = "lifetime_count_startup"
SENSOR_LIFE_COUNT_CRIT_OK = "lifetime_count_critical_ok"
SENSOR_LIFE_COUNT_CHARGE_ON = "lifetime_count_charge_on"
SENSOR_LIFE_COUNT_DISCHG_ON = "lifetime_count_discharge_on"
SENSOR_LIFE_COUNT_DAILY = "lifetime_count_daily_sessions"

# --- Life Metric v3/A (0x5633/0x5635) ---
SENSOR_LIFE_COUNT_CHARGE_LIMP = "lifetime_count_charge_limp"
SENSOR_LIFE_COUNT_DISCHG_LIMP = "lifetime_count_discharge_limp"
SENSOR_LIFE_COUNT_HEAT_ON = "lifetime_count_heat_on"
SENSOR_LIFE_COUNT_COOL_ON = "lifetime_count_cool_on"

# --- Life Metric B (0x5634) ---
SENSOR_LIFE_COUNT_SOC_LIMIT1 = "lifetime_count_soc_limit1"
SENSOR_LIFE_COUNT_SOC_LIMIT2 = "lifetime_count_soc_limit2"
SENSOR_LIFE_COUNT_SOC_LIMIT3 = "lifetime_count_soc_limit3"
SENSOR_LIFE_COUNT_SOC_LIMIT4 = "lifetime_count_soc_limit4"
SENSOR_LIFE_COUNT_ALT_CHARGE = "lifetime_count_alt_charge_on"
SENSOR_LIFE_COUNT_ALT_DISCHG = "lifetime_count_alt_dischg_on"

# --- Session Metrics (0x5431) ---
SENSOR_QUICK_SESSION_NUM_RECORDS = "quick_session_num_records"
SENSOR_QUICK_SESSION_MAX_RECORDS = "quick_session_max_records"
SENSOR_DAILY_SESSION_NUM_RECORDS = "daily_session_num_records"
SENSOR_DAILY_SESSION_MAX_RECORDS = "daily_session_max_records"

# --- Cell Group Setup (0x4B34/35/36) ---
SENSOR_CELL_SETUP_NOM_VOLT = "cell_setup_nom_cell_volt_mv"
SENSOR_CELL_SETUP_LO_VOLT = "cell_setup_lo_cell_volt_mv"
SENSOR_CELL_SETUP_HI_VOLT = "cell_setup_hi_cell_volt_mv"
SENSOR_CELL_SETUP_BYPASS_VOLT = "cell_setup_bypass_volt_mv"
SENSOR_CELL_SETUP_BYPASS_AMP = "cell_setup_bypass_amp_limit_ma"
SENSOR_CELL_SETUP_NOM_CELLS = "cell_setup_nom_cells_in_series"

# --- Shunt Setup (0x4C33/34/58) ---
SENSOR_SHUNT_SETUP_NOM_CAP = "shunt_setup_nom_capacity_ah"

# --- Critical Setup (0x4F33) ---
SENSOR_CRITICAL_CELL_VOLT_LO = "critical_setup_cell_volt_lo_mv"
SENSOR_CRITICAL_CELL_VOLT_HI = "critical_setup_cell_volt_hi_mv"
SENSOR_CRITICAL_CELL_TEMP_LO = "critical_setup_cell_temp_lo_c"
SENSOR_CRITICAL_CELL_TEMP_HI = "critical_setup_cell_temp_hi_c"
SENSOR_CRITICAL_SUPPLY_VOLT_LO = "critical_setup_supply_volt_lo_mv"
SENSOR_CRITICAL_SUPPLY_VOLT_HI = "critical_setup_supply_volt_hi_mv"
SENSOR_CRITICAL_SHUNT_PEAK_CHG = "critical_setup_shunt_peak_charge_a"
SENSOR_CRITICAL_SHUNT_PEAK_DCH = "critical_setup_shunt_peak_dischg_a"

# --- Charge Setup (0x5033) ---
SENSOR_CHARGE_CELL_VOLT_HI = "charge_setup_cell_volt_hi_mv"
SENSOR_CHARGE_CELL_VOLT_RESUME = "charge_setup_cell_volt_resume_mv"
SENSOR_CHARGE_SOC_HI = "charge_setup_shunt_soc_hi_pct"
SENSOR_CHARGE_SOC_RESUME = "charge_setup_shunt_soc_resume_pct"

# --- Discharge Setup (0x5158) ---
SENSOR_DISCHG_CELL_VOLT_LO = "discharge_setup_cell_volt_lo_mv"
SENSOR_DISCHG_CELL_VOLT_RESUME = "discharge_setup_cell_volt_resume_mv"
SENSOR_DISCHG_SOC_LO = "discharge_setup_shunt_soc_lo_pct"
SENSOR_DISCHG_SOC_RESUME = "discharge_setup_shunt_soc_resume_pct"

# Config flow
CONF_UDP_PORT = "udp_port"
DEFAULT_UDP_PORT = BATRIUM_UDP_PORT
