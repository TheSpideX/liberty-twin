# Liberty Twin - Complete Technical Documentation

## Executive Summary

**Liberty Twin** is a privacy-preserving IoT system that monitors library occupancy using a gimbal-mounted multi-modal sensor array. The system detects "ghost occupancy" (bags reserving seats), provides real-time zone state updates, and visualizes the data through a live digital twin dashboard.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Architecture](#2-architecture)
3. [Physical Layout](#3-physical-layout)
4. [Hardware Components](#4-hardware-components)
5. [Software Stack](#5-software-stack)
6. [Data Models](#6-data-models)
7. [State Machine](#7-state-machine)
8. [MQTT Protocol](#8-mqtt-protocol)
9. [Implementation Guide](#9-implementation-guide)
10. [API Reference](#10-api-reference)
11. [Dashboard Specification](#11-dashboard-specification)
12. [Setup & Deployment](#12-setup--deployment)

---

## 1. System Overview

### 1.1 Purpose
Monitor 32 library seats across 8 zones to:
- Detect real-time occupancy
- Identify ghost occupancy (bags left behind)
- Provide predictive occupancy forecasting
- Visualize live status via digital twin

### 1.2 Key Features
- **32-seat monitoring** with per-seat granularity
- **Ghost detection** using temporal + motion analysis
- **Privacy-first** edge computing (no video leaves device)
- **Digital twin** with Unity WebGL visualization
- **Multi-modal fusion** (Camera + mmWave Radar)
- **Auto-calibration** via gimbal sweep

### 1.3 System Boundaries
- **Edge**: Raspberry Pi with gimbal-mounted sensors
- **Cloud**: MQTT broker + time-series database
- **Client**: Web-based dashboard (WebGL)

---

## 2. Architecture

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         UNITY SIMULATION                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Virtual Library Room with 32 Seats                         │   │
│  │  ┌─────┐ ┌─────┐    ┌─────┐ ┌─────┐                        │   │
│  │  │ Z1  │ │ Z2  │... │ Z7  │ │ Z8  │   8 Zones              │   │
│  │  │4seat│ │4seat│    │4seat│ │4seat│                        │   │
│  │  └─────┘ └─────┘    └─────┘ └─────┘                        │   │
│  │                                                             │   │
│  │  ┌──────────────────────────────────────────────────────┐  │   │
│  │  │  VIRTUAL SENSOR HEAD (Gimbal + Camera + Radar)      │  │   │
│  │  │  • Sweeps through 8 positions                       │  │   │
│  │  │  • 2s dwell per zone + 1s transition                │  │   │
│  │  │  • Generates sensor data per seat                   │  │   │
│  │  └──────────────────────┬───────────────────────────────┘  │   │
│  └─────────────────────────┼─────────────────────────────────┘   │
└────────────────────────────┼──────────────────────────────────────┘
                             │ MQTT
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EDGE PROCESSOR (Raspberry Pi)                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  SENSOR FUSION MODULE                                       │   │
│  │  • Receives: presence, motion, object_type per seat         │   │
│  │  • Camera: Person/Bag/Empty classification                  │   │
│  │  • Radar: Micro-motion detection (breathing/fidgeting)      │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                          │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │  GHOST DETECTION ENGINE                                     │   │
│  │  • State machine: Empty → Occupied → Suspected → Ghost     │   │
│  │  • Timers: 2min grace period, 5min ghost threshold         │   │
│  │  • Confidence scoring based on sensor agreement            │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
│                         │                                          │
│  ┌──────────────────────▼──────────────────────────────────────┐   │
│  │  PREDICTION MODULE (Lightweight)                            │   │
│  │  • 20-minute occupancy forecasting                          │   │
│  │  • Trend analysis from historical data                      │   │
│  └──────────────────────┬──────────────────────────────────────┘   │
└─────────────────────────┼──────────────────────────────────────────┘
                          │ MQTT
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         CLOUD LAYER                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │  MQTT Broker    │  │  InfluxDB       │  │  Analytics Engine   │ │
│  │  (Mosquitto)    │  │  (Time Series)  │  │  • Peak hours       │ │
│  │                 │  │  • Historical   │  │  • Ghost patterns   │ │
│  │  Topics:        │  │    occupancy    │  │  • Utilization      │ │
│  │  /telemetry/*   │  │  • State changes│  │    metrics          │ │
│  │  /state/*       │  │  • Predictions  │  │                     │ │
│  │  /alerts/*      │  │                 │  │                     │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                          │ MQTT over WebSocket
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DASHBOARD (WebGL)                              │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Unity WebGL Build (Same assets as simulation)              │   │
│  │                                                             │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │  Zone Grid   │  │  Gimbal View │  │  Ghost Alerts    │  │   │
│  │  │  32 seats    │  │  Position    │  │  Countdown timers│  │   │
│  │  │  Color-coded │  │  Indicator   │  │                  │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │   │
│  │                                                             │   │
│  │  Features:                                                  │   │
│  │  • Real-time occupancy visualization                        │   │
│  │  • State transition history                                 │   │
│  │  • Confidence scores                                        │   │
│  │  • Predictive overlay (+20min forecast)                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Unity Simulation** | Generate realistic sensor data from 3D environment | Unity 3D, C# |
| **MQTT Broker** | Message routing between components | Mosquitto |
| **Edge Processor** | Real-time inference, state machine, ghost detection | Python 3.11 |
| **Time-Series DB** | Store historical data for analytics | InfluxDB |
| **Dashboard** | Real-time visualization and control | Unity WebGL |

---

## 3. Physical Layout

### 3.1 Room Configuration

```
TOP-DOWN VIEW (Gimbal positioned at center)

Section A (Left)                          Section B (Right)
┌─────────────────────┐                   ┌─────────────────────┐
│      ZONE 1         │                   │      ZONE 5         │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S1  │  │ S2  │   │    AISLE 1        │   │ S17 │  │ S18 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S5  │  │ S6  │   │                   │   │ S21 │  │ S22 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
└─────────────────────┘                   └─────────────────────┘

┌─────────────────────┐                   ┌─────────────────────┐
│      ZONE 2         │                   │      ZONE 6         │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S9  │  │ S10 │   │    AISLE 2        │   │ S25 │  │ S26 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S13 │  │ S14 │   │                   │   │ S29 │  │ S30 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
└─────────────────────┘                   └─────────────────────┘

┌─────────────────────┐                   ┌─────────────────────┐
│      ZONE 3         │                   │      ZONE 7         │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S3  │  │ S4  │   │    AISLE 3        │   │ S19 │  │ S20 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S7  │  │ S8  │   │                   │   │ S23 │  │ S24 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
└─────────────────────┘                   └─────────────────────┘

┌─────────────────────┐                   ┌─────────────────────┐
│      ZONE 4         │                   │      ZONE 8         │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S11 │  │ S12 │   │    AISLE 4        │   │ S27 │  │ S28 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
│  ┌─────┐  ┌─────┐   │                   │   ┌─────┐  ┌─────┐  │
│  │ S15 │  │ S16 │   │                   │   │ S31 │  │ S32 │  │
│  └─────┘  └─────┘   │                   │   └─────┘  └─────┘  │
└─────────────────────┘                   └─────────────────────┘

GIMBAL POSITIONS (Sweep Sequence):
Pos 1: Zone 1  →  Pos 2: Zone 2  →  Pos 3: Zone 3  →  Pos 4: Zone 4
  ↓                                                    ↓
Pos 8: Zone 8  ←  Pos 7: Zone 7  ←  Pos 6: Zone 6  ←  Pos 5: Zone 5
```

### 3.2 Zone-to-Seat Mapping

| Zone | Seat Numbers | Section | Position Angle |
|------|-------------|---------|----------------|
| Z1 | S1, S2, S5, S6 | Left (Back) | 0° |
| Z2 | S9, S10, S13, S14 | Left (Middle-Back) | 45° |
| Z3 | S3, S4, S7, S8 | Left (Middle-Front) | 90° |
| Z4 | S11, S12, S15, S16 | Left (Front) | 135° |
| Z5 | S17, S18, S21, S22 | Right (Back) | 180° |
| Z6 | S25, S26, S29, S30 | Right (Middle-Back) | 225° |
| Z7 | S19, S20, S23, S24 | Right (Middle-Front) | 270° |
| Z8 | S27, S28, S31, S32 | Right (Front) | 315° |

### 3.3 Gimbal Specifications

- **Pan Range**: 0 - 360 degrees continuous rotation
- **Tilt Range**: -30 to +30 degrees (for height adjustment)
- **Sweep Time**: approximately 24 seconds per full cycle (8 zones x 3 seconds)
- **Dwell Time**: 2 seconds per zone
- **Transition Time**: 1 second between zones

---

## 4. Hardware Components

### 4.1 Virtual Hardware (Simulation)

Since this is a simulation-based system:

| Component | Simulation Method | Output |
|-----------|------------------|---------|
| **mmWave Radar** | Raycast + noise | Distance, velocity, motion intensity |
| **Camera** | Unity Camera render | RGB frame, object bounding boxes |
| **Gimbal** | Unity Animator/Script | Rotation angles, position feedback |

### 4.2 Real Hardware (Optional Extension)

For physical deployment:

| Component | Model | Purpose |
|-----------|-------|---------|
| **Controller** | Raspberry Pi 4/5 | Edge processing |
| **Radar** | HLK-LD2410B or similar | Presence + micro-motion |
| **Camera** | RPi Camera Module 3 | Object classification |
| **Gimbal** | 2-axis servo mount | Sensor positioning |
| **Servos** | MG996R or similar | Pan/tilt control |

### 4.3 Sensor Fusion Logic

```
CAMERA INPUT                 RADAR INPUT
┌──────────────┐            ┌──────────────┐
│ Object Type  │            │ Motion Score │
│ • person     │            │ • 0.0 - 1.0  │
│ • bag        │            │ • breathing  │
│ • book       │            │ • fidgeting  │
│ • empty      │            │ • none       │
└──────┬───────┘            └──────┬───────┘
       │                           │
       └──────────┬────────────────┘
                  ▼
        ┌─────────────────┐
        │  FUSION LOGIC   │
        ├─────────────────┤
        │ IF person + motion │
        │ → Occupied      │
        │ IF object + no motion│
        │ → SuspectedGhost│
        │ IF no object + no motion│
        │ → Empty         │
        └─────────────────┘
```

---

## 5. Software Stack

### 5.1 Technology Selection

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Simulation** | Unity 2022.3 LTS | Industry standard, WebGL export |
| **Game Logic** | C# | Native Unity language |
| **Edge Processing** | Python 3.11 | Rich ML ecosystem, MQTT support |
| **MQTT Broker** | Eclipse Mosquitto | Lightweight, reliable |
| **Database** | InfluxDB 2.x | Time-series optimized |
| **Dashboard** | Unity WebGL | Same assets as simulation |
| **Web Server** | Nginx | Static file serving |

### 5.2 Python Dependencies

The edge processor relies on the following libraries: paho-mqtt for MQTT communication, influxdb-client for time-series storage, numpy and pandas for numerical and data analysis, scikit-learn for lightweight ML prediction, opencv-python for computer vision if using a real camera, pydantic for data validation, python-dotenv for configuration management, and schedule for periodic tasks.

### 5.3 Unity Packages

The Unity project uses M2Mqtt (or a custom implementation) for MQTT connectivity, TextMeshPro for UI text rendering, Cinemachine for camera control, and Post Processing Stack for visual enhancements.

---

## 6. Data Models

### 6.1 Sensor Telemetry (Unity to Edge)

Published to: `liberty_twin/telemetry/zone/{zone_id}`

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
      "radar_velocity": 0.00
    },
    "S5": {
      "seat_id": "S5",
      "presence_score": 0.05,
      "motion_score": 0.01,
      "object_type": "empty",
      "object_confidence": 0.95,
      "distance_m": 0.0,
      "radar_velocity": 0.00
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

### 6.2 Zone State (Edge to Cloud)

Published to: `liberty_twin/state/zone/{zone_id}`

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
      "occupant_type": "person"
    },
    "S2": {
      "seat_id": "S2",
      "state": "suspected_ghost",
      "confidence": 0.85,
      "last_updated": 1707153580,
      "ghost_timer_s": 120,
      "occupant_type": "bag"
    },
    "S5": {
      "seat_id": "S5",
      "state": "empty",
      "confidence": 0.95,
      "last_updated": 1707153600,
      "occupant_type": null
    },
    "S6": {
      "seat_id": "S6",
      "state": "occupied",
      "confidence": 0.91,
      "last_updated": 1707153600,
      "occupant_type": "person"
    }
  }
}
```

### 6.3 Alert Events (Edge to Cloud)

Published to: `liberty_twin/alerts/{alert_type}`

**Ghost Detected:**
```json
{
  "timestamp": 1707153600,
  "alert_type": "ghost_confirmed",
  "zone_id": "Z1",
  "seat_id": "S2",
  "ghost_duration_s": 300,
  "confidence": 0.85
}
```

**State Transition:**
```json
{
  "timestamp": 1707153600,
  "alert_type": "state_change",
  "zone_id": "Z1",
  "seat_id": "S2",
  "from_state": "suspected_ghost",
  "to_state": "ghost",
  "reason": "motion_timeout"
}
```

### 6.4 Historical Record (InfluxDB Schema)

**Measurement:** `seat_occupancy`

| Field | Type | Description |
|-------|------|-------------|
| `presence_score` | float | Raw presence detection (0-1) |
| `motion_score` | float | Motion intensity (0-1) |
| `state` | string | Current state enum |
| `confidence` | float | System confidence (0-1) |
| `object_type` | string | Camera classification |

**Tags:**
- `seat_id` (S1-S32)
- `zone_id` (Z1-Z8)
- `section` (left/right)

**Measurement:** `system_metrics`

| Field | Type | Description |
|-------|------|-------------|
| `sweep_cycle_time_ms` | int | Time for full sweep |
| `messages_processed` | int | MQTT messages this minute |
| `avg_confidence` | float | Average confidence across seats |

---

## 7. State Machine

### 7.1 Seat States

```
                    ┌─────────────────────────────────────┐
                    │              EMPTY                  │
                    │  • No presence detected             │
                    │  • No objects visible               │
                    └──────────────┬──────────────────────┘
                                   │ Presence > threshold
                                   │ Object detected
                                   ▼
                    ┌─────────────────────────────────────┐
                    │            OCCUPIED                 │
                    │  • Person or object present         │
                    │  • Motion detected                  │
                    │  • Someone actively using seat      │
                    └──────────────┬──────────────────────┘
                                   │ Motion < threshold
                                   │ For grace period
                                   ▼
                    ┌─────────────────────────────────────┐
                    │        SUSPECTED_GHOST              │
                    │  • Object still present             │
                    │  • No motion for 2+ minutes         │
                    │  • Grace period active              │
                    │  • Countdown timer visible          │
                    └──────────────┬──────────────────────┘
                                   │ Motion still < threshold
                                   │ After ghost threshold
                                   ▼
                    ┌─────────────────────────────────────┐
                    │             GHOST                   │
                    │  • Object confirmed static          │
                    │  • No motion for 5+ minutes         │
                    │  • Seat effectively available       │
                    │  • Flagged for reallocation         │
                    └──────────────┬──────────────────────┘
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              │ Presence lost      │ Motion detected    │
              ▼                    ▼                    │
    ┌─────────────────┐  ┌─────────────────┐            │
    │     EMPTY       │  │   OCCUPIED      │            │
    │ (bag removed)   │  │ (person back)   │            │
    └─────────────────┘  └─────────────────┘            │
                                                        │
    State Transitions:                                  │
    • SUSPECTED_GHOST → EMPTY: Bag taken away          │
    • SUSPECTED_GHOST → OCCUPIED: Person returns       │
    • GHOST → OCCUPIED: Person returns (reset timer)   │
    • GHOST → EMPTY: Bag removed                       │
```

### 7.2 State Transition Conditions

| Transition | Condition | Action |
|------------|-----------|--------|
| **Empty -> Occupied** | `presence > 0.6` AND (`motion > 0.15` OR `object_type == "person"`) | Start occupancy timer |
| **Occupied -> SuspectedGhost** | `presence > 0.6` AND `motion < 0.15` for `t_grace` (2 min) | Start ghost timer, emit alert |
| **SuspectedGhost -> Ghost** | `motion < 0.15` for `t_ghost` (5 min total) | Confirm ghost, emit alert, mark available |
| **SuspectedGhost -> Occupied** | `motion > 0.15` OR `object_type == "person"` | Reset timers, emit "returned" alert |
| **SuspectedGhost -> Empty** | `presence < 0.3` | Object removed, reset state |
| **Ghost -> Occupied** | `motion > 0.15` OR `object_type == "person"` | Person returned, reset to occupied |
| **Ghost -> Empty** | `presence < 0.3` | Bag removed, seat free |
| **Occupied -> Empty** | `presence < 0.3` | Person left with belongings |

### 7.3 Confidence Calculation

The confidence score is computed by averaging the camera's object classification confidence with a scaled version of the radar motion score. When the two sensors agree (for example, the camera sees a person and the radar detects motion, or the camera sees a bag and the radar detects no motion), a bonus of 0.1 is added to the confidence. The final confidence is capped at 1.0.

---

## 8. MQTT Protocol

### 8.1 Topic Structure

```
liberty_twin/
├── telemetry/
│   └── zone/{zone_id}           # Unity → Edge (sensor data)
├── state/
│   └── zone/{zone_id}           # Edge → Cloud (computed states)
├── alerts/
│   ├── ghost_detected           # Ghost confirmed
│   ├── ghost_suspected          # Entered grace period
│   ├── state_change             # Any state transition
│   └── seat_returned            # Person returned to ghost seat
├── commands/
│   ├── calibrate                # Start auto-calibration
│   ├── sweep_control            # Pause/resume sweep
│   └── config_update            # Update thresholds
├── health/
│   ├── edge/status              # Edge processor heartbeat
│   ├── unity/status             # Unity sim heartbeat
│   └── system/metrics           # Performance metrics
└── forecast/
    └── zone/{zone_id}           # Predictions for next 20min
```

### 8.2 QoS Levels

| Topic Pattern | QoS | Retain | Reason |
|--------------|-----|--------|---------|
| `telemetry/*` | 0 | No | High frequency, latest is fine |
| `state/*` | 1 | Yes | Important, deliver at least once |
| `alerts/*` | 1 | No | Events, no need to retain |
| `commands/*` | 1 | No | Actions must be received |
| `health/*` | 0 | No | Periodic, latest is fine |
| `forecast/*` | 1 | Yes | Show latest prediction |

### 8.3 Message Rates

- **Telemetry**: 8 messages per 24-second sweep = 20 msg/min
- **State Updates**: 8 messages per sweep (aggregated) = 20 msg/min
- **Alerts**: Event-driven, approximately 5-10 per hour during busy periods
- **Health**: 1 per minute (heartbeat)

---

## 9. Implementation Guide

### 9.1 Phase 1: Unity Simulation (Week 1-2)

**Objectives:**
- Create 3D library environment with 32 seats
- Implement virtual sensor head with gimbal movement
- Generate realistic sensor telemetry

**Key Components:**

The **SeatController** component is attached to each seat in the scene. It exposes a seat identifier, tracks whether the seat is occupied, and holds a reference to its occupant (person or bag). When the sensor head scans a zone, each seat calculates and returns its current presence score, motion score, and classified object type.

The **GimbalController** manages the sweep routine. It stores an array of eight zone angles (0 through 315 degrees in 45-degree increments) and continuously rotates to each position. At each zone it dwells for 2 seconds, collects data from the four seats in view, publishes the telemetry over MQTT, then transitions for 1 second before moving to the next zone.

**Deliverables:**
- [ ] 3D library scene with 32 seats
- [ ] Gimbal sweep animation (24s cycle)
- [ ] Sensor data generation per seat
- [ ] MQTT publisher integration
- [ ] Student behavior simulation (enter/study/leave)

### 9.2 Phase 2: Edge Processor (Week 2-3)

**Objectives:**
- Receive telemetry from Unity
- Run state machine for all 32 seats
- Detect ghosts and emit alerts

**Key Components:**

The **EdgeProcessor** initializes 32 seat state machines (one per seat), connects to the MQTT broker, and subscribes to all zone telemetry topics. When telemetry arrives, it parses the JSON payload, iterates through each seat's data in the zone, and feeds it to the corresponding state machine. If a state transition occurs, the processor publishes the new state to the retained seat topic and generates appropriate alerts for ghost suspicion, ghost confirmation, or person return events.

The **SeatStateMachine** defines four states: Empty, Occupied, SuspectedGhost, and Ghost. It tracks the current state, the time of entry into that state, and the timestamp of last detected motion. The transition logic checks presence and motion thresholds against configurable values (presence threshold of 0.6, motion threshold of 0.15, 2-minute grace period, 5-minute ghost threshold). On each sensor update it determines whether a state transition should occur and records the transition with its reason.

**Deliverables:**
- [ ] MQTT subscriber for telemetry
- [ ] State machine for 32 seats
- [ ] Ghost detection logic with timers
- [ ] Alert generation
- [ ] State persistence to InfluxDB

### 9.3 Phase 3: Dashboard (Week 3-4)

**Objectives:**
- Create WebGL dashboard
- Real-time zone visualization
- Ghost countdown timers

**Key Components:**

The **DashboardController** manages the display of all 8 zones. It connects to the MQTT broker via WebSocket, subscribes to zone state topics using QoS 1, and listens for incoming state updates. When a zone state message arrives, it parses the payload and updates the corresponding seat visuals by changing material colors (green for empty, red for occupied, yellow for suspected ghost, purple for confirmed ghost) and showing or hiding ghost countdown timers.

**Deliverables:**
- [ ] Unity WebGL build
- [ ] MQTT over WebSocket integration
- [ ] 32-seat grid visualization
- [ ] Color-coded state display
- [ ] Ghost countdown timers
- [ ] Gimbal position indicator

### 9.4 Phase 4: Integration & Polish (Week 5-6)

**Objectives:**
- End-to-end testing
- Performance optimization
- Demo preparation

**Deliverables:**
- [ ] Full system integration test
- [ ] Performance benchmarking (<1s latency)
- [ ] Demo script and scenarios
- [ ] Documentation completion

---

## 10. API Reference

### 10.1 MQTT Topics Reference

#### Publish Topics (Unity)

| Topic | Payload | Frequency |
|-------|---------|-----------|
| `liberty_twin/telemetry/zone/{Z1-Z8}` | SensorTelemetry | Every 3s (per zone) |
| `liberty_twin/health/unity` | `{status: "online", timestamp}` | Every 60s |

#### Publish Topics (Edge Processor)

| Topic | Payload | Retain |
|-------|---------|--------|
| `liberty_twin/state/zone/{Z1-Z8}` | ZoneState | Yes |
| `liberty_twin/state/seat/{S1-S32}` | SeatState | Yes |
| `liberty_twin/alerts/ghost_detected` | GhostAlert | No |
| `liberty_twin/alerts/state_change` | StateChangeAlert | No |
| `liberty_twin/health/edge` | HealthStatus | No |

#### Subscribe Topics (Edge Processor)

| Topic | Action |
|-------|--------|
| `liberty_twin/telemetry/zone/+` | Process sensor data |
| `liberty_twin/commands/calibrate` | Start calibration |
| `liberty_twin/commands/config_update` | Update thresholds |

#### Subscribe Topics (Dashboard)

| Topic | Action |
|-------|--------|
| `liberty_twin/state/zone/+` | Update zone display |
| `liberty_twin/alerts/+` | Show notifications |
| `liberty_twin/health/+` | System status |

### 10.2 REST API (Optional)

If implementing a REST API for the web dashboard, the following endpoints are available:

- **GET /api/v1/zones** - List all zones with current state
- **GET /api/v1/zones/{zone_id}** - Get detailed zone info
- **GET /api/v1/seats/{seat_id}/history** - Get 24-hour history for seat
- **GET /api/v1/analytics/ghosts** - Ghost detection statistics
- **POST /api/v1/commands/calibrate** - Trigger auto-calibration

---

## 11. Dashboard Specification

### 11.1 Layout Design

```
┌─────────────────────────────────────────────────────────────────────┐
│  LIBERTY TWIN - Library Occupancy Dashboard          [Live]         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  FLOOR PLAN - 32 Seats                                      │   │
│  │                                                             │   │
│  │  Section A (Left)          Section B (Right)               │   │
│  │  ┌──────────────┐          ┌──────────────┐                │   │
│  │  │ S1  S2       │          │ S17 S18      │                │   │
│  │  │ RED PURP     │          │ GRN RED      │                │   │
│  │  │ S5  S6       │          │ S21 S22      │                │   │
│  │  │ GRN RED      │          │ RED YLW      │                │   │
│  │  └──────────────┘          └──────────────┘                │   │
│  │  ┌──────────────┐          ┌──────────────┐                │   │
│  │  │ S9  S10      │          │ S25 S26      │                │   │
│  │  │ RED GRN      │          │ GRN GRN      │                │   │
│  │  │ S13 S14      │          │ S29 S30      │                │   │
│  │  │ YLW RED      │          │ RED PURP     │                │   │
│  │  └──────────────┘          └──────────────┘                │   │
│  │                                                              │   │
│  │  Legend: GRN=Empty  RED=Occupied  YLW=Suspected  PURP=Ghost  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ GIMBAL STATUS    │  │ GHOST ALERTS     │  │ 20-MIN FORECAST  │ │
│  │                  │  │                  │  │                  │ │
│  │ Position: Z3     │  │ • S2: 4:30 min   │  │ Zone 1: 75%      │ │
│  │ Angle: 90°       │  │ • S14: 2:15 min  │  │ Zone 2: 40%      │ │
│  │ Sweep: #156      │  │ • S30: 6:00 min  │  │ Zone 3: 90%      │ │
│  │                  │  │                  │  │ ...              │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ ZONE DETAIL: Z1                                             │   │
│  │ S1: Occupied (89%)  |  S2: Ghost (85%) [4:30]              │   │
│  │ S5: Empty (95%)     |  S6: Occupied (91%)                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 11.2 Interactive Features

- **Click seat**: Show detailed history and confidence breakdown
- **Hover zone**: Highlight all 4 seats in zone
- **Click ghost seat**: Show countdown timer and "person returned" simulation
- **Time slider**: View historical occupancy (optional)

### 11.3 Color Coding

| State | Color | Hex | RGB |
|-------|-------|-----|-----|
| Empty | Green | `#2ECC71` | (46, 204, 113) |
| Occupied | Red | `#E74C3C` | (231, 76, 60) |
| Suspected Ghost | Yellow | `#F39C12` | (243, 156, 18) |
| Ghost | Purple | `#9B59B6` | (155, 89, 182) |

---

## 12. Setup & Deployment

### 12.1 Prerequisites

**Hardware:**
- Computer capable of running Unity (Mac/Windows/Linux)
- Raspberry Pi 4 (or Mac for development/simulation)
- Network connection

**Software:**
- Unity 2022.3 LTS or newer
- Python 3.11+
- Docker (for InfluxDB and Mosquitto)
- Git

### 12.2 Installation

The installation process involves cloning the repository, starting the infrastructure services (Mosquitto MQTT broker and InfluxDB) via Docker Compose, installing the Python dependencies for the edge processor, configuring environment variables for MQTT and InfluxDB credentials, launching the edge processor, opening and running the Unity simulation, and finally viewing the dashboard in a browser or via the WebGL build.

### 12.3 Configuration

The system is configured through environment variables covering MQTT connection details (broker address, port, username, password), InfluxDB connection details (URL, token, organization, bucket), detection thresholds (presence threshold of 0.6, motion threshold of 0.15, grace period of 120 seconds, ghost threshold of 300 seconds), and gimbal parameters (sweep speed of 45 degrees/second, dwell time of 2 seconds, transition time of 1 second).

### 12.4 Development Mode (Mac Simulation)

For development without a Raspberry Pi, the edge processor can be run in simulation mode by setting appropriate environment variables. It receives data from the Unity simulation and processes it identically to how it would on real hardware.

### 12.5 Production Deployment

On a Raspberry Pi, the edge processor can be installed as a systemd service for automatic startup and managed through standard service control and log viewing mechanisms.

---

## 13. Demo Script

### 13.1 5-Minute Demo Flow

**Scene 1: Empty Library (30s)**
- Show dashboard with all seats green (Empty)
- Explain the system architecture briefly
- Show gimbal sweeping in Unity simulation

**Scene 2: Student Enters (60s)**
- Spawn student in Zone 1, Seat 1
- Watch seat turn red (Occupied) on dashboard
- Show confidence score (89%)
- Explain sensor fusion (camera + radar)

**Scene 3: Ghost Creation (90s)**
- Student stands up, walks away (bag stays)
- Wait for grace period (2 min)
- Seat turns yellow (Suspected Ghost) with countdown
- Show timer: "2:00 remaining"

**Scene 4: Ghost Confirmed (60s)**
- After 5 min total, seat turns purple (Ghost)
- Show alert notification
- Explain: "Seat is effectively available"

**Scene 5: Student Returns (60s)**
- Student returns to seat
- Seat immediately turns red (Occupied)
- Show state transition log

**Scene 6: Prediction View (optional, 30s)**
- Switch to forecast view
- Show Zone 2 trending to 90% occupancy in 20 min
- Explain predictive analytics

**Wrap-up (30s)**
- Summary of ghost detection accuracy
- Privacy preservation benefits
- Real-world deployment potential

---

## 14. Future Enhancements

### Phase 2 Features
- [ ] Per-seat prediction (not just zone-level)
- [ ] Smart gimbal prioritization (focus on suspected ghosts)
- [ ] Integration with library booking system
- [ ] Mobile app for students
- [ ] Heatmap analytics for library management

### Phase 3 Features
- [ ] Real hardware deployment
- [ ] Multiple sensor heads
- [ ] Facial recognition (privacy-preserving)
- [ ] CO2/environmental sensors
- [ ] Predictive maintenance for sensors

---

## Appendix A: Glossary

- **Ghost Occupancy**: Seat occupied by belongings but not person
- **Gimbal**: Motorized mount for positioning sensors
- **mmWave Radar**: Millimeter-wave radar for presence/motion detection
- **Digital Twin**: Virtual representation of physical space
- **Temporal Multiplexing**: Sharing sensor across multiple locations via rotation
- **Micro-motion**: Subtle movements (breathing, fidgeting) detected by radar

## Appendix B: Troubleshooting

**Issue: Unity not connecting to MQTT**
- Check broker address in Unity MQTT settings
- Verify Mosquitto is running
- Test with MQTT Explorer

**Issue: No state updates on dashboard**
- Check Edge Processor is running
- Verify topic subscriptions
- Check InfluxDB connection

**Issue: Ghost detection not triggering**
- Verify thresholds in configuration
- Check motion scores in telemetry
- Review state machine logs

## Appendix C: References

- Unity MQTT: https://github.com/gpvigano/M2MqttUnity
- InfluxDB Python: https://github.com/influxdata/influxdb-client-python
- Mosquitto MQTT: https://mosquitto.org/
- mmWave Radar Basics: https://www.ti.com/lit/wp/spyy006a/spyy006a.pdf

---

**Document Version:** 1.0
**Last Updated:** February 2025
**Authors:** Liberty Twin Team
**License:** MIT
