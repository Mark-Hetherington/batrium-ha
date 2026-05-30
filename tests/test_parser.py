"""Unit tests for the Batrium UDP packet parser."""

import struct

import pytest

from custom_components.batrium.const import (
    MSG_CELL_STATS,
    MSG_COMMS_STATUS,
    MSG_COMMS_STATUS_FULL,
    MSG_DAILY_SESSION_FULL,
    MSG_HW_SYSTEM_SETUP_FULL,
    MSG_LIVE_DISPLAY,
    MSG_SHUNT_STATUS,
    MSG_STATUS_CONTROL_LOGIC,
    MSG_SYSTEM_DISCO,
    MSG_TELEMETRY_FAST,
    MSG_TELEMETRY_RAPID,
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
    assert pkt.data["shunt_state_of_charge_pct"] == pytest.approx(60.0)


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
# Unknown message type
# ---------------------------------------------------------------------------


def test_unknown_msg_type_returns_packet_with_empty_data():
    header = make_header(0xFFFF)
    payload = bytearray(20)
    pkt = parse_packet(header + bytes(payload))
    # Should return a packet but with empty data (unhandled type)
    assert pkt is not None
    assert pkt.data == {}
