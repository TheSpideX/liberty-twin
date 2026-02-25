# Liberty Twin - MQTT Protocol Specification

## Table of Contents
1. [Protocol Overview](#protocol-overview)
2. [Topic Structure](#topic-structure)
3. [Message Schemas](#message-schemas)
4. [QoS and Retain Policies](#qos-and-retain-policies)
5. [Connection Details](#connection-details)
6. [Error Handling](#error-handling)
7. [Security](#security)
8. [Example Scenarios](#example-scenarios)

---

## Protocol Overview

Liberty Twin uses **MQTT 3.1.1** for all inter-service communication. MQTT was chosen for:
- **Lightweight**: Minimal overhead, suitable for IoT
- **Pub/Sub**: Decoupled architecture
- **QoS Levels**: Configurable delivery guarantees
- **Retain**: Last-known-state capability
- **WebSocket**: Browser support for dashboard

### Protocol Version
- **MQTT**: 3.1.1
- **WebSocket**: MQTT over WebSocket (port 9001)
- **TLS**: Optional, recommended for production

### Port Configuration
| Service | Port | Protocol | Usage |
|---------|------|----------|-------|
| MQTT | 1883 | TCP | Unity <-> Edge <-> Cloud |
| WebSocket | 9001 | WS/WSS | Dashboard |

---

## Topic Structure

All topics follow the pattern: `liberty_twin/{category}/{subcategory}/{resource}`

### Complete Topic Hierarchy

```
liberty_twin/
│
├── telemetry/
│   └── zone/
│       ├── Z1          # Zone 1 sensor data
│       ├── Z2          # Zone 2 sensor data
│       ├── Z3          # Zone 3 sensor data
│       ├── Z4          # Zone 4 sensor data
│       ├── Z5          # Zone 5 sensor data
│       ├── Z6          # Zone 6 sensor data
│       ├── Z7          # Zone 7 sensor data
│       └── Z8          # Zone 8 sensor data
│
├── state/
│   ├── zone/
│   │   ├── Z1          # Aggregated zone state
│   │   ├── Z2
│   │   ├── Z3
│   │   ├── Z4
│   │   ├── Z5
│   │   ├── Z6
│   │   ├── Z7
│   │   └── Z8
│   └── seat/
│       ├── S1          # Individual seat state (retained)
│       ├── S2
│       ├── ...
│       └── S32
│
├── alerts/
│   ├── ghost_detected     # Ghost confirmed
│   ├── ghost_suspected    # Entered grace period
│   ├── person_returned    # Returned to ghost seat
│   ├── state_change       # Any state transition
│   └── system_warning     # System issues
│
├── commands/
│   ├── calibrate          # Start auto-calibration
│   ├── sweep_control      # Pause/resume gimbal
│   ├── config_update      # Update thresholds
│   └── reboot             # Restart edge processor
│
├── health/
│   ├── unity/
│   │   └── status         # Unity heartbeat
│   ├── edge/
│   │   └── status         # Edge processor heartbeat
│   └── broker/
│       └── status         # MQTT broker status
│
├── forecast/
│   └── zone/
│       ├── Z1             # 20-min prediction
│       ├── Z2
│       └── ...
│
└── system/
    ├── metrics            # Performance metrics
    └── logs               # Error logs
```

---

## Message Schemas

### 1. Telemetry (Unity to Edge)

**Topic**: `liberty_twin/telemetry/zone/{Z1-Z8}`

**Description**: Raw sensor data from Unity simulation

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["timestamp", "zone_id", "sweep_cycle", "gimbal_position", "seats"],
  "properties": {
    "timestamp": {
      "type": "integer",
      "description": "Unix timestamp (seconds)"
    },
    "zone_id": {
      "type": "string",
      "enum": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
    },
    "sweep_cycle": {
      "type": "integer",
      "description": "Sweep iteration number"
    },
    "gimbal_position": {
      "type": "object",
      "required": ["pan_angle", "tilt_angle"],
      "properties": {
        "pan_angle": {
          "type": "number",
          "minimum": 0,
          "maximum": 360
        },
        "tilt_angle": {
          "type": "number",
          "minimum": -30,
          "maximum": 30
        }
      }
    },
    "seats": {
      "type": "object",
      "patternProperties": {
        "^S(1|[1-9][0-9]|3[0-2])$": {
          "type": "object",
          "required": ["seat_id", "presence_score", "motion_score", "object_type"],
          "properties": {
            "seat_id": {
              "type": "string",
              "pattern": "^S(1|[1-9][0-9]|3[0-2])$"
            },
            "presence_score": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "motion_score": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "object_type": {
              "type": "string",
              "enum": ["person", "bag", "book", "empty"]
            },
            "object_confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "distance_m": {
              "type": "number",
              "minimum": 0
            },
            "radar_velocity": {
              "type": "number"
            }
          }
        }
      }
    }
  }
}
```

**Example**:
```json
{
  "timestamp": 1707153600,
  "zone_id": "Z1",
  "sweep_cycle": 45,
  "gimbal_position": {
    "pan_angle": 0.0,
    "tilt_angle": 0.0
  },
  "seats": {
    "S1": {
      "seat_id": "S1",
      "presence_score": 0.85,
      "motion_score": 0.78,
      "object_type": "person",
      "object_confidence": 0.92,
      "distance_m": 1.2,
      "radar_velocity": 0.05
    },
    "S2": {
      "seat_id": "S2",
      "presence_score": 0.82,
      "motion_score": 0.02,
      "object_type": "bag",
      "object_confidence": 0.88,
      "distance_m": 1.3,
      "radar_velocity": 0.0
    },
    "S5": {
      "seat_id": "S5",
      "presence_score": 0.05,
      "motion_score": 0.01,
      "object_type": "empty",
      "object_confidence": 0.95,
      "distance_m": 0.0,
      "radar_velocity": 0.0
    },
    "S6": {
      "seat_id": "S6",
      "presence_score": 0.91,
      "motion_score": 0.65,
      "object_type": "person",
      "object_confidence": 0.94,
      "distance_m": 1.1,
      "radar_velocity": 0.08
    }
  }
}
```

---

### 2. Zone State (Edge to Cloud)

**Topic**: `liberty_twin/state/zone/{Z1-Z8}`

**Description**: Computed state for all seats in a zone

**Schema**:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["timestamp", "zone_id", "sweep_cycle", "seats"],
  "properties": {
    "timestamp": {
      "type": "integer"
    },
    "zone_id": {
      "type": "string",
      "enum": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8"]
    },
    "sweep_cycle": {
      "type": "integer"
    },
    "seats": {
      "type": "object",
      "patternProperties": {
        "^S(1|[1-9][0-9]|3[0-2])$": {
          "type": "object",
          "required": ["seat_id", "state", "confidence", "last_updated"],
          "properties": {
            "seat_id": {
              "type": "string"
            },
            "state": {
              "type": "string",
              "enum": ["empty", "occupied", "suspected_ghost", "ghost"]
            },
            "confidence": {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            "last_updated": {
              "type": "integer"
            },
            "ghost_timer_s": {
              "type": ["integer", "null"]
            },
            "occupant_type": {
              "type": ["string", "null"],
              "enum": ["person", "bag", "book", null]
            },
            "time_in_state": {
              "type": "integer"
            }
          }
        }
      }
    }
  }
}
```

**Example**:
```json
{
  "timestamp": 1707153600,
  "zone_id": "Z1",
  "sweep_cycle": 45,
  "seats": {
    "S1": {
      "seat_id": "S1",
      "state": "occupied",
      "confidence": 0.89,
      "last_updated": 1707153600,
      "ghost_timer_s": null,
      "occupant_type": "person",
      "time_in_state": 120
    },
    "S2": {
      "seat_id": "S2",
      "state": "suspected_ghost",
      "confidence": 0.85,
      "last_updated": 1707153580,
      "ghost_timer_s": 120,
      "occupant_type": "bag",
      "time_in_state": 180
    },
    "S5": {
      "seat_id": "S5",
      "state": "empty",
      "confidence": 0.95,
      "last_updated": 1707153600,
      "ghost_timer_s": null,
      "occupant_type": null,
      "time_in_state": 0
    },
    "S6": {
      "seat_id": "S6",
      "state": "occupied",
      "confidence": 0.91,
      "last_updated": 1707153600,
      "ghost_timer_s": null,
      "occupant_type": "person",
      "time_in_state": 300
    }
  }
}
```

---

### 3. Seat State - Retained (Edge to Cloud)

**Topic**: `liberty_twin/state/seat/{S1-S32}`

**Description**: Individual seat state with RETAIN flag

**Purpose**: Dashboard gets immediate state on connection

**Schema**: Same as individual seat object in Zone State

**Example**:
```json
{
  "timestamp": 1707153600,
  "seat_id": "S2",
  "state": "suspected_ghost",
  "confidence": 0.85,
  "zone_id": "Z1",
  "ghost_timer_s": 120,
  "occupant_type": "bag",
  "time_in_state": 180
}
```

---

### 4. Alerts (Edge to Cloud)

#### 4.1 Ghost Detected

**Topic**: `liberty_twin/alerts/ghost_detected`

**Description**: Ghost state confirmed after threshold

**Schema**:
```json
{
  "type": "object",
  "required": ["timestamp", "alert_type", "zone_id", "seat_id", "ghost_duration_s", "confidence"],
  "properties": {
    "timestamp": {"type": "integer"},
    "alert_type": {"type": "string", "const": "ghost_detected"},
    "zone_id": {"type": "string"},
    "seat_id": {"type": "string"},
    "ghost_duration_s": {"type": "integer"},
    "confidence": {"type": "number"},
    "previous_state_duration_s": {"type": "integer"}
  }
}
```

**Example**:
```json
{
  "timestamp": 1707153900,
  "alert_type": "ghost_detected",
  "zone_id": "Z1",
  "seat_id": "S2",
  "ghost_duration_s": 300,
  "confidence": 0.85,
  "previous_state_duration_s": 180
}
```

#### 4.2 Ghost Suspected

**Topic**: `liberty_twin/alerts/ghost_suspected`

**Description**: Entered grace period

**Example**:
```json
{
  "timestamp": 1707153720,
  "alert_type": "ghost_suspected",
  "zone_id": "Z1",
  "seat_id": "S2",
  "grace_period_s": 120,
  "confidence": 0.82
}
```

#### 4.3 Person Returned

**Topic**: `liberty_twin/alerts/person_returned`

**Description**: Person returned to ghost seat

**Example**:
```json
{
  "timestamp": 1707154200,
  "alert_type": "person_returned",
  "zone_id": "Z1",
  "seat_id": "S2",
  "ghost_duration_s": 600,
  "confidence": 0.91
}
```

#### 4.4 State Change

**Topic**: `liberty_twin/alerts/state_change`

**Description**: Generic state transition

**Example**:
```json
{
  "timestamp": 1707153600,
  "alert_type": "state_change",
  "zone_id": "Z1",
  "seat_id": "S1",
  "from_state": "empty",
  "to_state": "occupied",
  "reason": "presence_detected",
  "confidence": 0.89
}
```

---

### 5. Commands (Dashboard to Edge)

#### 5.1 Calibrate

**Topic**: `liberty_twin/commands/calibrate`

**Description**: Start auto-calibration routine

**Payload**: Empty or configuration

**Response Topic**: `liberty_twin/commands/calibrate/response`

**Example Request**:
```json
{
  "timestamp": 1707153600,
  "command_id": "cmd_001",
  "full_sweep": true
}
```

**Example Response**:
```json
{
  "timestamp": 1707153600,
  "command_id": "cmd_001",
  "status": "started",
  "eta_seconds": 30,
  "message": "Auto-calibration in progress"
}
```

#### 5.2 Sweep Control

**Topic**: `liberty_twin/commands/sweep_control`

**Description**: Pause or resume gimbal sweep

**Example**:
```json
{
  "timestamp": 1707153600,
  "command": "pause"
}
```

Valid commands: `pause`, `resume`, `speed_up`, `speed_down`

#### 5.3 Config Update

**Topic**: `liberty_twin/commands/config_update`

**Description**: Update detection thresholds

**Example**:
```json
{
  "timestamp": 1707153600,
  "config": {
    "presence_threshold": 0.55,
    "motion_threshold": 0.12,
    "grace_period_s": 90,
    "ghost_threshold_s": 240
  }
}
```

---

### 6. Health Status

**Topic**: `liberty_twin/health/{unity,edge,broker}/status`

**Description**: Heartbeat messages

**Example (Unity)**:
```json
{
  "timestamp": 1707153600,
  "component": "unity_sim",
  "status": "online",
  "sweep_cycle": 45,
  "fps": 60,
  "memory_mb": 512
}
```

**Example (Edge)**:
```json
{
  "timestamp": 1707153600,
  "component": "edge_processor",
  "status": "online",
  "cpu_percent": 35,
  "memory_mb": 128,
  "active_state_machines": 32,
  "messages_processed": 450
}
```

---

### 7. Forecast

**Topic**: `liberty_twin/forecast/zone/{Z1-Z8}`

**Description**: 20-minute occupancy prediction

**Schema**:
```json
{
  "type": "object",
  "required": ["timestamp", "zone_id", "forecast_time", "predictions"],
  "properties": {
    "timestamp": {"type": "integer"},
    "zone_id": {"type": "string"},
    "forecast_time": {"type": "integer"},
    "predictions": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "minutes_ahead": {"type": "integer"},
          "occupancy_probability": {"type": "number"},
          "confidence": {"type": "number"}
        }
      }
    }
  }
}
```

**Example**:
```json
{
  "timestamp": 1707153600,
  "zone_id": "Z1",
  "forecast_time": 1707154800,
  "predictions": [
    {"minutes_ahead": 5, "occupancy_probability": 0.75, "confidence": 0.82},
    {"minutes_ahead": 10, "occupancy_probability": 0.80, "confidence": 0.78},
    {"minutes_ahead": 15, "occupancy_probability": 0.85, "confidence": 0.72},
    {"minutes_ahead": 20, "occupancy_probability": 0.90, "confidence": 0.65}
  ]
}
```

---

## QoS and Retain Policies

### Quality of Service (QoS)

| Topic Pattern | QoS | Reason |
|--------------|-----|--------|
| `liberty_twin/telemetry/*` | 0 | High frequency, latest is sufficient |
| `liberty_twin/state/zone/*` | 1 | Important, at-least-once delivery |
| `liberty_twin/state/seat/*` | 1 | Retained, must be delivered |
| `liberty_twin/alerts/*` | 1 | Events should not be lost |
| `liberty_twin/commands/*` | 1 | Commands must be received |
| `liberty_twin/health/*` | 0 | Periodic, latest is sufficient |
| `liberty_twin/forecast/*` | 1 | Retained for dashboard |

### Retain Flag

| Topic Pattern | Retain | Reason |
|--------------|--------|--------|
| `liberty_twin/state/zone/*` | **YES** | Dashboard shows last known state on connect |
| `liberty_twin/state/seat/*` | **YES** | Individual seat state persisted |
| `liberty_twin/forecast/*` | **YES** | Latest prediction available |
| `liberty_twin/alerts/*` | NO | Events are transient |
| `liberty_twin/telemetry/*` | NO | Continuous stream |
| `liberty_twin/commands/*` | NO | Commands are processed once |
| `liberty_twin/health/*` | NO | Heartbeats are periodic |

---

## Connection Details

### Unity Simulation (Publisher)

The Unity simulation connects to the MQTT broker on port 1883 using a client ID of "unity_sim_client". It publishes telemetry messages to the zone-specific telemetry topic using QoS 0 (fire-and-forget) with the retain flag set to false, since telemetry is a continuous stream where only the latest reading matters.

### Edge Processor (Pub/Sub)

The edge processor connects with the client ID "edge_processor" and subscribes to all zone telemetry topics (using the + wildcard) and command topics, both with QoS 1 to ensure at-least-once delivery. When publishing state updates, it uses QoS 1 with the retain flag set to true so that newly connecting clients immediately receive the latest state.

### Dashboard (WebSocket Subscriber)

The dashboard connects to the broker via WebSocket (on port 9001) and subscribes to all zone state topics and alert topics with QoS 1. When messages arrive, it parses the JSON payload and updates the visual display accordingly.

---

## Error Handling

### MQTT Connection Errors

The system implements automatic reconnection with exponential backoff. When an unexpected disconnection occurs, the client logs the error and retries with a delay ranging from 1 to 30 seconds, progressively increasing with each failed attempt.

### Message Validation

All incoming telemetry is validated against the defined JSON schema before processing. If a message fails validation, the error is logged and the invalid message details are published to a dedicated error topic for monitoring and debugging.

### Dead Letter Queue

Failed messages are published to:
- `liberty_twin/system/errors` for processing errors
- `liberty_twin/system/invalid` for schema violations

---

## Security

### Authentication

Three user accounts control access: the Unity simulation publisher, the edge processor (which both publishes and subscribes), and the dashboard (which primarily subscribes and can send commands). Each has its own username and password credentials.

### Access Control

Access control lists enforce topic-level permissions:
- **Unity** can only write to telemetry and its own health topic
- **Edge Processor** can write to state, alerts, and its health topic, and read from telemetry and commands
- **Dashboard** can read all topics and write to the commands topic

### TLS/SSL (Production)

For production deployments, TLS encryption is enabled on all MQTT connections using certificate-based authentication. Each client is configured with a CA certificate, client certificate, and private key, using TLS 1.2 as the minimum protocol version.

---

## Example Scenarios

### Scenario 1: Student Creates Ghost

```
T+0s    Unity publishes telemetry/Z1
        S2: {presence: 0.82, motion: 0.75, object: "person"}

        Edge processes → S2: Occupied
        Publish state/seat/S2 (retain)

T+60s   Unity publishes telemetry/Z1
        S2: {presence: 0.82, motion: 0.02, object: "bag"}
        (Student left, bag remains)

        Edge processes → S2: SuspectedGhost
        Start grace timer (2 min)
        Publish state/seat/S2 (retain)
        Publish alerts/ghost_suspected

T+180s  Grace period expired
        Edge → S2: Ghost
        Publish state/seat/S2 (retain)
        Publish alerts/ghost_detected

T+600s  Student returns
        Unity publishes telemetry/Z1
        S2: {presence: 0.85, motion: 0.80, object: "person"}

        Edge → S2: Occupied
        Publish state/seat/S2 (retain)
        Publish alerts/person_returned
```

### Scenario 2: Dashboard Connection

```
Dashboard connects via WebSocket
↓
Automatically receives retained messages:
  • state/seat/S1 (Occupied)
  • state/seat/S2 (Ghost)
  • state/seat/S3 (Empty)
  • ... all 32 seats
  • state/zone/Z1 (aggregated)
  • ... all 8 zones
  • forecast/zone/Z1 (latest prediction)
  • ... all 8 zones
↓
Dashboard shows current state immediately
↓
Subscribes to non-retained topics:
  • alerts/+
  • health/+
↓
Receives real-time updates as they happen
```

### Scenario 3: Configuration Update

```
Dashboard publishes:
  topic: liberty_twin/commands/config_update
  payload: {
    "presence_threshold": 0.55,
    "grace_period_s": 90
  }
  qos: 1
  retain: false

Edge receives and validates
↓
Edge applies new configuration
↓
Edge publishes response:
  topic: liberty_twin/commands/config_update/response
  payload: {
    "status": "success",
    "applied_config": {...}
  }
```

---

## Summary

This MQTT protocol specification ensures:
- **Reliable message delivery** with appropriate QoS levels
- **Real-time updates** with WebSocket support for dashboard
- **State persistence** with retained messages
- **Security** with authentication and ACLs
- **Extensibility** with clear topic hierarchies

Total message types: **7 categories, 50+ topics**
Expected message rate: **~40 msg/min** (telemetry + state)
Peak rate: **~100 msg/min** (during ghost transitions)
