# Batrium BMS – Home Assistant Custom Integration

Integrates a **Batrium WatchMon** battery management system into Home Assistant via the WiFi UDP broadcast protocol (v0.5).

## Features

- **Zero-configuration discovery** – the WatchMon broadcasts on UDP port 18542 automatically
- **Real-time sensors** updated at 147 ms – 22 s depending on the message type
- **Per-cell monitoring** with dynamic entity creation as cells report in
- **Binary sensors** for all boolean states (charging, cooling, critical alerts, relays…)
- Automatic **availability tracking** (marks unavailable after 60 s of silence)

## Installation

1. Copy the `custom_components/batrium/` folder into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration** and search for **Batrium BMS**.
4. Accept the default UDP port (18542) unless you changed it.

> **Tip:** Your HA instance must be on the same network segment as the WatchMon so it receives the UDP broadcasts.

## Entities

### Sensors

| Entity | Unit | Update rate |
|--------|------|-------------|
| State of Charge | % | 1.55 s |
| Min / Max / Avg Cell Voltage | mV | 147–294 ms |
| Min / Max / Avg Cell Temperature | °C | 147–294 ms |
| Shunt Current | mA | 294 ms |
| Shunt Temperature | °C | 1.55 s |
| Capacity to Full / Empty | mAh | 1.55 s |
| System Status | text | 1.55 s |
| System Supply Voltage | mV | 1.55 s |
| Ambient Temperature | °C | 1.55 s |
| Time to Full / Empty | min | 22 s |
| Recent Charge / Discharge | mAh | 22 s |
| Daily Charge / Discharge | mAh | 22 s |
| Daily Critical Events | count | 22 s |
| Cells in System / Active / Bypass / Overdue | count | 294 ms |
| Cell N (per-cell entity) | status | 147 ms |
| Firmware / System Code | text | 22 s |

### Binary Sensors

- Battery OK / Critical Battery OK
- Charging / Discharging
- Heating / Cooling (system + thermal control)
- Low / High Voltage Alert
- Cells Overdue Alert
- Expansion Relays 1–4
- Battery Contactor / Load Contactor

## Message Types Parsed

| Identifier | Name | Freq |
|------------|------|------|
| 0x415A | Individual Cells Basic Status | 147 ms |
| 0x4232 | Individual Cell Full Info | 147 ms |
| 0x3E5A | Telemetry Rapid Info | 294 ms |
| 0x3F33 | Telemetry Fast Info | 1.55 s |
| 0x5732 | System Discovery Info | 1.55 s |
| 0x4732 | Logic Control Status | 1.55 s |
| 0x4932 | Remote Status Info | 1.55 s |
| 0x405A | Telemetry Slow Info | 22 s |
| 0x4A33 | System Setup | 22 s |
| 0x5457 | Daily Session Info | 22 s |
| 0x7857 | Shunt Metric Info | 22 s |
| 0x5632 | Lifetime Metric Info | 22 s |
| Legacy types | Various | — |

## Troubleshooting

**No data / unavailable:** Check that HA is on the same broadcast domain as the WatchMon. Confirm the WatchMon WiFi Broadcast Mode is set to **Verbose** (not Idle or Disabled) in its settings.

**Wrong port:** If you changed the WatchMon UDP port, update it in the integration options.

**Firewall:** Ensure UDP port 18542 is not blocked on the HA host.

## Protocol Reference

Batrium WatchMon WiFi UDP Protocol v0.5  
https://wiki.batrium.com/canbus/watchmon-wifi-udp-protocol-v0.5.pdf

## Acknowledgements

This integration was built using the [integration_blueprint](https://github.com/ludeeus/integration_blueprint) template by [@ludeeus](https://github.com/ludeeus) as a structural reference.
