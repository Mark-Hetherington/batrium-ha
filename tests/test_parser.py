"""Unit tests for the Batrium UDP packet parser."""

import struct

import pytest

from custom_components.batrium.const import (
    MSG_CELL_GROUP_SETUP_V6,
    MSG_CELL_STATS,
    MSG_CHARGE_SETUP,
    MSG_COMMS_STATUS,
    MSG_COMMS_STATUS_FULL,
    MSG_CRITICAL_SETUP,
    MSG_DAILY_SESSION_FULL,
    MSG_DAILY_SESSION_HIST,
    MSG_DISCHARGE_SETUP,
    MSG_EXPANSION_SETUP_V4,
    MSG_HW_SHUNT_METRIC,
    MSG_HW_SYSTEM_SETUP_FULL,
    MSG_HW_SYSTEM_SETUP_V4,
    MSG_HW_SYSTEM_SETUP_V5,
    MSG_INTEGRATION_SETUP_FULL,
    MSG_INTEGRATION_SETUP_V4,
    MSG_LIFE_METRIC_A,
    MSG_LIFE_METRIC_B,
    MSG_LIFE_METRIC_V3,
    MSG_LIVE_DISPLAY,
    MSG_NETWORK_SETUP,
    MSG_QUICK_SESSION_HIST,
    MSG_REMOTE_SETUP,
    MSG_REMOTE_SETUP_FULL,
    MSG_SESSION_METRICS,
    MSG_SHUNT_SETUP,
    MSG_SHUNT_STATUS,
    MSG_STATUS_CONTROL_LOGIC,
    MSG_STATUS_RAPID,
    MSG_STATUS_SLOW_V2,
    MSG_STATUS_SLOW_V3,
    MSG_SYSTEM_DISCO,
    MSG_TELEMETRY_FAST,
    MSG_TELEMETRY_RAPID,
    MSG_THERMAL_SETUP,
    MSG_THERMAL_SETUP_FULL,
    UDP_START_HEADER,
)
from custom_components.batrium.parser import (
    _decode_soc,
    _decode_temp,
    parse_packet,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_header(msg_type: int, system_id: int = 1, hub_id: int = 0) -> bytes:
    """Build a valid 8-byte Batrium packet header."""
    buf = bytearray(8)
    buf[0] = UDP_START_HEADER  # 0x3A
    struct.pack_into("<H", buf, 1, msg_type)
    buf[3] = 0x2C  # ','
    struct.pack_into("<H", buf, 4, system_id)
    struct.pack_into("<H", buf, 6, hub_id)
    return bytes(buf)


# ---------------------------------------------------------------------------
# Encoding helpers
# ---------------------------------------------------------------------------


def test_decode_temp_zero_offset():
    assert _decode_temp(40) == 0.0


def test_decode_temp_min():
    assert _decode_temp(0) == -40.0


def test_decode_temp_max():
    assert _decode_temp(165) == 125.0


def test_decode_soc_nominal():
    # raw=10 → 10 * 0.5 - 5 = 0.0%
    assert _decode_soc(10) == 0.0


def test_decode_soc_full():
    # raw=220 → 220 * 0.5 - 5 = 105.0%
    assert _decode_soc(220) == 105.0


# ---------------------------------------------------------------------------
# Header validation
# ---------------------------------------------------------------------------


def test_bad_header_returns_none():
    data = b"\x00" * 56
    assert parse_packet(data) is None


def test_too_short_returns_none():
    assert parse_packet(b"\x3a\x5a") is None


# ---------------------------------------------------------------------------
# Rapid info (0x3E5A)
# ---------------------------------------------------------------------------


def test_rapid_parses_cell_voltages():
    header = make_header(MSG_TELEMETRY_RAPID)
    payload = bytearray(48)
    # min cell voltage = 3200 mV at offset 8 (payload offset 0)
    struct.pack_into("<H", payload, 0, 3200)
    # max cell voltage = 3450 mV at offset 10 (payload offset 2)
    struct.pack_into("<H", payload, 2, 3450)
    # avg cell voltage = 3300 mV at offset 28 (payload offset 20)
    struct.pack_into("<H", payload, 20, 3300)

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["min_cell_voltage_mv"] == 3200
    assert pkt.data["max_cell_voltage_mv"] == 3450
    assert pkt.data["avg_cell_voltage_mv"] == 3300


def test_rapid_parses_shunt_current():
    header = make_header(MSG_TELEMETRY_RAPID)
    payload = bytearray(48)
    # shunt current is a float at payload offset 34 (packet offset 42)
    struct.pack_into("<f", payload, 34, 15000.0)  # 15A charge

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert abs(pkt.data["shunt_current_ma"] - 15000.0) < 0.01


def test_rapid_parses_cell_counts():
    header = make_header(MSG_TELEMETRY_RAPID)
    payload = bytearray(48)
    # cells_active at payload offset 27, cells_in_system at offset 28
    payload[27] = 16
    payload[28] = 16

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["cells_active"] == 16
    assert pkt.data["cells_in_system"] == 16


# ---------------------------------------------------------------------------
# Fast info (0x3F33)
# ---------------------------------------------------------------------------


def test_fast_parses_soc():
    header = make_header(MSG_TELEMETRY_FAST)
    payload = bytearray(80)
    # shunt_soc at payload offset 24: raw=130 → 130*0.5-5 = 60%
    payload[24] = 130

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["status_soc_pct"] == pytest.approx(60.0)


def test_fast_parses_system_status_text():
    header = make_header(MSG_TELEMETRY_FAST)
    payload = bytearray(80)
    payload[15] = 2  # Charging

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["system_op_status_text"] == "Charging"


# ---------------------------------------------------------------------------
# System Discovery (0x5732)
# ---------------------------------------------------------------------------


def test_disco_parses_system_code():
    header = make_header(MSG_SYSTEM_DISCO)
    payload = bytearray(50)
    code = b"BATT0001"
    payload[0:8] = code

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["system_code"] == "BATT0001"


def test_disco_parses_battery_ok():
    header = make_header(MSG_SYSTEM_DISCO)
    payload = bytearray(50)
    payload[18] = 1  # battery_ok_state = True

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["battery_ok_state"] is True


# ---------------------------------------------------------------------------
# Live Display (0x3233)
# ---------------------------------------------------------------------------


def test_live_display_parses_overview():
    header = make_header(MSG_LIVE_DISPLAY)
    payload = bytearray(49)
    payload[0] = 2  # SystemOpStatus = 2 (Charging)
    payload[2] = 0b00001001  # flags1: CritBatOk + HeatOn
    payload[3] = 0b00000101  # flags2: ChargeOnState + DischgOnState
    struct.pack_into("<h", payload, 4, 3100)  # MinCellVolt = 3100 mV
    struct.pack_into("<h", payload, 6, 3650)  # MaxCellVolt = 3650 mV
    struct.pack_into("<h", payload, 8, 3375)  # AvgCellVolt = 3375 mV
    payload[10] = 55  # MinCellTemp = 55-40 = 15°C
    payload[11] = 70  # MaxCellTemp = 70-40 = 30°C
    payload[13] = 3  # NumOfCellsInBypass = 3
    struct.pack_into("<h", payload, 14, 5200)  # ShuntVoltage raw=5200 → 52000 mV
    struct.pack_into("<f", payload, 16, 20000.0)  # ShuntCurrent = 20000 mA
    struct.pack_into("<f", payload, 20, 3000.0)  # ShuntPowerVA = 3000 W
    struct.pack_into("<h", payload, 24, 7500)  # ShuntSOC = 7500/100 = 75.00%
    struct.pack_into("<f", payload, 26, 80000.0)  # NomCapacityToEmpty = 80000 mAh
    struct.pack_into("<f", payload, 30, 1500000.0)  # CumulkWhCharge = 1500 kWh
    struct.pack_into("<f", payload, 34, 1450000.0)  # CumulkWhDischg = 1450 kWh

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_LIVE_DISPLAY
    assert pkt.data["system_op_status"] == 2
    assert pkt.data["system_op_status_text"] == "Charging"
    assert pkt.data["critical_battery_ok"] is True
    assert pkt.data["thermal_heat_on"] is True
    assert pkt.data["thermal_cool_on"] is False
    assert pkt.data["charging_is_on"] is True
    assert pkt.data["discharging_is_on"] is True
    assert pkt.data["min_cell_voltage_mv"] == 3100
    assert pkt.data["max_cell_voltage_mv"] == 3650
    assert pkt.data["avg_cell_voltage_mv"] == 3375
    assert pkt.data["min_cell_temp_c"] == pytest.approx(15.0)
    assert pkt.data["cells_in_bypass"] == 3
    assert pkt.data["shunt_voltage"] == 52000
    assert pkt.data["shunt_current_ma"] == pytest.approx(20000.0)
    assert pkt.data["shunt_power_w"] == pytest.approx(3000.0)
    assert pkt.data["shunt_state_of_charge_pct"] == pytest.approx(75.0)
    assert pkt.data["shunt_capacity_to_empty_mah"] == pytest.approx(80000.0)
    assert pkt.data["shunt_cumul_charge_kwh"] == pytest.approx(1500.0)
    assert pkt.data["shunt_cumul_dischg_kwh"] == pytest.approx(1450.0)


# ---------------------------------------------------------------------------
# Cell Stats (0x3E33)
# ---------------------------------------------------------------------------


def test_cell_stats_parses_voltages_and_node_ids():
    header = make_header(MSG_CELL_STATS)
    payload = bytearray(40)
    struct.pack_into("<h", payload, 0, 3200)  # MinCellVolt = 3200 mV
    struct.pack_into("<h", payload, 2, 3600)  # MaxCellVolt = 3600 mV
    payload[4] = 3  # MinCellVoltId = node 3
    payload[5] = 11  # MaxCellVoltId = node 11
    payload[6] = 60  # MinCellTemp = 60-40 = 20°C
    payload[7] = 65  # MaxCellTemp = 65-40 = 25°C
    struct.pack_into("<h", payload, 10, 50)  # MinBypassAmp = 50 mA
    struct.pack_into("<h", payload, 12, 800)  # MaxBypassAmp = 800 mA
    struct.pack_into("<h", payload, 20, 3400)  # AvgCellVolt = 3400 mV
    payload[22] = 62  # AvgCellTemp = 62-40 = 22°C
    payload[23] = 2  # cells_above_initial_bypass
    payload[24] = 1  # cells_above_final_bypass
    payload[25] = 1  # cells_in_bypass
    payload[26] = 0  # cells_overdue
    payload[27] = 16  # cells_active
    payload[28] = 16  # cells_in_system
    struct.pack_into("<f", payload, 30, 1500.0)  # MinBypassSession = 1500 mAh
    struct.pack_into("<f", payload, 34, 3200.0)  # MaxBypassSession = 3200 mAh

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_CELL_STATS
    assert pkt.data["min_cell_voltage_mv"] == 3200
    assert pkt.data["max_cell_voltage_mv"] == 3600
    assert pkt.data["min_cell_voltage_node_id"] == 3
    assert pkt.data["max_cell_voltage_node_id"] == 11
    assert pkt.data["min_cell_temp_c"] == pytest.approx(20.0)
    assert pkt.data["max_cell_temp_c"] == pytest.approx(25.0)
    assert pkt.data["avg_cell_voltage_mv"] == 3400
    assert pkt.data["cells_active"] == 16
    assert pkt.data["min_bypass_session_mah"] == pytest.approx(1500.0)
    assert pkt.data["max_bypass_session_mah"] == pytest.approx(3200.0)


# ---------------------------------------------------------------------------
# Shunt Status (0x3F34)
# ---------------------------------------------------------------------------


def test_shunt_status_parses_power_and_precision_soc():
    header = make_header(MSG_SHUNT_STATUS)
    payload = bytearray(42)
    struct.pack_into("<h", payload, 0, 5200)  # SupplyVolt raw=5200 → 52000 mV
    payload[2] = 65  # AmbientTemp = 65-40 = 25°C
    payload[3] = 61  # ShuntTemp = 61-40 = 21°C
    struct.pack_into("<h", payload, 4, 5000)  # ShuntVoltage raw=5000 → 50000 mV
    struct.pack_into("<f", payload, 6, 15000.0)  # ShuntCurrent = 15000 mA
    struct.pack_into("<f", payload, 10, 5000.0)  # ShuntPowerVA = 5000 W
    struct.pack_into("<h", payload, 14, 6050)  # ShuntSOC = 6050/100 = 60.50%
    struct.pack_into("<f", payload, 18, 100000.0)  # CapacityToFull = 100000 mAh
    struct.pack_into("<f", payload, 22, 50000.0)  # CapacityToEmpty = 50000 mAh
    struct.pack_into("<h", payload, 26, 120)  # EstDurationToFull = 120 min
    struct.pack_into("<h", payload, 28, 60)  # EstDurationToEmpty = 60 min
    struct.pack_into("<f", payload, 30, 12000.0)  # AvgCharge = 12000 mA → 12 A
    struct.pack_into("<f", payload, 34, 8000.0)  # AvgDischg = 8000 mA → 8 A

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_SHUNT_STATUS
    assert pkt.data["system_supply_voltage_mv"] == 52000
    assert pkt.data["system_ambient_temp_c"] == pytest.approx(25.0)
    assert pkt.data["shunt_current_ma"] == pytest.approx(15000.0)
    assert pkt.data["shunt_power_w"] == pytest.approx(5000.0)
    assert pkt.data["shunt_state_of_charge_pct"] == pytest.approx(60.50)
    assert pkt.data["shunt_capacity_to_full_mah"] == pytest.approx(100000.0)
    assert pkt.data["estimated_duration_to_full_min"] == 120
    assert pkt.data["shunt_accum_avg_charge_a"] == pytest.approx(12.0)
    assert pkt.data["shunt_accum_avg_dischg_a"] == pytest.approx(8.0)


# ---------------------------------------------------------------------------
# Daily Session Full (0x5432)
# ---------------------------------------------------------------------------


def test_daily_session_full_parses_kwh():
    header = make_header(MSG_DAILY_SESSION_FULL)
    payload = bytearray(61)
    struct.pack_into("<h", payload, 0, 3100)  # MinCellVolt = 3100 mV
    struct.pack_into("<h", payload, 2, 3700)  # MaxCellVolt = 3700 mV
    payload[14] = 120  # MinShuntSoc → 55%
    payload[15] = 200  # MaxShuntSoc → 95%
    struct.pack_into("<h", payload, 32, 4500)  # PeakCharge = 4500 * 0.01 = 45 A
    struct.pack_into("<h", payload, 34, 3000)  # PeakDischg = 3000 * 0.01 = 30 A
    payload[36] = 2  # CriticalEvents = 2
    struct.pack_into("<f", payload, 45, 50000.0)  # CumulAhCharge = 50000 mAh
    struct.pack_into("<f", payload, 49, 48000.0)  # CumulAhDischg = 48000 mAh
    struct.pack_into("<f", payload, 53, 2500.0)  # CumulkWhCharge → 2.5 kWh
    struct.pack_into("<f", payload, 57, 2400.0)  # CumulkWhDischg → 2.4 kWh

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_DAILY_SESSION_FULL
    assert pkt.data["daily_min_cell_voltage_mv"] == 3100
    assert pkt.data["daily_max_cell_voltage_mv"] == 3700
    assert pkt.data["daily_min_soc_pct"] == pytest.approx(55.0)
    assert pkt.data["daily_max_soc_pct"] == pytest.approx(95.0)
    assert pkt.data["daily_peak_charge_a"] == pytest.approx(45.0)
    assert pkt.data["daily_critical_events"] == 2
    assert pkt.data["daily_cumulative_charge_mah"] == pytest.approx(50000.0)
    assert pkt.data["daily_cumulative_charge_kwh"] == pytest.approx(2.5)
    assert pkt.data["daily_cumulative_discharge_kwh"] == pytest.approx(2.4)


# ---------------------------------------------------------------------------
# Comms Status (0x6131)
# ---------------------------------------------------------------------------


def test_comms_status_parses_diagnostics():
    header = make_header(MSG_COMMS_STATUS)
    payload = bytearray(25)
    payload[4] = 2  # SystemOpStatus = 2 (Charging)
    payload[10] = 3  # WifiState = 3
    payload[14] = 1  # CanbusOpStatus = 1
    payload[19] = 4  # ShuntStatus = 4 (Charging)
    payload[23] = 2  # CmuOpStatus = 2

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_COMMS_STATUS
    assert pkt.data["system_op_status"] == 2
    assert pkt.data["system_op_status_text"] == "Charging"
    assert pkt.data["comms_wifi_state"] == 3
    assert pkt.data["comms_canbus_op_status"] == 1
    assert pkt.data["comms_cmu_op_status"] == 2


def test_comms_status_full_parses_rssi_and_cell_group():
    header = make_header(MSG_COMMS_STATUS_FULL)
    payload = bytearray(86)
    payload[4] = 3  # SystemOpStatus = 3 (Discharging)
    payload[9] = 3  # WifiState = 3 (Broadcast Running)
    payload[14] = 72  # WifiRssi = 72
    payload[15] = 1  # CanbusOpStatus = 1
    payload[22] = 1  # ShuntStatus = 1 (Discharging)
    payload[51] = 1  # CmuOpStatus = 1
    struct.pack_into("<h", payload, 56, 3250)  # GroupMinCellVolt = 3250 mV
    struct.pack_into("<h", payload, 58, 3580)  # GroupMaxCellVolt = 3580 mV
    payload[60] = 65  # GroupMinCellTemp = 65-40 = 25°C
    payload[61] = 70  # GroupMaxCellTemp = 70-40 = 30°C

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_COMMS_STATUS_FULL
    assert pkt.data["system_op_status"] == 3
    assert pkt.data["system_op_status_text"] == "Discharging"
    assert pkt.data["comms_wifi_state"] == 3
    assert pkt.data["comms_wifi_rssi"] == 72
    assert pkt.data["comms_canbus_op_status"] == 1
    assert pkt.data["comms_cmu_op_status"] == 1
    assert pkt.data["min_cell_voltage_mv"] == 3250
    assert pkt.data["max_cell_voltage_mv"] == 3580
    assert pkt.data["min_cell_temp_c"] == pytest.approx(25.0)
    assert pkt.data["max_cell_temp_c"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Thermal Setup (0x5233)
# ---------------------------------------------------------------------------


def test_thermal_setup_full_parses_thresholds():
    header = make_header(MSG_THERMAL_SETUP_FULL)
    payload = bytearray(32)
    payload[0] = 0  # ControlHeatMode = 0 (Auto)
    payload[1] = 1  # ControlHeatMonitorLoCellTemp = True
    payload[2] = 0  # ControlHeatMonitorLoAmbient = False
    payload[3] = 20  # ControlHeatLoCellTemp = 20-40 = -20°C
    payload[4] = 15  # ControlHeatLoAmbient = 15-40 = -25°C
    payload[13] = 1  # ControlCoolMode = 1 (Manually On)
    payload[14] = 1  # ControlCoolMonitorHiCellTemp = True
    payload[15] = 1  # ControlCoolMonitorHiAmbient = True
    payload[16] = 0  # ControlCoolMonitorInBypass = False
    payload[17] = 85  # ControlCoolHiCellTemp = 85-40 = 45°C
    payload[18] = 80  # ControlCoolHiAmbient = 80-40 = 40°C
    payload[28] = 10  # ControlHeatLoCellCutout = 10-40 = -30°C
    payload[29] = 5  # ControlHeatLoAmbientCutout = 5-40 = -35°C
    payload[30] = 95  # ControlCoolHiCellCutout = 95-40 = 55°C
    payload[31] = 90  # ControlCoolHiAmbientCutout = 90-40 = 50°C

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_THERMAL_SETUP_FULL
    assert pkt.data["thermal_heat_mode"] == 0
    assert pkt.data["thermal_heat_monitor_cell_temp"] is True
    assert pkt.data["thermal_heat_monitor_ambient"] is False
    assert pkt.data["thermal_heat_lo_cell_temp_c"] == pytest.approx(-20.0)
    assert pkt.data["thermal_heat_lo_ambient_c"] == pytest.approx(-25.0)
    assert pkt.data["thermal_heat_lo_cell_cutout_c"] == pytest.approx(-30.0)
    assert pkt.data["thermal_heat_lo_ambient_cutout_c"] == pytest.approx(-35.0)
    assert pkt.data["thermal_cool_mode"] == 1
    assert pkt.data["thermal_cool_monitor_cell_temp"] is True
    assert pkt.data["thermal_cool_monitor_ambient"] is True
    assert pkt.data["thermal_cool_monitor_bypass"] is False
    assert pkt.data["thermal_cool_hi_cell_temp_c"] == pytest.approx(45.0)
    assert pkt.data["thermal_cool_hi_ambient_c"] == pytest.approx(40.0)
    assert pkt.data["thermal_cool_hi_cell_cutout_c"] == pytest.approx(55.0)
    assert pkt.data["thermal_cool_hi_ambient_cutout_c"] == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# HW System Setup Full (0x4A36)
# ---------------------------------------------------------------------------


def test_hw_system_setup_full_parses_identity_and_quick_session():
    header = make_header(MSG_HW_SYSTEM_SETUP_FULL)
    payload = bytearray(74)
    # SystemCode at o+6..13
    payload[6:14] = b"BATRIUM1"
    # SysName at o+14..33
    payload[14:28] = b"My Battery Pack"
    # AssetCode at o+34..53
    payload[34:42] = b"ASSET001"
    # FirmwareVersion at o+58..59
    struct.pack_into("<h", payload, 58, 215)
    # HardwareVersion at o+60..61
    struct.pack_into("<h", payload, 60, 3)
    # SerialNo at o+62..65
    struct.pack_into("<I", payload, 62, 987654)
    # AllowQuickSession at o+69
    payload[69] = 1
    # QuickSessionInterval at o+70..73 (ms → /1000 = s)
    struct.pack_into("<I", payload, 70, 300000)  # 300 s

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_HW_SYSTEM_SETUP_FULL
    assert pkt.data["system_code"] == "BATRIUM1"
    assert pkt.data["system_name"] == "My Battery Pack"
    assert pkt.data["asset_code"] == "ASSET001"
    assert pkt.data["firmware_version"] == 215
    assert pkt.data["hardware_version"] == 3
    assert pkt.data["serial_number"] == 987654
    assert pkt.data["quick_session_enabled"] is True
    assert pkt.data["quick_session_interval_s"] == pytest.approx(300.0)


# ---------------------------------------------------------------------------
# Remote Setup (0x4E33)
# ---------------------------------------------------------------------------


def test_remote_setup_full_parses_targets_and_soc_thresholds():
    header = make_header(MSG_REMOTE_SETUP_FULL)
    payload = bytearray(58)
    struct.pack_into("<h", payload, 0, 5600)  # chg norm volt = 5600
    struct.pack_into("<h", payload, 2, 1000)  # chg norm amp = 1000
    struct.pack_into("<h", payload, 6, 5400)  # chg limp volt = 5400
    struct.pack_into("<h", payload, 8, 200)  # chg limp amp = 200
    struct.pack_into("<h", payload, 18, 4800)  # dischg norm volt = 4800
    struct.pack_into("<h", payload, 20, 800)  # dischg norm amp = 800
    struct.pack_into("<h", payload, 24, 4600)  # dischg limp volt = 4600
    struct.pack_into("<h", payload, 26, 100)  # dischg limp amp = 100
    payload[37] = 2  # template_no = 2
    struct.pack_into("<h", payload, 38, 900)  # chg ramp1 amp = 900
    struct.pack_into("<h", payload, 40, 700)  # chg ramp2 amp = 700
    struct.pack_into("<h", payload, 42, 400)  # chg ramp3 amp = 400
    payload[44] = 200  # chg ramp1 soc: _decode_soc(200) = 95%
    payload[45] = 160  # chg ramp2 soc: _decode_soc(160) = 75%
    payload[46] = 120  # chg ramp3 soc: _decode_soc(120) = 55%
    payload[47] = 20  # chg limp soc:  _decode_soc(20) = 5%
    struct.pack_into("<h", payload, 48, 600)  # dischg ramp1 amp = 600
    struct.pack_into("<h", payload, 50, 400)  # dischg ramp2 amp = 400
    struct.pack_into("<h", payload, 52, 200)  # dischg ramp3 amp = 200
    payload[57] = 30  # dischg limp soc: _decode_soc(30) = 10%

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_REMOTE_SETUP_FULL
    assert pkt.data["remote_charge_target_norm_volt"] == 5600
    assert pkt.data["remote_charge_target_norm_amp"] == 1000
    assert pkt.data["remote_charge_target_limp_volt"] == 5400
    assert pkt.data["remote_charge_target_limp_amp"] == 200
    assert pkt.data["remote_dischg_target_norm_volt"] == 4800
    assert pkt.data["remote_dischg_target_norm_amp"] == 800
    assert pkt.data["remote_template_no"] == 2
    assert pkt.data["remote_charge_ramp1_amp"] == 900
    assert pkt.data["remote_charge_ramp2_amp"] == 700
    assert pkt.data["remote_charge_ramp3_amp"] == 400
    assert pkt.data["remote_charge_ramp1_soc_pct"] == pytest.approx(95.0)
    assert pkt.data["remote_charge_ramp2_soc_pct"] == pytest.approx(75.0)
    assert pkt.data["remote_charge_ramp3_soc_pct"] == pytest.approx(55.0)
    assert pkt.data["remote_charge_limp_soc_pct"] == pytest.approx(5.0)
    assert pkt.data["remote_dischg_ramp1_amp"] == 600
    assert pkt.data["remote_dischg_limp_soc_pct"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Integration Setup (0x5335)
# ---------------------------------------------------------------------------


def test_integration_setup_full_parses_bus_config():
    header = make_header(MSG_INTEGRATION_SETUP_FULL)
    payload = bytearray(20)
    payload[1] = 1  # USB broadcast enabled
    payload[2] = 1  # WiFi broadcast enabled
    payload[3] = 3  # WiFi broadcast mode = 3 (Verbose)
    payload[4] = 1  # CANbus broadcast enabled
    payload[5] = 5  # CANbus mode = 5
    struct.pack_into("<I", payload, 6, 0x18FF50E5)  # CANbus remote addr
    struct.pack_into("<I", payload, 10, 0x300)  # CANbus base addr
    struct.pack_into("<I", payload, 14, 0x400)  # CANbus group addr
    payload[18] = 1  # MQTT broadcast enabled
    payload[19] = 2  # MQTT broadcast mode = 2

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_INTEGRATION_SETUP_FULL
    assert pkt.data["integration_usb_broadcast_enabled"] is True
    assert pkt.data["integration_wifi_broadcast_enabled"] is True
    assert pkt.data["integration_wifi_broadcast_mode"] == 3
    assert pkt.data["integration_canbus_broadcast_enabled"] is True
    assert pkt.data["integration_canbus_mode"] == 5
    assert pkt.data["integration_canbus_remote_addr"] == 0x18FF50E5
    assert pkt.data["integration_canbus_base_addr"] == 0x300
    assert pkt.data["integration_canbus_group_addr"] == 0x400
    assert pkt.data["integration_mqtt_broadcast_enabled"] is True
    assert pkt.data["integration_mqtt_broadcast_mode"] == 2


# ---------------------------------------------------------------------------
# Network Setup (0x5A32) — layout reverse-engineered from a real packet
# ---------------------------------------------------------------------------

# Real packet captured from a live WatchMon (NZ timezone, pool.ntp.org).
_RAW_5A32 = bytes.fromhex(
    "3a325a2ccf1d897e02030000010020004453542d31310000000000000000"
    "00000000000000000000000000000000000000000000000000000000000000"
    "0000000000000000706f6f6c2e6e74702e6f72670000000000000000000000"
    "0000000000000000000000"
)


def test_network_setup_parses_real_packet():
    pkt = parse_packet(_RAW_5A32)
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_NETWORK_SETUP
    assert pkt.data["ntp_enabled"] is True
    assert pkt.data["ntp_update_interval"] == 32
    assert pkt.data["ntp_timezone"] == "DST-11"
    assert pkt.data["ntp_server"] == "pool.ntp.org"


def test_network_setup_disabled_ntp():
    header = make_header(MSG_NETWORK_SETUP)
    payload = bytearray(95)
    payload[4] = 0  # ntp_enabled = False
    payload[6] = 60  # ntp_update_interval = 60
    payload[8:16] = b"UTC+0\x00\x00\x00"
    payload[61:76] = b"time.google.com"  # NTP server at payload offset 61

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["ntp_enabled"] is False
    assert pkt.data["ntp_update_interval"] == 60
    assert pkt.data["ntp_timezone"] == "UTC+0"
    assert pkt.data["ntp_server"] == "time.google.com"


# ---------------------------------------------------------------------------
# StatusControlLogic (0x4733)  # noqa: ERA001
# ---------------------------------------------------------------------------

# Real packet captured from a live WatchMon.
# Battery OK, charging + discharging both ON at Normal Power (rate=4).
_RAW_4733 = bytes.fromhex(
    "3a33472ccf1d897e0300000000000000040401800000000004040100000000000000080800000000a7"
)


def test_status_control_logic_parses_real_packet():
    pkt = parse_packet(_RAW_4733)
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_STATUS_CONTROL_LOGIC
    assert pkt.data["critical_battery_ok"] is True
    assert pkt.data["charging_is_on"] is True
    assert pkt.data["ctrl_charge_power_rate_state"] == 4
    assert pkt.data["discharging_is_on"] is True
    assert pkt.data["ctrl_dischg_power_rate_state"] == 4
    assert pkt.data["thermal_heat_on"] is False
    assert pkt.data["thermal_cool_on"] is False
    assert pkt.data["ctrl_diff_logic_ticks"] == 0xA7


def test_status_control_logic_critical_flags():
    """Verify bit extraction for critical fault flags."""
    header = make_header(MSG_STATUS_CONTROL_LOGIC)
    payload = bytearray(33)
    # byte 0 (abs 8): bits 4+5 set → cell low + cell high voltage
    payload[0] = 0b00110000
    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["critical_has_cells_low_voltage"] is True
    assert pkt.data["critical_has_cells_high_voltage"] is True
    assert pkt.data["critical_battery_ok"] is False


# ---------------------------------------------------------------------------
# Status Rapid v2 (0x3E32)
# ---------------------------------------------------------------------------


def test_status_rapid_v2_parses_cell_voltages():
    header = make_header(MSG_STATUS_RAPID)
    payload = bytearray(42)
    struct.pack_into("<h", payload, 0, 3100)  # MinCellVolt = 3100 mV
    struct.pack_into("<h", payload, 2, 3600)  # MaxCellVolt = 3600 mV
    struct.pack_into("<h", payload, 20, 3350)  # AvgCellVolt = 3350 mV
    payload[6] = 55  # MinCellTemp = 55-40 = 15°C
    payload[7] = 75  # MaxCellTemp = 75-40 = 35°C
    payload[22] = 65  # AvgCellTemp = 65-40 = 25°C
    payload[25] = 4  # NumOfCellsInBypass = 4
    payload[27] = 16  # NumOfCellsActive = 16
    payload[28] = 16  # NumOfCellsInSystem = 16

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_STATUS_RAPID
    assert pkt.data["min_cell_voltage_mv"] == 3100
    assert pkt.data["max_cell_voltage_mv"] == 3600
    assert pkt.data["avg_cell_voltage_mv"] == 3350
    assert pkt.data["min_cell_temp_c"] == pytest.approx(15.0)
    assert pkt.data["max_cell_temp_c"] == pytest.approx(35.0)
    assert pkt.data["avg_cell_temp_c"] == pytest.approx(25.0)
    assert pkt.data["cells_in_bypass"] == 4
    assert pkt.data["cells_active"] == 16
    assert pkt.data["cells_in_system"] == 16


def test_status_rapid_v2_parses_shunt_power():
    header = make_header(MSG_STATUS_RAPID)
    payload = bytearray(42)
    struct.pack_into("<f", payload, 34, 12500.0)  # ShuntCurrent = 12500 mA
    struct.pack_into("<f", payload, 38, 3200.0)  # ShuntPowerVA = 3200 W

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["shunt_current_ma"] == pytest.approx(12500.0)
    assert pkt.data["shunt_power_w"] == pytest.approx(3200.0)


# ---------------------------------------------------------------------------
# HW Shunt Metrics v2 (0x7832)
# ---------------------------------------------------------------------------


def test_hw_shunt_metric_v2_parses_soc_cycles_and_flags():
    header = make_header(MSG_HW_SHUNT_METRIC)
    payload = bytearray(24)
    payload[1] = 0b00000011  # hasShuntSocCountLo=True, hasShuntSocCountHi=True
    struct.pack_into("<h", payload, 2, 42)  # ShuntSocCycles = 42

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_HW_SHUNT_METRIC
    assert pkt.data["shunt_soc_cycles"] == 42
    assert pkt.data["has_shunt_soc_count_lo"] is True
    assert pkt.data["has_shunt_soc_count_hi"] is True


def test_hw_shunt_metric_v2_parses_recal_timestamps():
    header = make_header(MSG_HW_SHUNT_METRIC)
    payload = bytearray(24)
    struct.pack_into("<I", payload, 4, 1_700_000_000)  # RecentTimeAcculmSave
    struct.pack_into("<I", payload, 8, 1_710_000_000)  # RecentTimeSocLoRecal
    struct.pack_into("<I", payload, 12, 1_720_000_000)  # RecentTimeSocHiRecal
    struct.pack_into("<I", payload, 16, 1_730_000_000)  # RecentTimeSocCountLo
    struct.pack_into("<I", payload, 20, 1_740_000_000)  # RecentTimeSocCountHi

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["shunt_ts_accum_save"] == 1_700_000_000
    assert pkt.data["shunt_ts_soc_lo_recal"] == 1_710_000_000
    assert pkt.data["shunt_ts_soc_hi_recal"] == 1_720_000_000
    assert pkt.data["shunt_ts_soc_count_lo"] == 1_730_000_000
    assert pkt.data["shunt_ts_soc_count_hi"] == 1_740_000_000


# ---------------------------------------------------------------------------
# Life Metric v3 (0x5633) and Life Metric A (0x5635)
# ---------------------------------------------------------------------------


def test_life_metric_v3_parses_counts():
    header = make_header(MSG_LIFE_METRIC_V3)
    payload = bytearray(86)
    struct.pack_into("<I", payload, 4, 1500)  # LifeCountStartup = 1500
    struct.pack_into("<I", payload, 8, 200)  # LifeCountCriticalBattOk = 200
    struct.pack_into("<I", payload, 12, 800)  # LifeCountChargeOn = 800
    struct.pack_into("<I", payload, 16, 50)  # LifeCountChargeLimp = 50
    struct.pack_into("<I", payload, 20, 780)  # LifeCountDischgOn = 780
    struct.pack_into("<I", payload, 24, 30)  # LifeCountDischgLimp = 30
    struct.pack_into("<I", payload, 28, 12)  # LifeCountHeatOn = 12
    struct.pack_into("<I", payload, 32, 8)  # LifeCountCoolOn = 8
    struct.pack_into("<h", payload, 36, 365)  # LifeCountDailySession = 365

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_LIFE_METRIC_V3
    assert pkt.data["lifetime_count_startup"] == 1500
    assert pkt.data["lifetime_count_critical_ok"] == 200
    assert pkt.data["lifetime_count_charge_on"] == 800
    assert pkt.data["lifetime_count_charge_limp"] == 50
    assert pkt.data["lifetime_count_discharge_on"] == 780
    assert pkt.data["lifetime_count_discharge_limp"] == 30
    assert pkt.data["lifetime_count_heat_on"] == 12
    assert pkt.data["lifetime_count_cool_on"] == 8
    assert pkt.data["lifetime_count_daily_sessions"] == 365


def test_life_metric_v3_parses_timestamps():
    header = make_header(MSG_LIFE_METRIC_V3)
    payload = bytearray(86)
    struct.pack_into("<I", payload, 38, 1_700_100_000)  # RecentTimeCriticalOn
    struct.pack_into("<I", payload, 46, 1_700_200_000)  # RecentTimeChargeOn
    struct.pack_into("<I", payload, 70, 1_700_300_000)  # RecentTimeHeatOn

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["lifetime_ts_critical_on"] == 1_700_100_000
    assert pkt.data["lifetime_ts_charge_on"] == 1_700_200_000
    assert pkt.data["lifetime_ts_heat_on"] == 1_700_300_000


def test_life_metric_a_shares_same_parser():
    """0x5635 is dispatched to the same parser as 0x5633."""
    header = make_header(MSG_LIFE_METRIC_A)
    payload = bytearray(87)  # 95 bytes total (extra LifetimeSetupVers byte)
    struct.pack_into("<I", payload, 12, 999)  # LifeCountChargeOn
    struct.pack_into("<I", payload, 28, 7)  # LifeCountHeatOn

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_LIFE_METRIC_A
    assert pkt.data["lifetime_count_charge_on"] == 999
    assert pkt.data["lifetime_count_heat_on"] == 7


# ---------------------------------------------------------------------------
# Life Metric B (0x5634)
# ---------------------------------------------------------------------------


def test_life_metric_b_parses_soc_limit_counts():
    header = make_header(MSG_LIFE_METRIC_B)
    payload = bytearray(96)
    struct.pack_into("<I", payload, 24, 42)  # LifeCountSocLimit1
    struct.pack_into("<I", payload, 36, 18)  # LifeCountSocLimit2
    struct.pack_into("<I", payload, 48, 5)  # LifeCountSocLimit3
    struct.pack_into("<I", payload, 60, 2)  # LifeCountSocLimit4
    struct.pack_into("<I", payload, 72, 10)  # LifeCountAltChargeOn
    struct.pack_into("<I", payload, 84, 6)  # LifeCountAltDischgOn

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_LIFE_METRIC_B
    assert pkt.data["lifetime_count_soc_limit1"] == 42
    assert pkt.data["lifetime_count_soc_limit2"] == 18
    assert pkt.data["lifetime_count_soc_limit3"] == 5
    assert pkt.data["lifetime_count_soc_limit4"] == 2
    assert pkt.data["lifetime_count_alt_charge_on"] == 10
    assert pkt.data["lifetime_count_alt_dischg_on"] == 6


def test_life_metric_b_parses_timestamps():
    header = make_header(MSG_LIFE_METRIC_B)
    payload = bytearray(96)
    struct.pack_into("<I", payload, 28, 1_710_000_000)  # RecentTimeSocLimit1On
    struct.pack_into("<I", payload, 32, 1_710_100_000)  # RecentTimeSocLimit1Off
    struct.pack_into("<I", payload, 76, 1_720_000_000)  # RecentTimeAltChargeOn

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["lifetime_ts_soc_limit1_on"] == 1_710_000_000
    assert pkt.data["lifetime_ts_soc_limit1_off"] == 1_710_100_000
    assert pkt.data["lifetime_ts_alt_charge_on"] == 1_720_000_000


# ---------------------------------------------------------------------------
# Session Metrics (0x5431)
# ---------------------------------------------------------------------------


def test_session_metrics_parses_record_counts():
    header = make_header(MSG_SESSION_METRICS)
    payload = bytearray(17)
    struct.pack_into("<I", payload, 0, 1_750_000_000)  # QuickSessRecentTime
    struct.pack_into("<h", payload, 4, 96)  # QuickSessNumOfRecords
    struct.pack_into("<h", payload, 6, 288)  # QuickSessMaxNumOfRecords
    struct.pack_into("<I", payload, 8, 300_000)  # QuickSessionInterval = 300 s
    payload[12] = 1  # AllowQuickSession = True
    struct.pack_into("<h", payload, 13, 30)  # DailySessNumOfRecords
    struct.pack_into("<h", payload, 15, 365)  # DailySessMaxNumOfRecords

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_SESSION_METRICS
    assert pkt.data["quick_session_recent_time"] == 1_750_000_000
    assert pkt.data["quick_session_num_records"] == 96
    assert pkt.data["quick_session_max_records"] == 288
    assert pkt.data["quick_session_interval_s"] == pytest.approx(300.0)
    assert pkt.data["quick_session_enabled"] is True
    assert pkt.data["daily_session_num_records"] == 30
    assert pkt.data["daily_session_max_records"] == 365


# ---------------------------------------------------------------------------
# Status Slow v2 (0x4032)
# ---------------------------------------------------------------------------


def test_slow_v2_parses_duration_and_soc_flags():
    header = make_header(MSG_STATUS_SLOW_V2)
    payload = bytearray(58)
    struct.pack_into("<h", payload, 20, 90)  # EstDurationToFullmins = 90
    struct.pack_into("<h", payload, 22, 45)  # EstDurationToEmptymins = 45
    struct.pack_into("<f", payload, 24, 12000.0)  # ShuntAcculmAvgCharge = 12 A
    struct.pack_into("<f", payload, 28, 8000.0)  # ShuntAcculmAvgDischg = 8 A
    payload[36] = 1  # hasShuntSocCountLo = True
    payload[37] = 0  # hasShuntSocCountHi = False

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_STATUS_SLOW_V2
    assert pkt.data["estimated_duration_to_full_min"] == 90
    assert pkt.data["estimated_duration_to_empty_min"] == 45
    assert pkt.data["shunt_accum_avg_charge_a"] == pytest.approx(12.0)
    assert pkt.data["shunt_accum_avg_dischg_a"] == pytest.approx(8.0)
    assert pkt.data["has_shunt_soc_count_lo"] is True
    assert pkt.data["has_shunt_soc_count_hi"] is False


# ---------------------------------------------------------------------------
# Status Slow v3 (0x4033)
# ---------------------------------------------------------------------------


def test_slow_v3_parses_session_records():
    header = make_header(MSG_STATUS_SLOW_V3)
    payload = bytearray(58)
    struct.pack_into("<h", payload, 4, 30)  # DailySessNumOfRecords = 30
    struct.pack_into("<h", payload, 6, 365)  # DailySessMaxNumOfRecords = 365
    struct.pack_into("<h", payload, 12, 96)  # QuickSessNumOfRecords = 96
    struct.pack_into("<h", payload, 14, 288)  # QuickSessMaxNumOfRecords = 288
    struct.pack_into("<I", payload, 8, 300_000)  # QuickSessionInterval = 300 s
    struct.pack_into("<f", payload, 18, 200_000.0)  # NomCapacityToEmpty = 200 Ah

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_STATUS_SLOW_V3
    assert pkt.data["daily_session_num_records"] == 30
    assert pkt.data["daily_session_max_records"] == 365
    assert pkt.data["quick_session_num_records"] == 96
    assert pkt.data["quick_session_max_records"] == 288
    assert pkt.data["quick_session_interval_s"] == pytest.approx(300.0)
    assert pkt.data["shunt_setup_nom_capacity_ah"] == pytest.approx(200.0)


# ---------------------------------------------------------------------------
# HW System Setup v4/v5 (0x4A34 / 0x4A35)
# ---------------------------------------------------------------------------


def test_hw_system_setup_v4_parses_identity():
    header = make_header(MSG_HW_SYSTEM_SETUP_V4)
    payload = bytearray(66)
    payload[2:10] = b"BATT0001"  # SystemCode at o+2
    payload[10:30] = (
        b"My Battery Pack\x00\x00\x00\x00\x00"  # SysName at o+10 (20 bytes)
    )
    payload[51] = 1  # AllowQuickSession
    struct.pack_into("<I", payload, 52, 120_000)  # QuickSessionInterval = 120 s
    struct.pack_into("<h", payload, 58, 220)  # FirmwareVersion
    struct.pack_into("<h", payload, 60, 4)  # HardwareVersion
    struct.pack_into("<I", payload, 62, 123456)  # SerialNo

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_HW_SYSTEM_SETUP_V4
    assert pkt.data["system_code"] == "BATT0001"
    assert pkt.data["quick_session_enabled"] is True
    assert pkt.data["quick_session_interval_s"] == pytest.approx(120.0)
    assert pkt.data["firmware_version"] == 220
    assert pkt.data["hardware_version"] == 4
    assert pkt.data["serial_number"] == 123456


def test_hw_system_setup_v5_dispatches_to_same_parser():
    header = make_header(MSG_HW_SYSTEM_SETUP_V5)
    payload = bytearray(68)  # 76 bytes total
    payload[2:10] = b"BATT0002"
    struct.pack_into("<h", payload, 58, 215)

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_HW_SYSTEM_SETUP_V5
    assert pkt.data["system_code"] == "BATT0002"
    assert pkt.data["firmware_version"] == 215


# ---------------------------------------------------------------------------
# Cell Group Setup (0x4B36)
# ---------------------------------------------------------------------------


def test_cellgroup_setup_parses_voltage_thresholds():
    header = make_header(MSG_CELL_GROUP_SETUP_V6)
    payload = bytearray(47)
    payload[2] = 1  # HwCellmonFirstID
    payload[3] = 16  # HwCellmonLastID
    struct.pack_into("<h", payload, 4, 3600)  # NomCellVolt = 3600 mV
    struct.pack_into("<h", payload, 6, 2800)  # LoCellVolt = 2800 mV
    struct.pack_into("<h", payload, 8, 4200)  # HiCellVolt = 4200 mV
    struct.pack_into("<h", payload, 10, 4150)  # BypassVoltLevel = 4150 mV
    struct.pack_into("<h", payload, 12, 500)  # BypassAmpLimit = 500 mA
    payload[14] = 75  # BypassTempLimit = 75-40 = 35°C
    payload[15] = 20  # LoCellTemp = 20-40 = -20°C
    payload[16] = 85  # HiCellTemp = 85-40 = 45°C
    payload[18] = 16  # NomCellsInSeries

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_CELL_GROUP_SETUP_V6
    assert pkt.data["cell_setup_first_id"] == 1
    assert pkt.data["cell_setup_last_id"] == 16
    assert pkt.data["cell_setup_nom_cell_volt_mv"] == 3600
    assert pkt.data["cell_setup_lo_cell_volt_mv"] == 2800
    assert pkt.data["cell_setup_hi_cell_volt_mv"] == 4200
    assert pkt.data["cell_setup_bypass_volt_mv"] == 4150
    assert pkt.data["cell_setup_bypass_amp_limit_ma"] == 500
    assert pkt.data["cell_setup_bypass_temp_limit_c"] == pytest.approx(35.0)
    assert pkt.data["cell_setup_lo_cell_temp_c"] == pytest.approx(-20.0)
    assert pkt.data["cell_setup_hi_cell_temp_c"] == pytest.approx(45.0)
    assert pkt.data["cell_setup_nom_cells_in_series"] == 16


# ---------------------------------------------------------------------------
# Shunt Setup (0x4C58)
# ---------------------------------------------------------------------------


def test_shunt_setup_parses_nom_capacity():
    header = make_header(MSG_SHUNT_SETUP)
    payload = bytearray(38)
    struct.pack_into("<f", payload, 16, 200.0)  # HwShuntNomCapacity = 200 Ah
    payload[36] = 0  # HwShuntReverseFlow = False

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_SHUNT_SETUP
    assert pkt.data["shunt_setup_nom_capacity_ah"] == pytest.approx(200.0)
    assert pkt.data["shunt_setup_reverse_flow"] is False


# ---------------------------------------------------------------------------
# Expansion Setup (0x4D34)
# ---------------------------------------------------------------------------


def test_expansion_setup_parses_relay_modes():
    header = make_header(MSG_EXPANSION_SETUP_V4)
    payload = bytearray(24)
    payload[1] = 3  # HwExpansionTemplate = 3
    payload[3] = 5  # HwExpansionRelay1 = 5
    payload[4] = 6  # HwExpansionRelay2 = 6
    payload[5] = 7  # HwExpansionRelay3 = 7
    payload[6] = 8  # HwExpansionRelay4 = 8

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_EXPANSION_SETUP_V4
    assert pkt.data["expansion_setup_template"] == 3
    assert pkt.data["expansion_setup_relay1"] == 5
    assert pkt.data["expansion_setup_relay2"] == 6
    assert pkt.data["expansion_setup_relay3"] == 7
    assert pkt.data["expansion_setup_relay4"] == 8


# ---------------------------------------------------------------------------
# Control Remote Setup (0x4E58)
# ---------------------------------------------------------------------------


def test_remote_setup_parses_charge_discharge_targets():
    header = make_header(MSG_REMOTE_SETUP)
    payload = bytearray(37)
    struct.pack_into("<h", payload, 0, 5600)  # ChargeTargetNormVolt
    struct.pack_into("<h", payload, 2, 1000)  # ChargeTargetNormAmp
    struct.pack_into("<h", payload, 6, 5400)  # ChargeTargetLimpVolt
    struct.pack_into("<h", payload, 8, 200)  # ChargeTargetLimpAmp
    struct.pack_into("<h", payload, 18, 4800)  # DischargeTargetNormVolt
    struct.pack_into("<h", payload, 20, 800)  # DischargeTargetNormAmp
    struct.pack_into("<h", payload, 24, 4600)  # DischargeTargetLimpVolt
    struct.pack_into("<h", payload, 26, 100)  # DischargeTargetLimpAmp

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_REMOTE_SETUP
    assert pkt.data["remote_charge_target_norm_volt"] == 5600
    assert pkt.data["remote_charge_target_norm_amp"] == 1000
    assert pkt.data["remote_charge_target_limp_volt"] == 5400
    assert pkt.data["remote_dischg_target_norm_volt"] == 4800
    assert pkt.data["remote_dischg_target_limp_amp"] == 100


# ---------------------------------------------------------------------------
# Control Critical Setup (0x4F33)
# ---------------------------------------------------------------------------


def test_critical_setup_parses_protection_thresholds():
    header = make_header(MSG_CRITICAL_SETUP)
    payload = bytearray(67)
    struct.pack_into("<h", payload, 5, 2700)  # CellVoltLo = 2700 mV
    struct.pack_into("<h", payload, 7, 4250)  # CellVoltHi = 4250 mV
    payload[11] = 20  # CellTempLo = 20-40 = -20°C
    payload[12] = 85  # CellTempHi = 85-40 = 45°C
    struct.pack_into("<h", payload, 15, 4000)  # SupplyVoltLo = 4000 mV
    struct.pack_into("<h", payload, 17, 5800)  # SupplyVoltHi = 5800 mV
    struct.pack_into("<h", payload, 33, 5000)  # ShuntPeakCharge = 5000/100 = 50 A
    struct.pack_into("<h", payload, 38, 4000)  # ShuntPeakDischg = 4000/100 = 40 A

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_CRITICAL_SETUP
    assert pkt.data["critical_setup_cell_volt_lo_mv"] == 2700
    assert pkt.data["critical_setup_cell_volt_hi_mv"] == 4250
    assert pkt.data["critical_setup_cell_temp_lo_c"] == pytest.approx(-20.0)
    assert pkt.data["critical_setup_cell_temp_hi_c"] == pytest.approx(45.0)
    assert pkt.data["critical_setup_supply_volt_lo_mv"] == 4000
    assert pkt.data["critical_setup_supply_volt_hi_mv"] == 5800
    assert pkt.data["critical_setup_shunt_peak_charge_a"] == pytest.approx(50.0)
    assert pkt.data["critical_setup_shunt_peak_dischg_a"] == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# Control Charge Setup (0x5033)
# ---------------------------------------------------------------------------


def test_charge_setup_parses_limits():
    header = make_header(MSG_CHARGE_SETUP)
    payload = bytearray(52)
    struct.pack_into("<h", payload, 22, 4200)  # CellVoltHi = 4200 mV
    struct.pack_into("<h", payload, 24, 4150)  # CellVoltResume = 4150 mV
    payload[36] = 210  # ShuntSocHi: _decode_soc(210) = 100%
    payload[37] = 180  # ShuntSocResume: _decode_soc(180) = 85%

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_CHARGE_SETUP
    assert pkt.data["charge_setup_cell_volt_hi_mv"] == 4200
    assert pkt.data["charge_setup_cell_volt_resume_mv"] == 4150
    assert pkt.data["charge_setup_shunt_soc_hi_pct"] == pytest.approx(100.0)
    assert pkt.data["charge_setup_shunt_soc_resume_pct"] == pytest.approx(85.0)


# ---------------------------------------------------------------------------
# Control Discharge Setup (0x5158)
# ---------------------------------------------------------------------------


def test_discharge_setup_parses_limits():
    header = make_header(MSG_DISCHARGE_SETUP)
    payload = bytearray(41)
    struct.pack_into("<h", payload, 16, 2800)  # CellVoltLo = 2800 mV
    struct.pack_into("<h", payload, 18, 2900)  # CellVoltResume = 2900 mV
    payload[30] = 20  # ShuntSocLo: _decode_soc(20) = 5%
    payload[31] = 30  # ShuntSocResume: _decode_soc(30) = 10%

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_DISCHARGE_SETUP
    assert pkt.data["discharge_setup_cell_volt_lo_mv"] == 2800
    assert pkt.data["discharge_setup_cell_volt_resume_mv"] == 2900
    assert pkt.data["discharge_setup_shunt_soc_lo_pct"] == pytest.approx(5.0)
    assert pkt.data["discharge_setup_shunt_soc_resume_pct"] == pytest.approx(10.0)


# ---------------------------------------------------------------------------
# Control Thermal Setup (0x5258)
# ---------------------------------------------------------------------------


def test_thermal_setup_parses_heat_cool_thresholds():
    header = make_header(MSG_THERMAL_SETUP)
    payload = bytearray(28)
    payload[0] = 1  # ControlHeatMode = 1
    payload[1] = 1  # MonitorLoCellTemp = True
    payload[2] = 0  # MonitorLoAmbient = False
    payload[3] = 25  # HeatLoCellTemp = 25-40 = -15°C
    payload[4] = 20  # HeatLoAmbient = 20-40 = -20°C
    payload[13] = 0  # ControlCoolMode = 0
    payload[14] = 1  # MonitorHiCellTemp = True
    payload[15] = 1  # MonitorHiAmbient = True
    payload[16] = 0  # MonitorInBypass = False
    payload[17] = 85  # CoolHiCellTemp = 85-40 = 45°C
    payload[18] = 80  # CoolHiAmbient = 80-40 = 40°C

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_THERMAL_SETUP
    assert pkt.data["thermal_heat_mode"] == 1
    assert pkt.data["thermal_heat_monitor_cell_temp"] is True
    assert pkt.data["thermal_heat_monitor_ambient"] is False
    assert pkt.data["thermal_heat_lo_cell_temp_c"] == pytest.approx(-15.0)
    assert pkt.data["thermal_heat_lo_ambient_c"] == pytest.approx(-20.0)
    assert pkt.data["thermal_cool_mode"] == 0
    assert pkt.data["thermal_cool_monitor_cell_temp"] is True
    assert pkt.data["thermal_cool_hi_cell_temp_c"] == pytest.approx(45.0)
    assert pkt.data["thermal_cool_hi_ambient_c"] == pytest.approx(40.0)


# ---------------------------------------------------------------------------
# HW Integration Setup v4 (0x5334)
# ---------------------------------------------------------------------------


def test_integration_setup_v4_parses_bus_config():
    header = make_header(MSG_INTEGRATION_SETUP_V4)
    payload = bytearray(18)
    payload[1] = 1  # USB broadcast enabled
    payload[2] = 1  # WiFi broadcast enabled
    payload[3] = 3  # WiFi broadcast mode
    payload[4] = 1  # CANbus broadcast enabled
    payload[5] = 5  # CANbus mode
    struct.pack_into("<I", payload, 6, 0x18FF50E5)  # CANbus remote addr
    struct.pack_into("<I", payload, 10, 0x300)  # CANbus base addr
    struct.pack_into("<I", payload, 14, 0x400)  # CANbus group addr

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_INTEGRATION_SETUP_V4
    assert pkt.data["integration_usb_broadcast_enabled"] is True
    assert pkt.data["integration_wifi_broadcast_mode"] == 3
    assert pkt.data["integration_canbus_mode"] == 5
    assert pkt.data["integration_canbus_remote_addr"] == 0x18FF50E5
    assert pkt.data["integration_canbus_base_addr"] == 0x300
    assert pkt.data["integration_canbus_group_addr"] == 0x400
    # No MQTT fields in 0x5334 (unlike 0x5335)
    assert "integration_mqtt_broadcast_enabled" not in pkt.data


# ---------------------------------------------------------------------------
# Daily Session History (0x5831)
# ---------------------------------------------------------------------------


def test_daily_session_hist_parses_identity_and_cell_stats():
    header = make_header(MSG_DAILY_SESSION_HIST)
    payload = bytearray(52)
    struct.pack_into("<h", payload, 0, 42)  # SessionId = 42
    struct.pack_into("<I", payload, 2, 1_750_000_000)  # SessionTime (epoch)
    payload[6] = 3  # CriticalEvents = 3
    payload[8] = 55  # MinReportTemp = 55-40 = 15°C
    payload[9] = 75  # MaxReportTemp = 75-40 = 35°C
    payload[10] = 130  # MinShuntSoc = 130*0.5-5 = 60%
    payload[11] = 180  # MaxShuntSoc = 180*0.5-5 = 85%
    struct.pack_into("<h", payload, 12, 3100)  # MinCellVolt = 3100 mV
    struct.pack_into("<h", payload, 14, 3700)  # MaxCellVolt = 3700 mV
    struct.pack_into("<h", payload, 16, 480)  # MinSupplyVolt raw=480 → 4800 mV
    struct.pack_into("<h", payload, 18, 530)  # MaxSupplyVolt raw=530 → 5300 mV
    struct.pack_into("<h", payload, 40, 4500)  # ShuntPeakCharge = 4500/100 = 45 A
    struct.pack_into("<h", payload, 42, 3000)  # ShuntPeakDischg = 3000/100 = 30 A
    struct.pack_into("<h", payload, 44, 500)  # CumulCharge = 500/10 = 50 Ah
    struct.pack_into("<h", payload, 46, 480)  # CumulDischg = 480/10 = 48 Ah

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_DAILY_SESSION_HIST
    assert pkt.data["hist_session_id"] == 42
    assert pkt.data["hist_session_time"] == 1_750_000_000
    assert pkt.data["hist_critical_events"] == 3
    assert pkt.data["hist_min_temp_c"] == pytest.approx(15.0)
    assert pkt.data["hist_max_temp_c"] == pytest.approx(35.0)
    assert pkt.data["hist_min_soc_pct"] == pytest.approx(60.0)
    assert pkt.data["hist_max_soc_pct"] == pytest.approx(85.0)
    assert pkt.data["hist_min_cell_volt_mv"] == 3100
    assert pkt.data["hist_max_cell_volt_mv"] == 3700
    assert pkt.data["hist_min_supply_volt_mv"] == 4800
    assert pkt.data["hist_max_supply_volt_mv"] == 5300
    assert pkt.data["hist_peak_charge_a"] == pytest.approx(45.0)
    assert pkt.data["hist_peak_dischg_a"] == pytest.approx(30.0)
    assert pkt.data["hist_cumul_charge_ah"] == pytest.approx(50.0)
    assert pkt.data["hist_cumul_dischg_ah"] == pytest.approx(48.0)


def test_daily_session_hist_parses_band_hours():
    header = make_header(MSG_DAILY_SESSION_HIST)
    payload = bytearray(52)
    # Thermal bands at payload offsets 24-31 (packet offsets 32-39), raw÷10 = hours
    payload[24] = 20  # band A = 2.0 h
    payload[25] = 35  # band B = 3.5 h
    payload[26] = 0  # band C = 0.0 h
    # SoC bands at payload offsets 32-39
    payload[32] = 10  # SoC band A = 1.0 h
    payload[39] = 240  # SoC band H = 24.0 h

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.data["hist_thermal_bands_h"][0] == pytest.approx(2.0)
    assert pkt.data["hist_thermal_bands_h"][1] == pytest.approx(3.5)
    assert pkt.data["hist_thermal_bands_h"][2] == pytest.approx(0.0)
    assert pkt.data["hist_soc_bands_h"][0] == pytest.approx(1.0)
    assert pkt.data["hist_soc_bands_h"][7] == pytest.approx(24.0)


# ---------------------------------------------------------------------------
# Quick Session History (0x6831)
# ---------------------------------------------------------------------------


def test_quick_session_hist_parses_snapshot():
    header = make_header(MSG_QUICK_SESSION_HIST)
    payload = bytearray(24)
    struct.pack_into("<h", payload, 0, 100)  # SessionId = 100
    struct.pack_into("<I", payload, 2, 1_760_000_000)  # SessionTime (epoch)
    payload[6] = 2  # SystemOpState = 2 (Charging)
    payload[7] = 1  # ControlLogic = 1
    struct.pack_into("<h", payload, 8, 3350)  # MinCellVolt = 3350 mV
    struct.pack_into("<h", payload, 10, 3420)  # MaxCellVolt = 3420 mV
    struct.pack_into("<h", payload, 12, 3385)  # AvgCellVolt = 3385 mV
    payload[14] = 65  # AvgCellTemp = 65-40 = 25°C
    struct.pack_into("<h", payload, 15, 7500)  # SocHiRes = 7500/100 = 75.0%
    struct.pack_into("<h", payload, 17, 500)  # ShuntVolt raw=500 → 5000 mV
    struct.pack_into("<f", payload, 19, 10_000.0)  # ShuntAmp raw=10000 → 10 A
    payload[23] = 2  # CellsInBypass = 2

    pkt = parse_packet(header + bytes(payload))
    assert pkt is not None
    assert pkt.raw_msg_type == MSG_QUICK_SESSION_HIST
    assert pkt.data["hist_session_id"] == 100
    assert pkt.data["hist_session_time"] == 1_760_000_000
    assert pkt.data["hist_system_op_state"] == 2
    assert pkt.data["hist_system_op_state_text"] == "Charging"
    assert pkt.data["hist_min_cell_volt_mv"] == 3350
    assert pkt.data["hist_max_cell_volt_mv"] == 3420
    assert pkt.data["hist_avg_cell_volt_mv"] == 3385
    assert pkt.data["hist_avg_cell_temp_c"] == pytest.approx(25.0)
    assert pkt.data["hist_soc_pct"] == pytest.approx(75.0)
    assert pkt.data["hist_shunt_volt_mv"] == 5000
    assert pkt.data["hist_shunt_amp_a"] == pytest.approx(10.0)
    assert pkt.data["hist_cells_in_bypass"] == 2


# ---------------------------------------------------------------------------
# Unknown message type
# ---------------------------------------------------------------------------


def test_unknown_msg_type_returns_packet_with_empty_data():
    header = make_header(0xFFFF)
    payload = bytearray(20)
    pkt = parse_packet(header + bytes(payload))
    # Should return a packet but with empty data (unhandled type)
    assert pkt is not None
    assert pkt.data == {}
