"""Pytest configuration for Batrium tests."""

import pytest


@pytest.fixture
def rapid_packet_hex():
    """
    Raw hex for a minimal valid 0x3E5A Rapid Info packet.
    Build a real fixture by capturing from your WatchMon:

        import socket, binascii
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", 18542))
        data, addr = s.recvfrom(4096)
        print(binascii.hexlify(data).decode())

    Then replace the placeholder below with the real capture.
    """
    # Header:  0x3A, msg_type=0x3E5A (LE), 0x2C, system_id=0x0001 (LE), hub_id=0x0000 (LE)
    # Payload: 48 bytes of zeros (all readings = 0 / -40°C temps)
    header = "3a5a3e2c01000000"
    payload = "00" * 48
    return header + payload
