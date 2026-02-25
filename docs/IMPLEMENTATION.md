# Liberty Twin - Implementation Guide

## Quick Start

This guide walks through implementing the Liberty Twin system step-by-step.

---

## Phase 1: Unity Simulation Setup

### Step 1: Project Setup

Create a new Unity 3D project named "LibertyTwin" using Unity 2022.3 LTS or newer.

### Step 2: Install Required Packages

The project requires M2Mqtt for MQTT communication, TextMeshPro for UI text rendering, and optionally Cinemachine for camera control. These are added through the Unity Package Manager.

### Step 3: Core Components

**LibraryManager** - Creates the room and seats:
- Creates 8 zones with 4 seats each (32 total)
- Positions zones in left and right sections
- Creates aisles between sections
- Spawns test students for simulation

**SeatController** - Manages individual seat state:
- Tracks occupant (person, bag, or empty)
- Generates sensor readings (presence, motion)
- Reports object type classification
- Calculates distance to sensor

**GimbalController** - Manages sensor head movement:
- Rotates through 8 zone positions
- Dwells 2 seconds at each zone
- Collects data from all 4 seats in zone
- Publishes telemetry via MQTT

**StudentBehavior** - Simulates realistic student actions:
- Enters library and sits at seat
- Studies for random duration
- Stands up and leaves bag (creates ghost)
- Returns later to collect bag
- Or leaves with bag (no ghost)

### Step 4: MQTT Integration

**MqttPublisher** - Handles network communication:
- Connects to MQTT broker at localhost:1883
- Publishes telemetry every 3 seconds per zone
- Subscribes to command topics
- Handles reconnection on disconnect

### Step 5: Data Generation

For each seat during sweep:
1. **Presence Score**: 0.0-1.0 based on occupant
   - Empty: 0.0-0.1
   - Person: 0.8-0.95
   - Bag: 0.75-0.85

2. **Motion Score**: 0.0-1.0 from radar simulation
   - Person: 0.1-0.8 (breathing + fidgeting)
   - Bag: 0.0-0.05 (static)
   - Empty: 0.0-0.05 (noise)

3. **Object Type**: Camera classification
   - person, bag, book, empty

4. **Confidence**: 0.0-1.0 based on detection quality

---

## Phase 2: Edge Processor (Python)

### Step 1: Environment Setup

The edge processor requires a Python 3.11+ virtual environment with its dependencies installed from the requirements file. Key libraries include paho-mqtt for MQTT communication, influxdb-client for time-series storage, and numpy for numerical operations.

### Step 2: Core Modules

**main.py** - Entry point:
- Initializes MQTT client
- Creates 32 state machines
- Subscribes to telemetry topics
- Runs event loop

**state_machine.py** - Ghost detection logic:
- Defines 4 states: Empty, Occupied, SuspectedGhost, Ghost
- Implements state transitions with timers
- 2-minute grace period before suspected ghost
- 5-minute total for confirmed ghost
- Tracks motion history

**fusion.py** - Sensor fusion:
- Combines camera and radar data
- Calculates confidence scores
- Detects sensor agreement/disagreement
- Outputs unified seat state

**mqtt_client.py** - Communication:
- Connects to broker
- Subscribes to topics with QoS
- Publishes state updates with retain
- Handles reconnection

**influx_writer.py** - Data persistence:
- Batches writes for efficiency
- Stores occupancy history
- Enables trend analysis

### Step 3: Configuration

The edge processor is configured through a YAML file that specifies MQTT connection parameters (broker address, port, credentials), detection thresholds (presence threshold of 0.6, motion threshold of 0.15, grace period of 120 seconds, ghost threshold of 300 seconds), and InfluxDB connection details (URL, token, organization, bucket). Sensitive values like tokens can be sourced from environment variables.

### Step 4: Running the Edge Processor

The edge processor is launched by setting the required environment variables (such as the InfluxDB token) and running the main entry point. On successful startup, it logs its connection to the MQTT broker, confirms subscription to telemetry topics, reports that all 32 state machines are initialized, and begins logging processed zone data as it arrives from the simulation.

---

## Phase 3: Dashboard

### Option A: Unity WebGL Dashboard

The Unity project is built for WebGL and deployed to a web server. It connects to the MQTT broker via WebSocket and provides a 3D visualization of all 32 seats.

### Option B: Web Dashboard (HTML/JS)

The web dashboard consists of an HTML page with a zone grid showing all 32 seats, color-coded by state (green for empty, red for occupied, yellow for suspected ghost, purple for confirmed ghost). It includes a gimbal position indicator, ghost countdown timers, and alert notifications.

The HTML structure contains a header with the project title and connection status, a main section with the zone grid (dynamically generated), and a sidebar showing gimbal status, ghost alerts, and current zone information. The dashboard loads the MQTT client library and connects via WebSocket.

The JavaScript logic handles four key functions: establishing the WebSocket connection to the broker, subscribing to state and alert topics, updating seat visuals when state messages arrive (changing colors and showing timers), and displaying alert notifications for ghost events.

---

## Phase 4: Integration & Testing

### Step 1: Start Infrastructure

The infrastructure services (Mosquitto MQTT broker and InfluxDB) are started via Docker Compose. After startup, verify that both containers are running and check their logs for any errors.

### Step 2: Start Components in Order

1. **Start Edge Processor** - Launch the Python application, which connects to the broker and begins listening for telemetry.
2. **Start Unity Simulation** - Open the project in Unity Editor and press Play. Verify the MQTT connection is established.
3. **Open Dashboard** - Navigate to the dashboard URL in a browser and verify that seats update in real-time.

### Step 3: Test Scenarios

**Scenario 1: Student Creates Ghost**
1. Spawn student in Unity at Seat S2
2. Wait for state: Occupied
3. Student leaves bag, walks away
4. After 2 minutes: State becomes SuspectedGhost
5. Dashboard shows countdown timer
6. After 5 minutes total: State becomes Ghost
7. Seat turns purple on dashboard

**Scenario 2: Person Returns**
1. Student returns to Seat S2 (Ghost state)
2. Motion detected
3. State immediately returns to Occupied
4. Alert: "Person returned to ghost seat"

**Scenario 3: Bag Removed**
1. Seat S2 is Ghost state
2. Bag disappears (student took it)
3. Presence drops
4. State becomes Empty

### Step 4: Performance Testing

Monitor metrics:
- Message latency (telemetry to dashboard)
- CPU usage of edge processor
- MQTT broker message rate
- Dashboard frame rate

Target metrics:
- Latency: < 500ms
- Message rate: ~40 msg/min
- CPU usage: < 50%

---

## Phase 5: Docker Deployment

### Docker Compose Services

The deployment uses Docker Compose to orchestrate three services:

- **Mosquitto** (Eclipse Mosquitto 2): The MQTT broker exposing ports 1883 (MQTT) and 9001 (WebSocket), with mounted volumes for configuration, data persistence, and logs.
- **InfluxDB** (InfluxDB 2.7): The time-series database on port 8086, initialized with the Liberty Twin organization and occupancy bucket, with persistent data storage.
- **Dashboard** (Nginx Alpine): A lightweight web server on port 8080 that serves the static dashboard files.

### Mosquitto Configuration

The Mosquitto broker is configured with two protocol listeners (MQTT on port 1883 and WebSocket on port 9001), password-based authentication with an ACL file for topic-level access control, message persistence to disk, and logging of all activity.

---

## Troubleshooting

### Issue: Unity cannot connect to MQTT

**Symptoms:** No telemetry messages, connection timeout

**Solutions:**
1. Verify Mosquitto is running
2. Check firewall settings
3. Verify correct broker address in Unity
4. Test with MQTT Explorer

### Issue: Edge processor not receiving data

**Symptoms:** No output, no state updates

**Solutions:**
1. Check subscription topic: `liberty_twin/telemetry/zone/+`
2. Verify MQTT credentials
3. Check Unity is actually publishing
4. View Mosquitto logs

### Issue: Dashboard not updating

**Symptoms:** Seats don't change color

**Solutions:**
1. Check browser console for JavaScript errors
2. Verify WebSocket connection
3. Check if edge processor is publishing state updates
4. Verify retain flag is set on state topics

### Issue: Ghost detection not working

**Symptoms:** No ghost alerts, seats stay occupied

**Solutions:**
1. Check motion threshold in config
2. Verify timer logic in state machine
3. Check Unity is simulating motion correctly
4. Review state transition logs

---

## Demo Script

### 5-Minute Demo Flow

**Slide 1: Introduction (30s)**
"Liberty Twin monitors library occupancy using a gimbal-mounted sensor head that sweeps 32 seats across 8 zones."

**Slide 2: Live Dashboard (30s)**
- Show empty library (all green)
- Point out 32 seats in 8 zones
- Show gimbal position indicator

**Demo 1: Student Enters (60s)**
1. Spawn student in Unity
2. Student walks to Seat S1
3. Watch dashboard: S1 turns red
4. Show confidence score: 89%
5. Explain sensor fusion

**Demo 2: Ghost Creation (90s)**
1. Student stands up, leaves bag
2. Bag remains on seat
3. Wait for grace period (2 min)
4. Seat turns yellow (SuspectedGhost)
5. Countdown timer appears
6. After 5 min total, seat turns purple (Ghost)
7. Alert notification appears

**Demo 3: Person Returns (60s)**
1. Student returns to seat
2. Seat immediately turns red
3. System detected motion
4. Show state transition log

**Demo 4: Predictions (30s)**
- Switch to prediction view
- Show Zone 2 will be 90% occupied in 20 min
- Explain trend analysis

**Wrap-up (30s)**
- Privacy: Raw data never leaves edge
- Cost: One sensor head for 32 seats
- Impact: Reduces seat hunting time

---

## Next Steps

1. Complete Phase 1: Unity simulation
2. Implement Phase 2: Edge processor
3. Build Phase 3: Dashboard
4. Integrate and test
5. Prepare demo
6. Document and present

**Estimated Timeline:**
- Week 1-2: Unity simulation
- Week 3: Edge processor
- Week 4: Dashboard
- Week 5: Integration & testing
- Week 6: Demo preparation
