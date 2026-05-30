"""
Batrium UDP coordinator.

Listens on the broadcast UDP port and dispatches parsed packets
to all registered listeners (sensor platforms).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import socket
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.dispatcher import async_dispatcher_send

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import (
    BATRIUM_UDP_PORT,
    DOMAIN,
    MSG_CELL_BASIC_STATUS,
    MSG_CELL_FULL_INFO,
    MSG_LEGACY_CELL_FULL,
    MSG_LEGACY_DISCO,
    MSG_SYSTEM_DISCO,
    MSG_SYSTEM_SETUP,
)
from .parser import BatriumPacket, parse_packet

_LOGGER = logging.getLogger(__name__)

SIGNAL_BATRIUM_UPDATE = f"{DOMAIN}_update"
SIGNAL_BATRIUM_CELL_UPDATE = f"{DOMAIN}_cell_update"

# How long (seconds) to wait before marking the device unavailable
TIMEOUT_SECONDS = 60


class BatriumUDPListener(asyncio.DatagramProtocol):
    """asyncio DatagramProtocol that receives Batrium broadcasts."""

    def __init__(self, coordinator: BatriumCoordinator) -> None:
        """Initialize with the owning coordinator."""
        self._coordinator = coordinator

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        """Forward a received datagram to the coordinator."""
        self._coordinator.handle_datagram(data, addr)

    def error_received(self, exc: Exception) -> None:
        """Log a transport-layer error."""
        _LOGGER.warning("Batrium UDP error: %s", exc)

    def connection_lost(self, exc: Exception | None) -> None:
        """Log when the UDP transport is closed."""
        _LOGGER.info("Batrium UDP connection lost: %s", exc)


class BatriumCoordinator:
    """Manages the UDP socket and holds the latest state."""

    def __init__(self, hass: HomeAssistant, port: int = BATRIUM_UDP_PORT) -> None:
        """Initialize coordinator with the HA instance and UDP port to bind."""
        self.hass = hass
        self.port = port
        self._transport: asyncio.BaseTransport | None = None
        self._available = False
        self._timeout_handle = None

        # Merged state from all message types
        self.state: dict[str, Any] = {}
        # Per-node cell data: {node_id: dict}
        self.cells: dict[int, dict] = {}
        # Device identification (from system setup / disco msgs)
        self.device_info: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def async_start(self) -> None:
        """Open the UDP socket."""
        loop = asyncio.get_event_loop()
        try:
            # Create a socket that can receive broadcast packets
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            with contextlib.suppress(AttributeError):
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.bind(("", self.port))
            sock.settimeout(0.0)

            transport, _ = await loop.create_datagram_endpoint(
                lambda: BatriumUDPListener(self),
                sock=sock,
            )
            self._transport = transport
            _LOGGER.info("Batrium UDP listener started on port %d", self.port)
        except OSError:
            _LOGGER.exception("Failed to open Batrium UDP socket on port %d", self.port)
            raise

    async def async_stop(self) -> None:
        """Close the UDP socket."""
        if self._timeout_handle:
            self._timeout_handle.cancel()
        if self._transport:
            self._transport.close()
            self._transport = None
        _LOGGER.info("Batrium UDP listener stopped")

    # ------------------------------------------------------------------
    # Packet handling
    # ------------------------------------------------------------------

    def handle_datagram(self, data: bytes, _addr: tuple[str, int]) -> None:
        """Parse and process an incoming UDP datagram."""
        packet = parse_packet(data)
        if packet is None:
            return

        self._reset_timeout()
        self._update_state(packet)

    def _update_state(self, packet: BatriumPacket) -> None:
        """Merge parsed packet data into coordinator state and dispatch signals."""
        msg_type = packet.raw_msg_type

        if msg_type in (
            MSG_CELL_BASIC_STATUS,
            MSG_CELL_FULL_INFO,
            MSG_LEGACY_CELL_FULL,
        ):
            # Cell-level updates
            self._update_cell_state(packet)
            self.hass.loop.call_soon_threadsafe(
                async_dispatcher_send, self.hass, SIGNAL_BATRIUM_CELL_UPDATE
            )
        else:
            # System-level updates
            self.state.update(packet.data)

            # Extract device identification from preferred messages
            if msg_type in (MSG_SYSTEM_SETUP, MSG_SYSTEM_DISCO, MSG_LEGACY_DISCO):
                for key in (
                    "system_code",
                    "firmware_version",
                    "hardware_version",
                    "serial_number",
                    "system_name",
                ):
                    if key in packet.data:
                        self.device_info[key] = packet.data[key]

            if not self._available:
                self._available = True
                _LOGGER.info("Batrium system online (system_id=%d)", packet.system_id)

            self.hass.loop.call_soon_threadsafe(
                async_dispatcher_send, self.hass, SIGNAL_BATRIUM_UPDATE
            )

    def _update_cell_state(self, packet: BatriumPacket) -> None:
        """Update per-cell state."""
        data = packet.data
        if "cells" in data:
            # Bulk update from basic status
            for cell in data["cells"]:
                node_id = cell["node_id"]
                self.cells[node_id] = {**self.cells.get(node_id, {}), **cell}
        elif "node_id" in data:
            # Single cell full-info update
            node_id = data["node_id"]
            self.cells[node_id] = {**self.cells.get(node_id, {}), **data}

    # ------------------------------------------------------------------
    # Availability / timeout
    # ------------------------------------------------------------------

    def _reset_timeout(self) -> None:
        if self._timeout_handle:
            self._timeout_handle.cancel()
        self._timeout_handle = self.hass.loop.call_later(
            TIMEOUT_SECONDS, self._mark_unavailable
        )

    def _mark_unavailable(self) -> None:
        if self._available:
            _LOGGER.warning("Batrium system timed out - marking unavailable")
            self._available = False
            async_dispatcher_send(self.hass, SIGNAL_BATRIUM_UPDATE)

    @property
    def available(self) -> bool:
        """Return True when packets have been received within the timeout window."""
        return self._available
