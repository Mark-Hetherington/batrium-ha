"""
Batrium WatchMon UDP protocol parser (v0.5).

All offsets match the official Batrium documentation.
Payload data starts at byte 8 of the UDP datagram.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from typing import Any

from .const import (
    CELL_NODE_STATUS,
    MSG_CELL_BASIC_STATUS,
    MSG_CELL_FULL_INFO,
    MSG_CELL_STATS,
    MSG_COMMS_STATUS,
    MSG_COMMS_STATUS_FULL,
    MSG_DAILY_SESSION,
    MSG_DAILY_SESSION_FULL,
    MSG_HW_SYSTEM_SETUP_FULL,
    MSG_LEGACY_CELL_FULL,
    MSG_LEGACY_DISCO,
    MSG_LEGACY_FAST,
    MSG_LEGACY_LOGIC,
    MSG_LEGACY_REMOTE,
    MSG_LIFE_METRIC,
    MSG_LIVE_DISPLAY,
    MSG_LOGIC_CONTROL,
    MSG_REMOTE_STATUS,
    MSG_SHUNT_METRIC,
    MSG_SHUNT_STATUS,
    MSG_STATUS_CONTROL_LOGIC,
    MSG_SYSTEM_DISCO,
    MSG_SYSTEM_SETUP,
    MSG_TELEMETRY_FAST,
    MSG_TELEMETRY_RAPID,
    MSG_TELEMETRY_SLOW,
    MSG_THERMAL_SETUP_FULL,
    OFFSET_MSG_TYPE,
    OFFSET_PAYLOAD,
    OFFSET_SYSTEM_ID,
    SHUNT_STATUS,
    SYSTEM_OP_STATUS,
    UDP_START_HEADER,
)

_LOGGER = logging.getLogger(__name__)


# Temperature helpers
def _decode_temp(raw: int) -> float:
    """Decode temperature: 1°C/bit with 40°C offset. Range -40 to +125°C."""
    return float(raw) - 40.0


def _decode_soc(raw: int) -> float:
    """Decode SoC: 0.5%/bit with 5% offset. Range -5% to +105%."""
    return float(raw) * 0.5 - 5.0


@dataclass
class BatriumPacket:
    """Parsed Batrium UDP packet."""

    raw_msg_type: int = 0
    system_id: int = 0
    hub_id: int = 0
    data: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Individual message parsers  (parse_packet is defined after these)
# ---------------------------------------------------------------------------


def _parse_rapid(p: bytes) -> dict:
    """0x3E5A - Telemetry Combined Status Rapid Info (48 bytes payload)."""
    o = OFFSET_PAYLOAD
    min_cell_v = struct.unpack_from("<H", p, o + 0)[0]  # offset 8
    max_cell_v = struct.unpack_from("<H", p, o + 2)[0]  # offset 10
    min_cell_v_ref = p[o + 4]  # offset 12
    max_cell_v_ref = p[o + 5]  # offset 13
    min_cell_t = _decode_temp(p[o + 6])  # offset 14
    max_cell_t = _decode_temp(p[o + 7])  # offset 15
    min_cell_t_ref = p[o + 8]  # offset 16
    max_cell_t_ref = p[o + 9]  # offset 17
    min_bp_cur = struct.unpack_from("<H", p, o + 10)[0]  # offset 18
    max_bp_cur = struct.unpack_from("<H", p, o + 12)[0]  # offset 20
    min_bp_cur_ref = p[o + 14]  # offset 22
    max_bp_cur_ref = p[o + 15]  # offset 23
    min_bp_t = _decode_temp(p[o + 16])  # offset 24
    max_bp_t = _decode_temp(p[o + 17])  # offset 25
    min_bp_t_ref = p[o + 18]  # offset 26
    max_bp_t_ref = p[o + 19]  # offset 27
    avg_cell_v = struct.unpack_from("<H", p, o + 20)[0]  # offset 28
    avg_cell_t = _decode_temp(p[o + 22])  # offset 30
    cells_init_bp = p[o + 23]  # offset 31
    cells_final_bp = p[o + 24]  # offset 32
    cells_in_bp = p[o + 25]  # offset 33
    cells_overdue = p[o + 26]  # offset 34
    cells_active = p[o + 27]  # offset 35
    cells_in_sys = p[o + 28]  # offset 36
    shunt_v = struct.unpack_from("<H", p, o + 32)[0]  # offset 40
    shunt_a = struct.unpack_from("<f", p, o + 34)[0]  # offset 42 (float mA)
    shunt_rx_ticks = p[o + 38]  # offset 46
    shunt_tx_ticks = p[o + 39]  # offset 47

    return {
        "min_cell_voltage_mv": min_cell_v,
        "max_cell_voltage_mv": max_cell_v,
        "avg_cell_voltage_mv": avg_cell_v,
        "min_cell_voltage_ref": min_cell_v_ref,
        "max_cell_voltage_ref": max_cell_v_ref,
        "min_cell_temp_c": min_cell_t,
        "max_cell_temp_c": max_cell_t,
        "avg_cell_temp_c": avg_cell_t,
        "min_cell_temp_ref": min_cell_t_ref,
        "max_cell_temp_ref": max_cell_t_ref,
        "min_bypass_current_ma": min_bp_cur,
        "max_bypass_current_ma": max_bp_cur,
        "min_bypass_current_ref": min_bp_cur_ref,
        "max_bypass_current_ref": max_bp_cur_ref,
        "min_bypass_temp_c": min_bp_t,
        "max_bypass_temp_c": max_bp_t,
        "min_bypass_temp_ref": min_bp_t_ref,
        "max_bypass_temp_ref": max_bp_t_ref,
        "cells_above_initial_bypass": cells_init_bp,
        "cells_above_final_bypass": cells_final_bp,
        "cells_in_bypass": cells_in_bp,
        "cells_overdue": cells_overdue,
        "cells_active": cells_active,
        "cells_in_system": cells_in_sys,
        "shunt_voltage_raw": shunt_v,
        "shunt_current_ma": shunt_a,
        "shunt_rx_ticks": shunt_rx_ticks,
        "shunt_tx_ticks": shunt_tx_ticks,
    }


def _parse_fast(p: bytes) -> dict:
    """0x3F33 - Telemetry Combined Status Fast Info (80 bytes)."""
    o = OFFSET_PAYLOAD
    cmu_poller_mode = p[o + 0]  # offset 8
    min_cell_v = struct.unpack_from("<H", p, o + 5)[0]  # offset 13
    max_cell_v = struct.unpack_from("<H", p, o + 7)[0]  # offset 15
    min_cell_t = _decode_temp(p[o + 9])  # offset 17
    max_cell_t = _decode_temp(p[o + 10])  # offset 18
    sys_op_status = p[o + 15]  # offset 23
    sys_auth_mode = p[o + 16]  # offset 24
    sys_supply_v = struct.unpack_from("<H", p, o + 17)[0]  # offset 25
    sys_ambient_t = _decode_temp(p[o + 19])  # offset 27
    sys_device_time = struct.unpack_from("<I", p, o + 20)[0]  # offset 28
    shunt_soc = _decode_soc(p[o + 24])  # offset 32
    shunt_celsius = _decode_temp(p[o + 25])  # offset 33
    shunt_cap_full = struct.unpack_from("<f", p, o + 26)[0]  # offset 34
    shunt_cap_empty = struct.unpack_from("<f", p, o + 30)[0]  # offset 38
    shunt_poller = p[o + 34]  # offset 42
    shunt_status = p[o + 35]  # offset 43
    exp_batt_on = bool(p[o + 38])  # offset 46
    exp_batt_off = bool(p[o + 39])  # offset 47
    exp_load_on = bool(p[o + 40])  # offset 48
    exp_load_off = bool(p[o + 41])  # offset 49
    exp_relay1 = bool(p[o + 42])  # offset 50
    exp_relay2 = bool(p[o + 43])  # offset 51
    exp_relay3 = bool(p[o + 44])  # offset 52
    exp_relay4 = bool(p[o + 45])  # offset 53

    return {
        "cmu_poller_mode": cmu_poller_mode,
        "min_cell_voltage_mv": min_cell_v,
        "max_cell_voltage_mv": max_cell_v,
        "min_cell_temp_c": min_cell_t,
        "max_cell_temp_c": max_cell_t,
        "system_op_status": sys_op_status,
        "system_op_status_text": SYSTEM_OP_STATUS.get(
            sys_op_status, f"Unknown({sys_op_status})"
        ),
        "system_auth_mode": sys_auth_mode,
        "system_supply_voltage_mv": sys_supply_v,
        "system_ambient_temp_c": sys_ambient_t,
        "system_device_time": sys_device_time,
        "shunt_state_of_charge_pct": shunt_soc,
        "shunt_temp_c": shunt_celsius,
        "shunt_capacity_to_full_mah": shunt_cap_full,
        "shunt_capacity_to_empty_mah": shunt_cap_empty,
        "shunt_poller_mode": shunt_poller,
        "shunt_status": shunt_status,
        "shunt_status_text": SHUNT_STATUS.get(shunt_status, f"Unknown({shunt_status})"),
        "expansion_battery_on": exp_batt_on,
        "expansion_battery_off": exp_batt_off,
        "expansion_load_on": exp_load_on,
        "expansion_load_off": exp_load_off,
        "expansion_relay1": exp_relay1,
        "expansion_relay2": exp_relay2,
        "expansion_relay3": exp_relay3,
        "expansion_relay4": exp_relay4,
    }


def _parse_disco(p: bytes) -> dict:
    """0x5732 - System Discovery Information (50 bytes)."""
    o = OFFSET_PAYLOAD
    sys_code = p[o : o + 8].rstrip(b"\x00").decode("ascii", errors="replace")
    fw_version = struct.unpack_from("<H", p, o + 8)[0]  # offset 16
    hw_version = struct.unpack_from("<H", p, o + 10)[0]  # offset 18
    device_time = struct.unpack_from("<I", p, o + 12)[0]  # offset 20
    sys_op_status = p[o + 16]  # offset 24
    sys_auth_mode = p[o + 17]  # offset 25
    batt_ok = bool(p[o + 18])  # offset 26
    charge_rate = p[o + 19]  # offset 27
    discharge_rate = p[o + 20]  # offset 28
    heat_on = bool(p[o + 21])  # offset 29
    cool_on = bool(p[o + 22])  # offset 30
    min_cell_v = struct.unpack_from("<H", p, o + 23)[0]  # offset 31
    max_cell_v = struct.unpack_from("<H", p, o + 25)[0]  # offset 33
    avg_cell_v = struct.unpack_from("<H", p, o + 27)[0]  # offset 35
    min_cell_t = _decode_temp(p[o + 29])  # offset 37
    num_active = p[o + 30]  # offset 38
    shunt_soc = _decode_soc(p[o + 33])  # offset 41
    shunt_v = struct.unpack_from("<H", p, o + 34)[0]  # offset 42
    shunt_a = struct.unpack_from("<f", p, o + 36)[0]  # offset 44
    shunt_status = p[o + 40]  # offset 48

    return {
        "system_code": sys_code,
        "firmware_version": fw_version,
        "hardware_version": hw_version,
        "device_time": device_time,
        "system_op_status": sys_op_status,
        "system_op_status_text": SYSTEM_OP_STATUS.get(
            sys_op_status, f"Unknown({sys_op_status})"
        ),
        "system_auth_mode": sys_auth_mode,
        "battery_ok_state": batt_ok,
        "charge_power_rate": charge_rate,
        "discharge_power_rate": discharge_rate,
        "heat_on": heat_on,
        "cool_on": cool_on,
        "min_cell_voltage_mv": min_cell_v,
        "max_cell_voltage_mv": max_cell_v,
        "avg_cell_voltage_mv": avg_cell_v,
        "min_cell_temp_c": min_cell_t,
        "num_active_cellmons": num_active,
        "shunt_state_of_charge_pct": shunt_soc,
        "shunt_voltage_raw": shunt_v,
        "shunt_current_ma": shunt_a,
        "shunt_status": shunt_status,
        "shunt_status_text": SHUNT_STATUS.get(shunt_status, f"Unknown({shunt_status})"),
    }


def _parse_logic_control(p: bytes) -> dict:
    """0x4732 - Telemetry Logic Control Status Info (79 bytes)."""
    o = OFFSET_PAYLOAD
    return {
        "critical_battery_ok": bool(p[o + 0]),
        "critical_battery_ok_live": bool(p[o + 1]),
        "critical_is_transition": bool(p[o + 2]),
        "critical_has_cells_overdue": bool(p[o + 3]),
        "critical_has_cells_low_voltage": bool(p[o + 4]),
        "critical_has_cells_high_voltage": bool(p[o + 5]),
        "critical_has_cells_low_temp": bool(p[o + 6]),
        "critical_has_cells_high_temp": bool(p[o + 7]),
        "critical_has_supply_volt_low": bool(p[o + 8]),
        "critical_has_supply_volt_high": bool(p[o + 9]),
        "critical_has_ambient_temp_low": bool(p[o + 10]),
        "critical_has_ambient_temp_high": bool(p[o + 11]),
        "critical_has_shunt_volt_low": bool(p[o + 12]),
        "critical_has_shunt_volt_high": bool(p[o + 13]),
        "critical_has_shunt_low_idle": bool(p[o + 14]),
        "critical_has_shunt_peak_charge": bool(p[o + 15]),
        "critical_has_shunt_peak_discharge": bool(p[o + 16]),
        "charging_is_on": bool(p[o + 17]),
        "charging_is_limited_power": bool(p[o + 18]),
        "charging_is_transition": bool(p[o + 19]),
        "charging_power_rate": p[o + 20],
        "charging_power_rate_live": p[o + 21],
        "discharging_is_on": bool(p[o + 41]),
        "discharging_is_limited_power": bool(p[o + 42]),
        "discharging_is_transition": bool(p[o + 43]),
        "discharging_power_rate": p[o + 44],
        "discharging_power_rate_live": p[o + 45],
        "thermal_heat_on": bool(p[o + 60]),
        "thermal_heat_on_live": bool(p[o + 61]),
        "thermal_cool_on": bool(p[o + 65]),
        "thermal_cool_on_live": bool(p[o + 66]),
    }


def _parse_remote_status(p: bytes) -> dict:
    """0x4932 - Telemetry Remote Status Info (62 bytes)."""
    o = OFFSET_PAYLOAD
    charge_actual_temp = p[o + 3]  # offset 11
    charge_target_v = struct.unpack_from("<H", p, o + 4)[0]  # offset 12, 10mV/bit
    charge_target_a = struct.unpack_from("<H", p, o + 6)[0]  # offset 14, 10mA/bit
    charge_actual_v = struct.unpack_from("<H", p, o + 10)[0]  # offset 18
    charge_actual_a = struct.unpack_from("<H", p, o + 12)[0]  # offset 20
    discharge_actual_v = struct.unpack_from("<H", p, o + 36)[0]  # offset 44
    discharge_actual_a = struct.unpack_from("<H", p, o + 38)[0]  # offset 46

    return {
        "charge_actual_celsius": charge_actual_temp,
        "charge_target_voltage_v": charge_target_v * 0.01,
        "charge_target_current_a": charge_target_a * 0.01,
        "charge_actual_voltage_v": charge_actual_v * 0.01,
        "charge_actual_current_a": charge_actual_a * 0.01,
        "discharge_actual_voltage_v": discharge_actual_v * 0.01,
        "discharge_actual_current_a": discharge_actual_a * 0.01,
    }


def _parse_slow(p: bytes) -> dict:
    """0x405A - Telemetry Combined Status Slow Info (46 bytes)."""
    o = OFFSET_PAYLOAD
    startup_time = struct.unpack_from("<I", p, o + 0)[0]  # offset 8
    duration_full = struct.unpack_from("<H", p, o + 20)[0]  # offset 28
    duration_empty = struct.unpack_from("<H", p, o + 22)[0]  # offset 30
    recent_charge = struct.unpack_from("<f", p, o + 24)[0]  # offset 32
    recent_dischg = struct.unpack_from("<f", p, o + 28)[0]  # offset 36
    recent_nett = struct.unpack_from("<f", p, o + 32)[0]  # offset 40
    soc_lo = bool(p[o + 36])  # offset 44
    soc_hi = bool(p[o + 37])  # offset 45

    return {
        "startup_time": startup_time,
        "estimated_duration_to_full_min": duration_full,
        "estimated_duration_to_empty_min": duration_empty,
        "recent_charge_mah": recent_charge,
        "recent_discharge_mah": recent_dischg,
        "recent_nett_mah": recent_nett,
        "has_shunt_soc_count_lo": soc_lo,
        "has_shunt_soc_count_hi": soc_hi,
    }


def _parse_system_setup(p: bytes) -> dict:
    """0x4A33 - Hardware System Setup configuration (68 bytes)."""
    o = OFFSET_PAYLOAD
    fw_version = struct.unpack_from("<H", p, o + 2)[0]  # offset 10
    hw_version = struct.unpack_from("<H", p, o + 4)[0]  # offset 12
    serial_num = struct.unpack_from("<I", p, o + 6)[0]  # offset 14
    sys_code = (
        p[o + 10 : o + 18].rstrip(b"\x00").decode("ascii", errors="replace")
    )  # offset 18
    sys_name = (
        p[o + 18 : o + 38].rstrip(b"\x00").decode("ascii", errors="replace")
    )  # offset 26
    asset_code = (
        p[o + 38 : o + 58].rstrip(b"\x00").decode("ascii", errors="replace")
    )  # offset 46

    return {
        "firmware_version": fw_version,
        "hardware_version": hw_version,
        "serial_number": serial_num,
        "system_code": sys_code,
        "system_name": sys_name,
        "asset_code": asset_code,
    }


def _parse_hw_system_setup_full(p: bytes) -> dict:
    """0x4A36 - HW System Setup v6 (82 bytes, 30 s). Superset of 0x4A33."""
    o = OFFSET_PAYLOAD
    fw_version = struct.unpack_from("<h", p, o + 58)[0]
    hw_version = struct.unpack_from("<h", p, o + 60)[0]
    serial_num = struct.unpack_from("<I", p, o + 62)[0]
    sys_code = p[o + 6 : o + 14].rstrip(b"\x00").decode("ascii", errors="replace")
    sys_name = p[o + 14 : o + 34].rstrip(b"\x00").decode("ascii", errors="replace")
    asset_code = p[o + 34 : o + 54].rstrip(b"\x00").decode("ascii", errors="replace")
    quick_session = bool(p[o + 69])
    quick_interval_ms = struct.unpack_from("<I", p, o + 70)[0]
    return {
        # Reuse existing system-setup state_keys
        "firmware_version": fw_version,
        "hardware_version": hw_version,
        "serial_number": serial_num,
        "system_code": sys_code,
        "system_name": sys_name,
        "asset_code": asset_code,
        # New: quick session configuration
        "quick_session_enabled": quick_session,
        "quick_session_interval_s": quick_interval_ms / 1000.0,
    }


def _parse_daily_session(p: bytes) -> dict:
    """0x5457 - Telemetry Daily Session Info (61 bytes)."""
    o = OFFSET_PAYLOAD
    min_cell_v = struct.unpack_from("<H", p, o + 0)[0]  # offset 8
    max_cell_v = struct.unpack_from("<H", p, o + 2)[0]  # offset 10
    min_soc = _decode_soc(p[o + 14])  # offset 22
    max_soc = _decode_soc(p[o + 15])  # offset 23
    peak_chg = struct.unpack_from("<H", p, o + 32)[0]  # offset 40
    peak_dischg = struct.unpack_from("<H", p, o + 34)[0]  # offset 42
    crit_events = p[o + 36]  # offset 44
    start_time = struct.unpack_from("<I", p, o + 37)[0]  # offset 45
    finish_time = struct.unpack_from("<I", p, o + 41)[0]  # offset 49
    cum_charge = struct.unpack_from("<f", p, o + 45)[0]  # offset 53
    cum_dischg = struct.unpack_from("<f", p, o + 49)[0]  # offset 57

    return {
        "daily_min_cell_voltage_mv": min_cell_v,
        "daily_max_cell_voltage_mv": max_cell_v,
        "daily_min_soc_pct": min_soc,
        "daily_max_soc_pct": max_soc,
        "daily_peak_charge_a": peak_chg * 0.01,
        "daily_peak_discharge_a": peak_dischg * 0.01,
        "daily_critical_events": crit_events,
        "daily_start_time": start_time,
        "daily_finish_time": finish_time,
        "daily_cumulative_charge_mah": cum_charge,
        "daily_cumulative_discharge_mah": cum_dischg,
    }


def _parse_shunt_metric(p: bytes) -> dict:
    """0x7857 - Telemetry Shunt Metric Info (76 bytes)."""
    o = OFFSET_PAYLOAD
    soc_cycles = struct.unpack_from("<H", p, o + 0)[0]  # offset 8
    est_full_min = struct.unpack_from("<H", p, o + 24)[0]  # offset 32
    est_empty_min = struct.unpack_from("<H", p, o + 26)[0]  # offset 34
    recent_chg = struct.unpack_from("<f", p, o + 28)[0]  # offset 36
    recent_dischg = struct.unpack_from("<f", p, o + 32)[0]  # offset 40
    recent_nett = struct.unpack_from("<f", p, o + 36)[0]  # offset 44
    serial_num = struct.unpack_from("<I", p, o + 40)[0]  # offset 48

    return {
        "shunt_soc_cycles": soc_cycles,
        "shunt_est_duration_full_min": est_full_min,
        "shunt_est_duration_empty_min": est_empty_min,
        "shunt_recent_charge_avg_mah": recent_chg,
        "shunt_recent_discharge_avg_mah": recent_dischg,
        "shunt_recent_nett_mah": recent_nett,
        "shunt_serial_number": serial_num,
    }


def _parse_life_metric(p: bytes) -> dict:
    """0x5632 - Telemetry Lifetime Metrics Info (115 bytes)."""
    o = OFFSET_PAYLOAD
    count_startup = struct.unpack_from("<I", p, o + 4)[0]  # offset 12
    count_crit_ok = struct.unpack_from("<I", p, o + 8)[0]  # offset 16
    count_chg_on = struct.unpack_from("<I", p, o + 12)[0]  # offset 20
    count_dischg_on = struct.unpack_from("<I", p, o + 20)[0]  # offset 28
    count_daily = struct.unpack_from("<H", p, o + 36)[0]  # offset 44

    return {
        "lifetime_count_startup": count_startup,
        "lifetime_count_critical_ok": count_crit_ok,
        "lifetime_count_charge_on": count_chg_on,
        "lifetime_count_discharge_on": count_dischg_on,
        "lifetime_count_daily_sessions": count_daily,
    }


def _parse_cell_basic_status(p: bytes) -> dict:
    """0x415A - Individual Cells Basic Status (variable length)."""
    o = OFFSET_PAYLOAD
    cmu_rx_node_id = p[o + 0]  # offset 8
    records = p[o + 1]  # offset 9
    first_node_id = p[o + 2]  # offset 10
    last_node_id = p[o + 3]  # offset 11

    cells = []
    idx = o + 4  # offset 12
    record_size = 11  # bytes per cell record
    for _ in range(records):
        if idx + record_size > len(p):
            break
        node_id = p[idx + 0]
        usn = p[idx + 1]
        min_cv = struct.unpack_from("<H", p, idx + 2)[0]
        max_cv = struct.unpack_from("<H", p, idx + 4)[0]
        max_ct = _decode_temp(p[idx + 6])
        bypass_t = _decode_temp(p[idx + 7])
        bypass_a = struct.unpack_from("<H", p, idx + 8)[0]
        node_status = p[idx + 10]
        cells.append(
            {
                "node_id": node_id,
                "usn": usn,
                "min_cell_voltage_mv": min_cv,
                "max_cell_voltage_mv": max_cv,
                "max_cell_temp_c": max_ct,
                "bypass_temp_c": bypass_t,
                "bypass_current_ma": bypass_a,
                "status": node_status,
                "status_text": CELL_NODE_STATUS.get(
                    node_status, f"Unknown({node_status})"
                ),
            }
        )
        idx += record_size

    return {
        "cmu_rx_node_id": cmu_rx_node_id,
        "cell_records": records,
        "first_node_id": first_node_id,
        "last_node_id": last_node_id,
        "cells": cells,
    }


def _parse_cell_full_info(p: bytes) -> dict:
    """0x4232 - Individual Cell Full Info (52 bytes, one cell per packet)."""
    o = OFFSET_PAYLOAD
    node_id = p[o + 0]
    usn = p[o + 1]
    min_cv = struct.unpack_from("<H", p, o + 2)[0]
    max_cv = struct.unpack_from("<H", p, o + 4)[0]
    max_ct = _decode_temp(p[o + 6])
    bypass_t = _decode_temp(p[o + 7])
    bypass_a = struct.unpack_from("<H", p, o + 8)[0]
    err_counter = p[o + 10]
    reset_counter = p[o + 11]
    op_status = p[o + 12]
    is_overdue = bool(p[o + 13])
    fw_version = struct.unpack_from("<H", p, o + 25)[0]
    hw_version = struct.unpack_from("<H", p, o + 27)[0]
    serial_num = struct.unpack_from("<I", p, o + 31)[0]
    bypass_mah = struct.unpack_from("<f", p, o + 39)[0]

    return {
        "node_id": node_id,
        "usn": usn,
        "min_cell_voltage_mv": min_cv,
        "max_cell_voltage_mv": max_cv,
        "max_cell_temp_c": max_ct,
        "bypass_temp_c": bypass_t,
        "bypass_current_ma": bypass_a,
        "error_data_counter": err_counter,
        "reset_counter": reset_counter,
        "operating_status": op_status,
        "operating_status_text": CELL_NODE_STATUS.get(
            op_status, f"Unknown({op_status})"
        ),
        "is_overdue": is_overdue,
        "firmware_version": fw_version,
        "hardware_version": hw_version,
        "serial_number": serial_num,
        "bypass_session_mah": bypass_mah,
    }


def _parse_live_display(p: bytes) -> dict:
    """0x3233 - Live Display (57 bytes, 2 s). Compact system overview."""
    o = OFFSET_PAYLOAD
    op_status = p[o + 0]
    flags1 = p[o + 2]
    flags2 = p[o + 3]
    min_cv = struct.unpack_from("<h", p, o + 4)[0]
    max_cv = struct.unpack_from("<h", p, o + 6)[0]
    avg_cv = struct.unpack_from("<h", p, o + 8)[0]
    min_ct = _decode_temp(p[o + 10])
    max_ct = _decode_temp(p[o + 11])
    avg_ct = _decode_temp(p[o + 12])
    cells_in_bypass = p[o + 13]
    shunt_v_raw = struct.unpack_from("<h", p, o + 14)[0]
    shunt_i = struct.unpack_from("<f", p, o + 16)[0]
    shunt_pwr = struct.unpack_from("<f", p, o + 20)[0]
    shunt_soc_raw = struct.unpack_from("<h", p, o + 24)[0]
    cap_empty = struct.unpack_from("<f", p, o + 26)[0]
    cumul_kwh_chg = struct.unpack_from("<f", p, o + 30)[0]
    cumul_kwh_dischg = struct.unpack_from("<f", p, o + 34)[0]
    return {
        # System status
        "system_op_status": op_status,
        "system_op_status_text": SYSTEM_OP_STATUS.get(
            op_status, f"Unknown({op_status})"
        ),
        # Critical / thermal / charge / discharge flags — reuse binary sensor keys
        "critical_battery_ok": bool(flags1 & 0x01),
        "thermal_heat_on": bool(flags1 & 0x08),
        "thermal_cool_on": bool(flags1 & 0x10),
        "charging_is_on": bool(flags2 & 0x01),
        "discharging_is_on": bool(flags2 & 0x04),
        # Cell stats — reuse existing rapid/cell-stats keys
        "min_cell_voltage_mv": min_cv,
        "max_cell_voltage_mv": max_cv,
        "avg_cell_voltage_mv": avg_cv,
        "min_cell_temp_c": min_ct,
        "max_cell_temp_c": max_ct,
        "avg_cell_temp_c": avg_ct,
        "cells_in_bypass": cells_in_bypass,
        # Shunt — reuse existing shunt keys
        "shunt_voltage": shunt_v_raw * 10,
        "shunt_current_ma": shunt_i,
        "shunt_power_w": shunt_pwr,
        "shunt_state_of_charge_pct": shunt_soc_raw / 100.0,
        "shunt_capacity_to_empty_mah": cap_empty,
        # New: lifetime cumulative kWh (raw float / 1000)
        "shunt_cumul_charge_kwh": cumul_kwh_chg / 1000.0,
        "shunt_cumul_dischg_kwh": cumul_kwh_dischg / 1000.0,
    }


def _parse_cell_stats(p: bytes) -> dict:
    """0x3E33 - Status Cell Stats (48 bytes, 300 ms)."""
    o = OFFSET_PAYLOAD
    min_cv = struct.unpack_from("<h", p, o + 0)[0]
    max_cv = struct.unpack_from("<h", p, o + 2)[0]
    min_cv_id = p[o + 4]
    max_cv_id = p[o + 5]
    min_ct = _decode_temp(p[o + 6])
    max_ct = _decode_temp(p[o + 7])
    min_ba = struct.unpack_from("<h", p, o + 10)[0]
    max_ba = struct.unpack_from("<h", p, o + 12)[0]
    avg_cv = struct.unpack_from("<h", p, o + 20)[0]
    avg_ct = _decode_temp(p[o + 22])
    cells_above_init = p[o + 23]
    cells_above_final = p[o + 24]
    cells_in_bypass = p[o + 25]
    cells_overdue = p[o + 26]
    cells_active = p[o + 27]
    cells_in_system = p[o + 28]
    min_bp_session = struct.unpack_from("<f", p, o + 30)[0]
    max_bp_session = struct.unpack_from("<f", p, o + 34)[0]
    return {
        # Reuse existing rapid-message state_keys
        "min_cell_voltage_mv": min_cv,
        "max_cell_voltage_mv": max_cv,
        "avg_cell_voltage_mv": avg_cv,
        "min_cell_temp_c": min_ct,
        "max_cell_temp_c": max_ct,
        "avg_cell_temp_c": avg_ct,
        "min_bypass_current_ma": min_ba,
        "max_bypass_current_ma": max_ba,
        "cells_above_initial_bypass": cells_above_init,
        "cells_above_final_bypass": cells_above_final,
        "cells_in_bypass": cells_in_bypass,
        "cells_overdue": cells_overdue,
        "cells_active": cells_active,
        "cells_in_system": cells_in_system,
        # New: node IDs for min/max cell and bypass session energy
        "min_cell_voltage_node_id": min_cv_id,
        "max_cell_voltage_node_id": max_cv_id,
        "min_bypass_session_mah": min_bp_session,
        "max_bypass_session_mah": max_bp_session,
    }


def _parse_shunt_status(p: bytes) -> dict:
    """0x3F34 - Status Shunt (50 bytes, 300 ms)."""
    o = OFFSET_PAYLOAD
    supply_v_raw = struct.unpack_from("<h", p, o + 0)[0]
    ambient_t = _decode_temp(p[o + 2])
    shunt_t = _decode_temp(p[o + 3])
    shunt_v_raw = struct.unpack_from("<h", p, o + 4)[0]
    shunt_i = struct.unpack_from("<f", p, o + 6)[0]
    shunt_pwr = struct.unpack_from("<f", p, o + 10)[0]
    shunt_soc_raw = struct.unpack_from("<h", p, o + 14)[0]
    cap_full = struct.unpack_from("<f", p, o + 18)[0]
    cap_empty = struct.unpack_from("<f", p, o + 22)[0]
    dur_full = struct.unpack_from("<h", p, o + 26)[0]
    dur_empty = struct.unpack_from("<h", p, o + 28)[0]
    avg_chg = struct.unpack_from("<f", p, o + 30)[0]
    avg_dischg = struct.unpack_from("<f", p, o + 34)[0]
    return {
        # Reuse existing state_keys with correct unit conversions
        "system_supply_voltage_mv": supply_v_raw * 10,
        "system_ambient_temp_c": ambient_t,
        "shunt_temp_c": shunt_t,
        "shunt_voltage": shunt_v_raw * 10,
        "shunt_current_ma": shunt_i,
        "shunt_state_of_charge_pct": shunt_soc_raw / 100.0,
        "shunt_capacity_to_full_mah": cap_full,
        "shunt_capacity_to_empty_mah": cap_empty,
        "estimated_duration_to_full_min": dur_full,
        "estimated_duration_to_empty_min": dur_empty,
        # New: instantaneous power and average charge/discharge current
        "shunt_power_w": shunt_pwr,
        "shunt_accum_avg_charge_a": avg_chg / 1000.0,
        "shunt_accum_avg_dischg_a": avg_dischg / 1000.0,
    }


def _parse_daily_session_full(p: bytes) -> dict:
    """0x5432 - Daily Session Full (69 bytes, 20 s). Superset of 0x5457."""
    o = OFFSET_PAYLOAD
    min_cv = struct.unpack_from("<h", p, o + 0)[0]
    max_cv = struct.unpack_from("<h", p, o + 2)[0]
    min_soc = _decode_soc(p[o + 14])
    max_soc = _decode_soc(p[o + 15])
    peak_chg = struct.unpack_from("<h", p, o + 32)[0]
    peak_dischg = struct.unpack_from("<h", p, o + 34)[0]
    crit_events = p[o + 36]
    start_time = struct.unpack_from("<i", p, o + 37)[0]
    finish_time = struct.unpack_from("<i", p, o + 41)[0]
    cum_ah_chg = struct.unpack_from("<f", p, o + 45)[0]
    cum_ah_dischg = struct.unpack_from("<f", p, o + 49)[0]
    cum_kwh_chg = struct.unpack_from("<f", p, o + 53)[0]
    cum_kwh_dischg = struct.unpack_from("<f", p, o + 57)[0]
    return {
        # Reuse existing daily session state_keys
        "daily_min_cell_voltage_mv": min_cv,
        "daily_max_cell_voltage_mv": max_cv,
        "daily_min_soc_pct": min_soc,
        "daily_max_soc_pct": max_soc,
        "daily_peak_charge_a": peak_chg * 0.01,
        "daily_peak_discharge_a": peak_dischg * 0.01,
        "daily_critical_events": crit_events,
        "daily_start_time": start_time,
        "daily_finish_time": finish_time,
        "daily_cumulative_charge_mah": cum_ah_chg,
        "daily_cumulative_discharge_mah": cum_ah_dischg,
        # New: energy in kWh (raw float / 1000)
        "daily_cumulative_charge_kwh": cum_kwh_chg / 1000.0,
        "daily_cumulative_discharge_kwh": cum_kwh_dischg / 1000.0,
    }


def _parse_thermal_setup_full(p: bytes) -> dict:
    """0x5233 - Control Thermal Setup (40 bytes, 22 s)."""
    o = OFFSET_PAYLOAD
    heat_mode = p[o + 0]
    heat_monitor_cell = bool(p[o + 1])
    heat_monitor_ambient = bool(p[o + 2])
    heat_lo_cell = _decode_temp(p[o + 3])
    heat_lo_ambient = _decode_temp(p[o + 4])
    cool_mode = p[o + 13]
    cool_monitor_cell = bool(p[o + 14])
    cool_monitor_ambient = bool(p[o + 15])
    cool_monitor_bypass = bool(p[o + 16])
    cool_hi_cell = _decode_temp(p[o + 17])
    cool_hi_ambient = _decode_temp(p[o + 18])
    heat_lo_cell_cutout = _decode_temp(p[o + 28])
    heat_lo_ambient_cutout = _decode_temp(p[o + 29])
    cool_hi_cell_cutout = _decode_temp(p[o + 30])
    cool_hi_ambient_cutout = _decode_temp(p[o + 31])
    return {
        "thermal_heat_mode": heat_mode,
        "thermal_heat_lo_cell_temp_c": heat_lo_cell,
        "thermal_heat_lo_ambient_c": heat_lo_ambient,
        "thermal_heat_lo_cell_cutout_c": heat_lo_cell_cutout,
        "thermal_heat_lo_ambient_cutout_c": heat_lo_ambient_cutout,
        "thermal_heat_monitor_cell_temp": heat_monitor_cell,
        "thermal_heat_monitor_ambient": heat_monitor_ambient,
        "thermal_cool_mode": cool_mode,
        "thermal_cool_hi_cell_temp_c": cool_hi_cell,
        "thermal_cool_hi_ambient_c": cool_hi_ambient,
        "thermal_cool_hi_cell_cutout_c": cool_hi_cell_cutout,
        "thermal_cool_hi_ambient_cutout_c": cool_hi_ambient_cutout,
        "thermal_cool_monitor_cell_temp": cool_monitor_cell,
        "thermal_cool_monitor_ambient": cool_monitor_ambient,
        "thermal_cool_monitor_bypass": cool_monitor_bypass,
    }


def _parse_comms_status(p: bytes) -> dict:
    """0x6131 - Status Comms (33 bytes, 2 s)."""
    o = OFFSET_PAYLOAD
    op_status = p[o + 4]
    wifi_state = p[o + 10]
    canbus_status = p[o + 14]
    shunt_status = p[o + 19]
    cmu_status = p[o + 23]
    return {
        # Reuse existing state_keys
        "system_op_status": op_status,
        "system_op_status_text": SYSTEM_OP_STATUS.get(
            op_status, f"Unknown({op_status})"
        ),
        "shunt_status": shunt_status,
        # New: comms health fields
        "comms_wifi_state": wifi_state,
        "comms_canbus_op_status": canbus_status,
        "comms_cmu_op_status": cmu_status,
    }


def _parse_comms_status_full(p: bytes) -> dict:
    """0x6133 - Status Comms Full (94 bytes, 300 ms). Superset of 0x6131."""
    o = OFFSET_PAYLOAD
    op_status = p[o + 4]
    wifi_state = p[o + 9]
    wifi_rssi = p[o + 14]
    canbus_status = p[o + 15]
    shunt_status = p[o + 22]
    cmu_status = p[o + 51]
    group_min_cv = struct.unpack_from("<h", p, o + 56)[0]
    group_max_cv = struct.unpack_from("<h", p, o + 58)[0]
    group_min_ct = _decode_temp(p[o + 60])
    group_max_ct = _decode_temp(p[o + 61])
    return {
        # Reuse existing state_keys
        "system_op_status": op_status,
        "system_op_status_text": SYSTEM_OP_STATUS.get(
            op_status, f"Unknown({op_status})"
        ),
        "shunt_status": shunt_status,
        "comms_wifi_state": wifi_state,
        "comms_canbus_op_status": canbus_status,
        "comms_cmu_op_status": cmu_status,
        # Reuse cell min/max keys — group context cell stats
        "min_cell_voltage_mv": group_min_cv,
        "max_cell_voltage_mv": group_max_cv,
        "min_cell_temp_c": group_min_ct,
        "max_cell_temp_c": group_max_ct,
        # New: WiFi signal strength
        "comms_wifi_rssi": wifi_rssi,
    }


def _parse_status_control_logic(p: bytes) -> dict:
    """0x4733 - Status Control Logic (41 bytes, compact successor to 0x4732)."""
    o = OFFSET_PAYLOAD
    crit0 = p[o + 0]
    crit1 = p[o + 1]
    heat = p[o + 6]
    cool = p[o + 7]
    charge_rate_state = p[o + 8]
    charge0 = p[o + 10]
    dischg_rate_state = p[o + 16]
    dischg0 = p[o + 18]
    expansion_out = p[o + 24]
    ain1 = struct.unpack_from("<h", p, o + 28)[0]
    ain2 = struct.unpack_from("<h", p, o + 30)[0]
    ticks = p[o + 32]
    return {
        # Critical status — reuse existing binary-sensor state_keys
        "critical_battery_ok": bool(crit0 & 0x01),
        "critical_has_cells_overdue": bool(crit0 & 0x08),
        "critical_has_cells_low_voltage": bool(crit0 & 0x10),
        "critical_has_cells_high_voltage": bool(crit0 & 0x20),
        "critical_has_supply_volt_low": bool(crit1 & 0x01),
        "critical_has_supply_volt_high": bool(crit1 & 0x02),
        # Thermal — reuse existing binary-sensor state_keys
        "thermal_heat_on": bool(heat & 0x01),
        "thermal_cool_on": bool(cool & 0x01),
        # Charge — reuse existing binary-sensor state_keys
        "charging_is_on": bool(charge0 & 0x01),
        "ctrl_charge_power_rate_state": charge_rate_state,
        # Discharge — reuse existing binary-sensor state_keys
        "discharging_is_on": bool(dischg0 & 0x01),
        "ctrl_dischg_power_rate_state": dischg_rate_state,
        # Expansion relays (bits 4-7 of expansion output byte)
        "expansion_relay1": bool(expansion_out & 0x10),
        "expansion_relay2": bool(expansion_out & 0x20),
        "expansion_relay3": bool(expansion_out & 0x40),
        "expansion_relay4": bool(expansion_out & 0x80),
        # Expansion analog inputs and timing counter
        "ctrl_expansion_ain1": ain1,
        "ctrl_expansion_ain2": ain2,
        "ctrl_diff_logic_ticks": ticks,
    }


# ---------------------------------------------------------------------------
# Dispatch table and packet entry point
# ---------------------------------------------------------------------------

_DISPATCH: dict[int, Any] = {
    MSG_LIVE_DISPLAY: _parse_live_display,
    MSG_CELL_STATS: _parse_cell_stats,
    MSG_TELEMETRY_RAPID: _parse_rapid,
    MSG_SHUNT_STATUS: _parse_shunt_status,
    MSG_TELEMETRY_FAST: _parse_fast,
    MSG_LEGACY_FAST: _parse_fast,
    MSG_SYSTEM_DISCO: _parse_disco,
    MSG_LEGACY_DISCO: _parse_disco,
    MSG_LOGIC_CONTROL: _parse_logic_control,
    MSG_LEGACY_LOGIC: _parse_logic_control,
    MSG_STATUS_CONTROL_LOGIC: _parse_status_control_logic,
    MSG_REMOTE_STATUS: _parse_remote_status,
    MSG_LEGACY_REMOTE: _parse_remote_status,
    MSG_TELEMETRY_SLOW: _parse_slow,
    MSG_SYSTEM_SETUP: _parse_system_setup,
    MSG_HW_SYSTEM_SETUP_FULL: _parse_hw_system_setup_full,
    MSG_DAILY_SESSION: _parse_daily_session,
    MSG_DAILY_SESSION_FULL: _parse_daily_session_full,
    MSG_THERMAL_SETUP_FULL: _parse_thermal_setup_full,
    MSG_SHUNT_METRIC: _parse_shunt_metric,
    MSG_COMMS_STATUS: _parse_comms_status,
    MSG_COMMS_STATUS_FULL: _parse_comms_status_full,
    MSG_LIFE_METRIC: _parse_life_metric,
    MSG_CELL_FULL_INFO: _parse_cell_full_info,
    MSG_LEGACY_CELL_FULL: _parse_cell_full_info,
    MSG_CELL_BASIC_STATUS: _parse_cell_basic_status,
}


def parse_packet(payload: bytes) -> BatriumPacket | None:
    """Parse a raw Batrium UDP datagram. Returns None on error."""
    if len(payload) < OFFSET_PAYLOAD:
        return None
    if payload[0] != UDP_START_HEADER:
        _LOGGER.debug("Ignoring non-Batrium packet (bad header 0x%02X)", payload[0])
        return None

    msg_type = struct.unpack_from("<H", payload, OFFSET_MSG_TYPE)[0]
    system_id = struct.unpack_from("<H", payload, OFFSET_SYSTEM_ID)[0]
    hub_id = struct.unpack_from("<H", payload, 6)[0]

    pkt = BatriumPacket(raw_msg_type=msg_type, system_id=system_id, hub_id=hub_id)

    try:
        parser = _DISPATCH.get(msg_type)
        if parser is not None:
            pkt.data = parser(payload)
        else:
            _LOGGER.debug(
                "Unhandled Batrium message type: 0x%04X  payload(%d)=%s",
                msg_type,
                len(payload),
                payload.hex(),
            )
    except (struct.error, IndexError) as exc:
        _LOGGER.warning("Failed to parse Batrium msg 0x%04X: %s", msg_type, exc)
        return None

    return pkt
