"""Unit tests for the Batrium UDP packet parser."""

import struct

import pytest

from custom_components.batrium.const import (
    MSG_STATUS_CONTROL_LOGIC,
    MSG_SYSTEM_DISCO,
    MSG_TELEMETRY_FAST,
    MSG_TELEMETRY_RAPID,
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
