# Liberty Twin - Quick Reference

## System Overview

**Liberty Twin** monitors 32 library seats using a gimbal-mounted sensor array. The system detects ghost occupancy (bags reserving seats) and provides real-time visualization.

## Architecture

```
Unity Simulation -> MQTT Broker -> Edge Processor -> Dashboard
                         |                |
                         v                v
                    InfluxDB (history)   Alerts
```

## Key Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Simulation | Unity 3D | Generate sensor data |
| Broker | Mosquitto | Message routing |
| Edge | Python | State machine, ghost detection |
| Dashboard | WebGL/HTML | Real-time visualization |
| Database | InfluxDB | Historical data |

## Seat Layout

32 seats in 8 zones:
- Section A (Left): Zones 1-4
- Section B (Right): Zones 5-8
- Each zone: 4 seats

Gimbal sweeps 8 positions, 24-second cycle.

## States

| State | Color | Description |
|-------|-------|-------------|
| Empty | Green | No occupant |
| Occupied | Red | Person actively using |
| SuspectedGhost | Yellow | Object present, no motion (2min grace) |
| Ghost | Purple | Confirmed abandoned seat (5min threshold) |

## MQTT Topics

**Telemetry:**
- `liberty_twin/telemetry/zone/{Z1-Z8}` - Sensor data

**State:**
- `liberty_twin/state/zone/{Z1-Z8}` - Zone state
- `liberty_twin/state/seat/{S1-S32}` - Individual seat (retained)

**Alerts:**
- `liberty_twin/alerts/ghost_detected`
- `liberty_twin/alerts/ghost_suspected`
- `liberty_twin/alerts/person_returned`

**Commands:**
- `liberty_twin/commands/calibrate`
- `liberty_twin/commands/config_update`

## Configuration

**Detection Thresholds:**
- Presence: 0.6
- Motion: 0.15
- Grace period: 120 seconds
- Ghost threshold: 300 seconds

**Sweep Timing:**
- Dwell time: 2 seconds per zone
- Transition: 1 second between zones
- Total cycle: 24 seconds

## Services and Operations

**Infrastructure**: The Mosquitto MQTT broker and InfluxDB time-series database run as Docker Compose services. The edge processor is a standalone Python application. Unity runs in the editor during development.

**Monitoring**: Mosquitto and InfluxDB logs are accessible through Docker. MQTT traffic can be inspected using tools like MQTT Explorer by subscribing to the state topics.

## Ports

| Service | Port | Protocol |
|---------|------|----------|
| MQTT | 1883 | TCP |
| WebSocket | 9001 | WS |
| InfluxDB | 8086 | HTTP |
| Dashboard | 8080 | HTTP |

## File Structure

```
liberty_twin/
├── docker/           # Docker compose files
├── unity/            # Unity project
├── edge_processor/   # Python application
├── dashboard/        # Web dashboard
└── docs/            # Documentation
```

## Troubleshooting

**Unity not connecting:**
- Check broker address: localhost:1883
- Verify Mosquitto is running
- Check firewall

**No state updates:**
- Verify edge processor subscribed to telemetry
- Check MQTT credentials
- View Mosquitto logs

**Dashboard not updating:**
- Check WebSocket connection in browser
- Verify state topics have retain flag
- Check JavaScript console for errors

## Support

- Documentation: `/docs`
- Issues: GitHub issues

## License

MIT License - Liberty Twin Team 2025
