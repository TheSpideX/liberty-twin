# Liberty Twin - System Architecture

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Component Details](#component-details)
3. [Data Flow](#data-flow)
4. [Communication Patterns](#communication-patterns)
5. [Deployment Architecture](#deployment-architecture)
6. [Scalability Considerations](#scalability-considerations)

---

## Architecture Overview

Liberty Twin follows a **three-tier edge-cloud-client architecture** with real-time data processing and visualization.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              PRESENTATION LAYER                             │
│                         (Unity WebGL Dashboard)                             │
│                                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│   │ Zone Grid    │  │ Gimbal View  │  │ Ghost Alerts │  │ Analytics    │   │
│   │ (32 seats)   │  │ Position     │  │ Countdown    │  │ Charts       │   │
│   └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘   │
│                                                                             │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ MQTT over WebSocket
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                               CLOUD LAYER                                   │
│                                                                             │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │ MQTT Broker      │    │ InfluxDB         │    │ Analytics        │     │
│   │ (Eclipse         │◄──►│ (Time-Series     │◄──►│ Engine           │     │
│   │  Mosquitto)      │    │  Database)       │    │                  │     │
│   │                  │    │                  │    │ • Peak hour      │     │
│   │ • Message        │    │ • Historical     │    │   detection      │     │
│   │   routing        │    │   occupancy      │    │ • Ghost patterns │     │
│   │ • Pub/Sub        │    │ • State changes  │    │ • Utilization    │     │
│   └────────┬─────────┘    └──────────────────┘    └──────────────────┘     │
│            │                                                                │
└────────────┼────────────────────────────────────────────────────────────────┘
             │ MQTT
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                                EDGE LAYER                                   │
│                        (Raspberry Pi 4/5 or Mac)                            │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    SENSOR FUSION MODULE                          │      │
│   │  ┌────────────┐    ┌────────────┐    ┌──────────────────────┐   │      │
│   │  │ Camera     │    │ Radar      │    │ Fusion Algorithm     │   │      │
│   │  │ Input      │    │ Input      │    │                      │   │      │
│   │  │            │    │            │    │ • Presence detection │   │      │
│   │  │ • Object   │    │ • Micro-   │    │ • Motion analysis    │   │      │
│   │  │   class    │    │   motion   │    │ • Confidence calc    │   │      │
│   │  │ • Position │    │ • Distance │    │                      │   │      │
│   │  └──────┬─────┘    └──────┬─────┘    └──────────┬───────────┘   │      │
│   └─────────┼─────────────────┼─────────────────────┼───────────────┘      │
│             │                 │                     │                       │
│             ▼                 ▼                     ▼                       │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │              GHOST DETECTION ENGINE                         │          │
│   │                                                             │          │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │          │
│   │  │ State        │───►│ Timer        │───►│ Alert        │  │          │
│   │  │ Machine      │    │ Management   │    │ Generator    │  │          │
│   │  │ (32 seats)   │    │ (Grace/      │    │              │  │          │
│   │  │              │    │  Ghost)      │    │ • MQTT pubs  │  │          │
│   │  │ 8 zones ×    │    │              │    │ • Logging    │  │          │
│   │  │ 4 seats      │    │ • 2min grace │    │              │  │          │
│   │  │              │    │ • 5min ghost │    │              │  │          │
│   │  └──────────────┘    └──────────────┘    └──────────────┘  │          │
│   └─────────────────────────────────────────────────────────────┘          │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────┐          │
│   │              PREDICTION MODULE (Optional)                   │          │
│   │                                                             │          │
│   │  • 20-minute occupancy forecasting                          │          │
│   │  • Trend analysis from InfluxDB                             │          │
│   │  • Lightweight ML model (scikit-learn)                      │          │
│   └─────────────────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ MQTT / Local
                                      │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SIMULATION LAYER                                  │
│                              (Unity 3D)                                     │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    VIRTUAL LIBRARY ROOM                          │      │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │      │
│   │  │ Section A    │  │ Aisles       │  │ Section B    │           │      │
│   │  │ (16 seats)   │  │ (4 aisles)   │  │ (16 seats)   │           │      │
│   │  │ 4 zones      │  │              │  │ 4 zones      │           │      │
│   │  └──────────────┘  └──────────────┘  └──────────────┘           │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    VIRTUAL SENSOR HEAD                           │      │
│   │  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │      │
│   │  │ Gimbal       │    │ Camera       │    │ Radar Simulator  │   │      │
│   │  │ Controller   │    │ Simulator    │    │ (Raycast + Noise)│   │      │
│   │  │              │    │              │    │                  │   │      │
│   │  │ • 8 pos      │    │ • 30 FPS     │    │ • Presence       │   │      │
│   │  │ • 24s cycle  │    │ • Object det │    │ • Velocity       │   │      │
│   │  │ • Auto sweep │    │ • Person/bag │    │ • Micro-motion   │   │      │
│   │  └──────────────┘    └──────────────┘    └──────────────────┘   │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    STUDENT SIMULATION                            │      │
│   │  • Enter → Sit → Study → Leave bag → Return → Leave with bag    │      │
│   │  • Random behavior patterns                                      │      │
│   │  • Configurable ghost duration                                   │      │
│   └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Details

### 1. Simulation Layer (Unity 3D)

**Purpose**: Generate realistic sensor data from virtual environment

**Key Components**:

#### 1.1 Virtual Sensor Head

The Virtual Sensor Head is a Unity MonoBehaviour that simulates a gimbal-mounted sensor array. It stores an array of eight zone angles (spaced at 45-degree intervals from 0 to 315 degrees), a sweep speed of 45 degrees per second, a dwell time of 2 seconds at each zone, and a 1-second transition time between zones. The sweep routine runs in a continuous loop: it rotates to the next zone angle, waits the dwell time while collecting data from all seats in the current zone's field of view, publishes the telemetry data via MQTT, then advances to the next zone index (wrapping around after zone 8) and waits for the transition period.

**Responsibilities**:
- Simulate gimbal rotation (8 positions, 24s cycle)
- Generate camera data (object classification)
- Generate radar data (presence, motion, distance)
- Publish telemetry via MQTT

#### 1.2 Seat Simulation

Each seat in the simulation has a controller that tracks its identifier, current state, and occupant reference. When queried for sensor data, it produces a data structure containing the seat ID, a Unix timestamp, a presence score, a motion score, the classified object type, classification confidence, and distance to the sensor. Sensor noise is added for realism (small random offsets to presence and motion scores).

The presence calculation returns 0.0 for empty seats, approximately 0.85 for a person (with positional variance), and approximately 0.75 for a bag. The motion calculation uses Perlin noise to simulate a person's breathing and fidgeting (yielding scores between 0.1 and 0.8), while a bag produces near-zero motion with only tiny environmental noise.

#### 1.3 Student Behavior Simulation

Students follow a scripted behavior cycle: they enter the library, move to an assigned seat, sit and study for a random duration (30-120 seconds), then study more (60-300 seconds). They then stand up, spawn a bag object at their seat, and walk away, entering the "away" phase (a ghost period lasting 2-10 minutes). After this period, they return to their seat and the bag is removed. They may study a bit longer or leave immediately. This cycle creates realistic ghost occupancy events for the system to detect.

---

### 2. Edge Layer (Python)

**Purpose**: Real-time processing, state machine, ghost detection

**Architecture Pattern**: Event-driven with async processing

The main processing pipeline initializes 32 seat state machines (one per seat, labeled S1 through S32), an MQTT client, an InfluxDB client, and an alert manager. The main run loop connects to the MQTT broker, subscribes to all zone telemetry topics, and starts background tasks for MQTT message processing, periodic state publishing, and health reporting.

When telemetry arrives, each seat's data is processed asynchronously. The processing involves running the sensor fusion algorithm on the raw data, updating the corresponding state machine, and handling any state transitions. Transitions trigger state update publications via MQTT and, for important events like ghost suspicion, ghost confirmation, or person return, generate targeted alerts. All measurements are asynchronously written to InfluxDB for historical analysis.

#### 2.1 Sensor Fusion Engine

The fusion engine combines camera and radar inputs to produce a unified data structure containing a fused presence score, a motion score, the classified object type, an overall confidence, and a sensor agreement metric.

The fused presence score is a weighted average: camera presence (binary: 1.0 if any object detected, 0.0 otherwise) weighted at 0.6, and radar presence weighted at 0.4. Motion is taken directly from the radar's micro-doppler reading. Object classification comes from the camera.

Sensor agreement measures how consistent the two sensor modalities are. Full agreement (1.0) occurs when the camera sees a person and the radar detects motion, or when the camera sees a bag and the radar shows no motion, or when both agree the seat is empty. Partial disagreement yields 0.5. The overall confidence is the average of object confidence and radar presence, with a 0.1 bonus when sensors fully agree, capped at 1.0.

#### 2.2 State Machine

The state machine defines four states: Empty, Occupied, SuspectedGhost, and Ghost. Each seat state machine tracks its current state, the time it entered that state, and the last time motion was detected. Configurable parameters include a grace period (default 120 seconds), a ghost threshold (default 300 seconds), a presence threshold (0.6), and a motion threshold (0.15).

The transition logic works as follows:
- **From Empty**: If presence exceeds the threshold and either motion exceeds its threshold or the object is classified as a person, transition to Occupied.
- **From Occupied**: If presence drops below the threshold, transition to Empty. If motion stays below the threshold for longer than the grace period, transition to SuspectedGhost.
- **From SuspectedGhost**: If motion returns or a person is detected, transition back to Occupied. If presence drops, transition to Empty. If motion remains absent past the ghost threshold, transition to Ghost.
- **From Ghost**: If motion returns or a person is detected, transition to Occupied. If presence drops, transition to Empty.

Each transition records the old state, new state, timestamp, and reason. A ghost timer method returns the remaining countdown (in SuspectedGhost state) or the elapsed duration (in Ghost state).

---

### 3. Cloud Layer

**Purpose**: Message routing, data persistence, analytics

#### 3.1 MQTT Broker Configuration

The Mosquitto broker is configured with two listeners: a standard MQTT listener on port 1883 and a WebSocket listener on port 9001 for dashboard connectivity. Authentication is required (anonymous access is disabled), with credentials stored in a password file. Messages are persisted to disk, and logging captures all activity.

Access control rules enforce that Unity can only publish to telemetry and its own health topic, the edge processor can read telemetry and commands while publishing state updates and alerts, and the dashboard can read all topics while only writing to the commands topic.

#### 3.2 InfluxDB Schema

The time-series database stores two measurement types. The **seat_occupancy** measurement captures per-seat data tagged by seat ID, zone ID, and section (left or right), with fields for presence score, motion score, confidence, state, and object type. The **system_metrics** measurement tracks operational performance including sweep cycle time, messages processed, average confidence, and active ghost count.

---

### 4. Presentation Layer (Dashboard)

**Purpose**: Real-time visualization and user interaction

#### 4.1 Unity WebGL Dashboard

The dashboard manager initializes 32 seat visualizer instances and connects to the MQTT broker via WebSocket. It subscribes to zone state topics and alert topics. When a zone state message arrives, it parses the payload and updates each seat's visual representation with the new state, confidence score, and ghost timer value. When an alert message arrives, it displays an appropriate notification.

#### 4.2 Seat Visualizer Component

Each seat visualizer manages its own renderer, label text, confidence indicator, and timer display. When the state changes, the renderer's material switches to the appropriate color: green for Empty, red for Occupied, yellow (with a pulsing animation) for SuspectedGhost, and purple for Ghost. A subtle sound effect plays on state changes. The ghost timer display activates when relevant, formatting the remaining seconds as minutes:seconds and changing the text color based on urgency (red below 60 seconds, yellow below 120 seconds, white otherwise).

---

## Data Flow

### End-to-End Data Flow Diagram

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Unity Sim  │────►│ MQTT Broker  │────►│   Edge Proc  │────►│  InfluxDB    │
│   (24s loop) │     │  (routing)   │     │ (state mach) │     │ (storage)    │
└──────────────┘     └──────────────┘     └──────┬───────┘     └──────────────┘
                                                 │
                                                 │ MQTT
                                                 ▼
                                          ┌──────────────┐
                                          │   Dashboard  │
                                          │  (WebGL)     │
                                          └──────────────┘

Timeline (Single Sweep Cycle):
────────────────────────────────────────────────────────────────────────────────

T=0s    Unity publishes telemetry/Z1
        {S1: occupied, S2: bag, S5: empty, S6: occupied}

T=0.1s  MQTT broker receives and routes

T=0.2s  Edge Processor processes Z1 data
        • Updates 4 state machines
        • S2: Occupied → SuspectedGhost (timer started)
        • Publishes state/Z1

T=0.3s  Dashboard receives state/Z1
        • Updates 4 seat visualizers
        • S2 turns yellow, shows 2:00 timer

T=0.5s  InfluxDB receives data points (async batch write)

T=3s    Unity moves to Zone 2, publishes telemetry/Z2...

────────────────────────────────────────────────────────────────────────────────

T=120s  (Later) S2 timer expires
        Edge Processor: SuspectedGhost → Ghost
        • Publishes state/Z1 (S2 now Ghost)
        • Publishes alerts/ghost_confirmed
        • Dashboard: S2 turns purple

T=300s  Person returns to S2
        Unity: S2 motion_score spikes to 0.8
        Edge Processor: Ghost → Occupied
        • Publishes state/Z1
        • Publishes alerts/person_returned
        • Dashboard: S2 turns red immediately
```

---

## Communication Patterns

### 1. Request-Reply (Commands)

```
Dashboard ──► liberty_twin/commands/calibrate ──► Edge Processor
                                                     │
                                                     ▼
                                       Start calibration routine
                                                     │
Dashboard ◄── liberty_twin/commands/calibrate/ack ───┘
           {status: "started", eta_seconds: 30}
```

### 2. Pub-Sub (State Updates)

```
Edge Processor ──► liberty_twin/state/zone/Z1 ──► [Dashboard, InfluxDB, Logger]
(Retain=True)

Any new subscriber immediately receives latest state
```

### 3. Event-Driven (Alerts)

```
Edge Processor ──► liberty_twin/alerts/ghost_confirmed ──► Dashboard
(Retain=False)

Dashboard shows popup notification
```

### 4. Streaming (Telemetry)

```
Unity ──► liberty_twin/telemetry/zone/Z1 (QoS 0) ──► Edge Processor

High frequency, fire-and-forget
Latest data always most relevant
```

---

## Deployment Architecture

### Development Environment (Single Machine)

```
┌─────────────────────────────────────────────────────────────┐
│                     Development Laptop                      │
│                          (Mac/PC)                           │
│                                                             │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│   │   Unity      │  │  Docker      │  │   Python     │     │
│   │   Editor     │  │  Compose     │  │   (Edge)     │     │
│   │              │  │              │  │              │     │
│   │ • Simulation │  │ • Mosquitto  │  │ • State Mach │     │
│   │ • Dashboard  │  │ • InfluxDB   │  │ • Fusion     │     │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│          │                 │                 │              │
│          └─────────────────┼─────────────────┘              │
│                            │                                │
│                    localhost:1883 (MQTT)                     │
│                    localhost:8086 (InfluxDB)                 │
│                    localhost:8080 (Dashboard)                │
└─────────────────────────────────────────────────────────────┘
```

### Production Environment (Distributed)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLOUD VPS                                      │
│                         (AWS/DigitalOcean/etc)                              │
│                                                                             │
│   ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐     │
│   │ MQTT Broker      │    │ InfluxDB         │    │ Dashboard Server │     │
│   │ (Mosquitto)      │    │ (Time-Series)    │    │ (Nginx + WebGL)  │     │
│   │ Port: 1883/9001  │    │ Port: 8086       │    │ Port: 443        │     │
│   └────────┬─────────┘    └──────────────────┘    └──────────────────┘     │
│            │                                                                │
└────────────┼────────────────────────────────────────────────────────────────┘
             │ Internet
             │ MQTT + TLS
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EDGE DEVICE                                      │
│                        (Raspberry Pi 4/5)                                   │
│                                                                             │
│   ┌──────────────────────────────────────────────────────────────────┐      │
│   │                    EDGE PROCESSOR                                │      │
│   │  • Python Application                                            │      │
│   │  • MQTT Client (w/ TLS)                                          │      │
│   │  • InfluxDB Client                                               │      │
│   │  • State Machines (32 seats)                                     │      │
│   └──────────────────────┬───────────────────────────────────────────┘      │
│                          │                                                  │
│   ┌──────────────────────┴───────────────────────────────────────────┐      │
│   │                    SENSOR HEAD                                     │      │
│   │  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │      │
│   │  │ Camera   │    │ mmWave   │    │ Gimbal   │                   │      │
│   │  │ Module   │    │ Radar    │    │ Servos   │                   │      │
│   │  │ (USB)    │    │ (UART)   │    │ (GPIO)   │                   │      │
│   │  └──────────┘    └──────────┘    └──────────┘                   │      │
│   └──────────────────────────────────────────────────────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Scalability Considerations

### Current Scale
- **32 seats** in 8 zones
- **24-second** sweep cycle
- **~20 messages/minute** (telemetry)
- **~20 messages/minute** (state updates)
- **~5-10 alerts/hour** during busy periods

### Scaling to 128 Seats

**Option 1: Multiple Sensor Heads** - Deploy four independent sensor heads, each covering 4 zones (16 seats). Sections A through D each get their own gimbal, operating in parallel.

**Option 2: Static Sensors** - Replace the gimbal with one dedicated sensor per zone (16 sensors for 128 seats). This has a higher hardware cost but lower complexity, with all zones monitored simultaneously.

**Option 3: Hybrid Approach** - Use dedicated static sensors for high-priority zones and a shared gimbal for low-priority zones, balancing cost and responsiveness.

### Performance Optimization

To maintain performance at scale, the system uses batched writes to InfluxDB (writing multiple data points in a single request), asynchronous parallel processing of all seats within a zone, and MQTT connection pooling with configurable message queuing limits.

---

## Summary

This architecture provides:

1. **Modularity**: Each layer can be developed and tested independently
2. **Scalability**: Easy to add more zones or sensors
3. **Reliability**: MQTT QoS ensures message delivery
4. **Real-time**: Sub-second latency from sensor to dashboard
5. **Extensibility**: Easy to add new sensors or algorithms
6. **Privacy**: Raw data processed at edge, only states sent to cloud

The gimbal-based temporal multiplexing approach is cost-effective for medium-scale deployments (32-64 seats) while maintaining per-seat granularity.
