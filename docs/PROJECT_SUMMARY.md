# Liberty Twin Project Summary

## One-Line Pitch
**Privacy-preserving IoT system for library occupancy monitoring with ghost detection and predictive analytics.**

## What Problem Does It Solve?

In university libraries, students waste 10-15 minutes searching for available seats. Meanwhile, 20-30% of "occupied" seats are actually abandoned (ghosts - bags reserving space while students are away).

**Liberty Twin solves this by:**
- Real-time seat availability monitoring
- Automatic ghost detection (identifying abandoned bags)
- Predictive analytics for future occupancy
- Privacy-first design (no cameras in cloud)

## How It Works

### 1. Simulation Layer (Unity 3D)
A virtual library with 32 seats across 8 zones. Virtual students:
- Enter and sit at seats
- Study for random durations
- Leave bags and walk away (creating ghosts)
- Return later or leave with bags

A virtual sensor head on a gimbal sweeps through 8 positions:
- Dwells 2 seconds at each zone
- Collects camera + radar data
- 24-second full sweep cycle

### 2. Edge Processing (Python on Raspberry Pi)
Receives sensor data and runs:
- **Sensor Fusion**: Combines camera (object type) + radar (motion)
- **State Machine**: Tracks 4 states per seat
  - Empty -> Occupied -> SuspectedGhost -> Ghost
- **Ghost Detection**:
  - 2-minute grace period (suspected)
  - 5-minute confirmation (ghost)
- **Prediction**: 20-minute occupancy forecasting

### 3. Communication (MQTT)
Lightweight messaging between components:
- Unity publishes telemetry every 3 seconds
- Edge processor publishes state updates
- Dashboard subscribes to real-time updates
- InfluxDB stores historical data

### 4. Dashboard (WebGL)
Real-time visualization:
- 32-seat floor plan with color coding
- Green (empty), Red (occupied), Yellow (suspected), Purple (ghost)
- Ghost countdown timers
- Gimbal position indicator
- Alert notifications

## Technical Highlights

### Multi-Modal Sensor Fusion
Combines two sensor types:
- **Camera**: Identifies person vs bag vs empty
- **mmWave Radar**: Detects micro-motion (breathing/fidgeting)
- **Fusion**: Higher confidence when sensors agree

### Temporal Multiplexing
One sensor head covers 32 seats:
- Rotates through 8 zones
- Reduces hardware cost 32x
- Acceptable for library use (24s refresh)

### Privacy by Design
- All processing at edge (Raspberry Pi)
- Only state data sent to cloud
- Raw video/images never leave device
- No personal identification

### Ghost Detection Algorithm
Three-stage detection:
1. **Occupied**: Person present with motion
2. **SuspectedGhost**: Object present, no motion for 2 minutes
3. **Ghost**: Confirmed abandoned after 5 minutes

## System Specifications

| Feature | Specification |
|---------|--------------|
| Total Seats | 32 |
| Zones | 8 (4 seats each) |
| Sweep Cycle | 24 seconds |
| States per Seat | 4 (Empty, Occupied, SuspectedGhost, Ghost) |
| Grace Period | 2 minutes |
| Ghost Threshold | 5 minutes |
| Prediction Horizon | 20 minutes |
| Latency | < 500ms |

## Data Flow

```
Unity Simulation
  | (every 3s)
MQTT Broker
  |
Edge Processor (Python)
  - Sensor fusion
  - State machine
  - Ghost detection
  |
Dashboard (real-time) + InfluxDB (history)
```

## Key Features

- **Real-time occupancy** - Live seat status updates
- **Ghost detection** - Automatically identifies abandoned seats
- **Privacy-first** - No video leaves the device
- **Predictive analytics** - Forecast future occupancy
- **Cost-effective** - One sensor for 32 seats
- **Digital twin** - 3D visualization of library
- **Alert system** - Notifications for ghost seats
- **Historical data** - Trend analysis and reporting

## Demo Story (5 Minutes)

**Scene 1:** Show empty library (all green)

**Scene 2:** Student enters, sits at Seat S1
- Dashboard: S1 turns red
- Confidence: 89%

**Scene 3:** Student leaves, bag stays
- After 2 min: S1 turns yellow (suspected)
- Countdown timer: 3:00 remaining
- After 5 min: S1 turns purple (ghost)
- Alert: "Ghost detected at S1"

**Scene 4:** Student returns
- S1 immediately turns red
- Alert: "Person returned to ghost seat"

**Scene 5:** Predictions
- Show Zone 2 will be 90% full in 20 min

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Simulation | Unity 2022.3 LTS, C# |
| Edge Processing | Python 3.11, paho-mqtt |
| Message Broker | Eclipse Mosquitto (MQTT) |
| Database | InfluxDB 2.7 (time-series) |
| Dashboard | Unity WebGL or HTML/JS |
| Infrastructure | Docker, Docker Compose |

## Project Structure

```
liberty_twin/
├── docs/                    # Documentation
│   ├── README.md           # Full documentation
│   ├── ARCHITECTURE.md     # System architecture
│   ├── MQTT_PROTOCOL.md    # MQTT specification
│   ├── IMPLEMENTATION.md   # Setup guide
│   └── QUICK_REFERENCE.md  # Cheat sheet
├── docker/                 # Infrastructure
│   ├── docker-compose.yml
│   ├── mosquitto/
│   └── influxdb/
├── unity/                  # Unity project
│   ├── Assets/
│   │   ├── Scripts/
│   │   ├── Prefabs/
│   │   ├── Scenes/
│   │   └── Materials/
│   └── Packages/
├── edge_processor/         # Python application
│   ├── src/
│   │   ├── main.py
│   │   ├── state_machine.py
│   │   ├── fusion.py
│   │   └── mqtt_client.py
│   ├── tests/
│   └── requirements.txt
└── dashboard/              # Web dashboard
    ├── web/
    └── unity_webgl/
```

## Implementation Phases

### Phase 1: Unity Simulation (Week 1-2)
- [ ] Create 3D library environment
- [ ] Implement 32 seats in 8 zones
- [ ] Build virtual sensor head
- [ ] Generate realistic telemetry
- [ ] Connect to MQTT

### Phase 2: Edge Processor (Week 3)
- [ ] Implement state machine
- [ ] Build sensor fusion
- [ ] Add ghost detection logic
- [ ] Connect to MQTT and InfluxDB
- [ ] Write unit tests

### Phase 3: Dashboard (Week 4)
- [ ] Build WebGL or web dashboard
- [ ] Real-time visualization
- [ ] Ghost countdown timers
- [ ] Alert notifications
- [ ] Gimbal position indicator

### Phase 4: Integration (Week 5)
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Bug fixes
- [ ] Documentation

### Phase 5: Demo Preparation (Week 6)
- [ ] Prepare demo script
- [ ] Record demo video
- [ ] Create presentation
- [ ] Practice presentation

## Success Metrics

- **Ghost Detection Accuracy**: > 90%
- **False Positive Rate**: < 5%
- **System Latency**: < 500ms
- **Uptime**: > 99%
- **Demo Story**: Complete 5-minute flow

## Benefits

**For Students:**
- Find available seats faster
- Avoid ghost seats
- Plan library visits better

**For Library Management:**
- Understand usage patterns
- Optimize space allocation
- Reduce conflicts over seats

**For Privacy:**
- No personal data collected
- No video stored
- All processing local

## Future Enhancements

- Real hardware deployment (mmWave + camera)
- Mobile app for students
- Integration with library booking system
- Heatmap analytics
- Multi-library deployment
- Machine learning for behavior prediction

## Team Roles

**If working in a team:**

| Role | Responsibilities |
|------|-----------------|
| Unity Developer | 3D simulation, sensor head, student behavior |
| Edge Developer | State machine, ghost detection, MQTT |
| Dashboard Developer | UI/UX, real-time visualization |
| DevOps/Infrastructure | Docker, MQTT broker, database |
| Integration Lead | Testing, debugging, documentation |

**If solo:** Follow implementation phases sequentially.

## Resources

- **Documentation**: `/docs` directory
- **Code**: Repository root
- **Docker**: `/docker` directory
- **Issues**: GitHub Issues

## License

MIT License - Liberty Twin Project 2025

---

## Getting Started

1. **Clone repository** and navigate to the project root.
2. **Start infrastructure** by launching the Docker Compose services (Mosquitto and InfluxDB).
3. **Start Unity** simulation in the editor.
4. **Start edge processor** by installing Python dependencies and running the main entry point.
5. **Open dashboard** in a browser at the configured port.
6. **Watch it work!**

---

**Ready to build Liberty Twin? Start with Phase 1: Unity Simulation!**
