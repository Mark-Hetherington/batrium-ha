"""Unit tests for the Batrium coordinator."""

import asyncio
import struct
from unittest.mock import MagicMock

import pytest

from custom_components.batrium.const import MSG_TELEMETRY_RAPID, UDP_START_HEADER
from custom_components.batrium.coordinator import BatriumCoordinator


def make_rapid_packet(min_v=3200, max_v=3450, cells_active=16) -> bytes:
    buf = bytearray(8 + 48)
    buf[0] = UDP_START_HEADER
    struct.pack_into("<H", buf, 1, MSG_TELEMETRY_RAPID)
    buf[3] = 0x2C
    struct.pack_into("<H", buf, 4, 1)  # system_id
    struct.pack_into("<H", buf, 6, 0)  # hub_id
    struct.pack_into("<H", buf, 8, min_v)
    struct.pack_into("<H", buf, 10, max_v)
    buf[8 + 27] = cells_active
    buf[8 + 28] = cells_active
    return bytes(buf)


@pytest.fixture
def mock_hass():
    hass = MagicMock()
    hass.loop = asyncio.get_event_loop()
    return hass


def test_coordinator_starts_unavailable(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    assert coordinator.available is False


def test_coordinator_becomes_available_on_packet(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    coordinator.handle_datagram(make_rapid_packet(), ("192.168.1.100", 18542))
    assert coordinator.available is True


def test_coordinator_merges_state(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    coordinator.handle_datagram(
        make_rapid_packet(min_v=3100, max_v=3500), ("192.168.1.100", 18542)
    )
    assert coordinator.state["min_cell_voltage_mv"] == 3100
    assert coordinator.state["max_cell_voltage_mv"] == 3500


def test_coordinator_ignores_bad_packet(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    coordinator.handle_datagram(b"\x00\x00\x00\x00", ("192.168.1.100", 18542))
    assert coordinator.available is False
    assert coordinator.state == {}


def test_coordinator_marks_unavailable_on_timeout(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    coordinator.handle_datagram(make_rapid_packet(), ("192.168.1.100", 18542))
    assert coordinator.available is True

    # Simulate timeout firing
    coordinator._mark_unavailable()
    assert coordinator.available is False


def test_coordinator_recovers_after_timeout(mock_hass):
    coordinator = BatriumCoordinator(mock_hass)
    coordinator._mark_unavailable()
    assert coordinator.available is False

    coordinator.handle_datagram(make_rapid_packet(), ("192.168.1.100", 18542))
    assert coordinator.available is True
