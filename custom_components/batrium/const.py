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
MSG_CELL_STATS = 0x3E33  # Freq B: 300 ms, cell aggregate stats + node IDs
MSG_TELEMETRY_RAPID = 0x3E5A  # Freq B: 294ms
MSG_SHUNT_STATUS = 0x3F34  # Freq B: 300 ms, shunt power + precision SoC
MSG_TELEMETRY_FAST = 0x3F33  # Freq C: 1.55s
MSG_SYSTEM_DISCO = 0x5732  # Freq C: 1.55s
MSG_LOGIC_CONTROL = 0x4732  # Freq C: 1.55s
MSG_STATUS_CONTROL_LOGIC = 0x4733  # Freq C: ~2s, compact logic status
MSG_REMOTE_STATUS = 0x4932  # Freq C: 1.55s
MSG_TELEMETRY_SLOW = 0x405A  # Freq D: 22s
MSG_SYSTEM_SETUP = 0x4A33  # Freq D: 22s
MSG_CELL_GROUP_SETUP = 0x4B33  # Freq D: 22s
MSG_SHUNT_SETUP = 0x4C58  # Freq D: 22s
MSG_EXPANSION_SETUP = 0x4D58  # Freq D: 22s
MSG_REMOTE_SETUP = 0x4E58  # Freq D: 22s
MSG_CRITICAL_SETUP = 0x4F58  # Freq D: 22s
MSG_CHARGE_SETUP = 0x5033  # Freq D: 22s
MSG_DISCHARGE_SETUP = 0x5158  # Freq D: 22s
MSG_THERMAL_SETUP = 0x5258  # Freq D: 22s
MSG_INTEGRATION_SETUP = 0x5333  # Freq D: 22s
MSG_DAILY_SESSION = 0x5457  # Freq D: 22s
MSG_DAILY_SESSION_FULL = 0x5432  # Freq D: 20 s, daily session with kWh
MSG_SHUNT_METRIC = 0x7857  # Freq D: 22s
MSG_LIFE_METRIC = 0x5632  # Freq D: 22s
MSG_COMMS_STATUS = 0x6131  # Freq C: 2 s, comms link health
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

# Config flow
CONF_UDP_PORT = "udp_port"
DEFAULT_UDP_PORT = BATRIUM_UDP_PORT
