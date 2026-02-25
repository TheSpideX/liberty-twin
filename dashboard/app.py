
import base64
import json
import logging
import os
import threading
import time
from datetime import datetime, timezone

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("liberty-twin-dashboard")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET", "liberty-twin-secret-key")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

state = {
    "sensors": {},
    "zones": {},
    "seats": {},
    "alerts": [],
    "stats": {
        "occupied": 0,
        "empty": 0,
        "ghost": 0,
        "suspected": 0,
        "total_scans": 0,
        "utilization": 0.0,
    },
    "camera_frames": {},
    "history": [],
}
state_lock = threading.Lock()

HISTORY_MAX = 3600

_last_history_ts = 0

def _maybe_record_history():
    global _last_history_ts
    now = time.time()
    if now - _last_history_ts < 5:
        return
    _last_history_ts = now
    point = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "occupied": state["stats"]["occupied"],
        "empty": state["stats"]["empty"],
        "ghost": state["stats"]["ghost"],
        "suspected": state["stats"]["suspected"],
        "total": state["stats"]["occupied"] + state["stats"]["empty"]
                 + state["stats"]["ghost"] + state["stats"]["suspected"],
    }
    state["history"].append(point)
    if len(state["history"]) > HISTORY_MAX:
        state["history"] = state["history"][-HISTORY_MAX:]

def _recompute_stats():
    counts = {"occupied": 0, "empty": 0, "ghost": 0, "suspected": 0}
    for seat in state["seats"].values():
        s = seat.get("state", "empty")
        if s in counts:
            counts[s] += 1
    total = sum(counts.values()) or 1
    state["stats"].update(counts)
    state["stats"]["utilization"] = round(counts["occupied"] / total * 100, 1)
    _maybe_record_history()

mqtt_client = None
mqtt_connected = False

def _start_mqtt():
    global mqtt_client, mqtt_connected
    try:
        import paho.mqtt.client as paho_mqtt

        broker_host = os.environ.get("MQTT_HOST", "localhost")
        broker_port = int(os.environ.get("MQTT_PORT", 1883))

        def on_connect(client, userdata, flags, reason_code, properties=None):
            global mqtt_connected
            mqtt_connected = True
            log.info("MQTT connected to %s:%s", broker_host, broker_port)
            client.subscribe("liberty_twin/state/#")
            client.subscribe("liberty_twin/alerts/#")
            client.subscribe("liberty_twin/sensor/+/camera")

        def on_disconnect(client, userdata, flags, reason_code, properties=None):
            global mqtt_connected
            mqtt_connected = False
            log.warning("MQTT disconnected (rc=%s)", reason_code)

        def on_message(client, userdata, msg):
            topic = msg.topic
            try:
                if topic.endswith("/camera"):
                    parts = topic.split("/")
                    sensor_id = parts[2] if len(parts) >= 4 else "unknown"
                    frame_b64 = base64.b64encode(msg.payload).decode("ascii")
                    with state_lock:
                        state["camera_frames"][sensor_id] = frame_b64
                    socketio.emit("camera_frame", {
                        "sensor_id": sensor_id,
                        "image": frame_b64,
                    })
                    return

                payload = json.loads(msg.payload.decode())

                if topic.startswith("liberty_twin/state/"):
                    _handle_state_message(topic, payload)
                elif topic.startswith("liberty_twin/alerts/"):
                    _handle_alert_message(topic, payload)

            except Exception as exc:
                log.error("Error processing MQTT message on %s: %s", topic, exc)

        client = paho_mqtt.Client(
            paho_mqtt.CallbackAPIVersion.VERSION2,
            client_id="liberty-twin-dashboard",
        )
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message

        client.connect_async(broker_host, broker_port, keepalive=60)
        client.loop_start()
        mqtt_client = client
        log.info("MQTT client started (connecting to %s:%s)", broker_host, broker_port)
    except Exception as exc:
        log.warning("MQTT not available, running in HTTP-only mode: %s", exc)

def _handle_state_message(topic, payload):
    with state_lock:
        if "sensor_id" in payload:
            sid = payload["sensor_id"]
            state["sensors"][sid] = {
                "status": payload.get("status", "online"),
                "zone": payload.get("zone", ""),
                "last_seen": datetime.now(timezone.utc).isoformat(),
            }
            socketio.emit("sensor_status", {
                "sensor_id": sid,
                **state["sensors"][sid],
            })

        if "zone" in payload and "seats" in payload:
            zone_name = payload["zone"]
            seats_data = payload["seats"]
            state["zones"][zone_name] = {
                "name": zone_name,
                "occupied": sum(1 for s in seats_data if s.get("state") == "occupied"),
                "total": len(seats_data),
                "seats": {s["id"]: s for s in seats_data},
            }
            for s in seats_data:
                state["seats"][s["id"]] = {**s, "zone": zone_name}

            _recompute_stats()
            state["stats"]["total_scans"] = state["stats"].get("total_scans", 0) + 1

            socketio.emit("telemetry", {
                "zone": zone_name,
                "zone_data": state["zones"][zone_name],
                "stats": state["stats"],
            })
            socketio.emit("stats", state["stats"])
            socketio.emit("seat_state", {
                "seats": {sid: sdata for sid, sdata in state["seats"].items()},
            })

def _handle_alert_message(topic, payload):
    with state_lock:
        alert = {
            "type": payload.get("type", "ghost"),
            "message": payload.get("message", "Unknown alert"),
            "seat_id": payload.get("seat_id", ""),
            "zone": payload.get("zone", ""),
            "countdown": payload.get("countdown", 0),
            "timestamp": payload.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
        }
        state["alerts"].insert(0, alert)
        state["alerts"] = state["alerts"][:200]

    socketio.emit("ghost_alert", alert)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/telemetry", methods=["POST"])
def api_telemetry():
    payload = request.get_json(force=True)
    _handle_state_message("liberty_twin/state/http", payload)
    return jsonify({"status": "ok"})

@app.route("/api/camera", methods=["POST"])
def api_camera():
    payload = request.get_json(force=True)
    sensor_id = payload.get("sensor_id", "unknown")
    image_b64 = payload.get("image", "")
    with state_lock:
        state["camera_frames"][sensor_id] = image_b64
    socketio.emit("camera_frame", {"sensor_id": sensor_id, "image": image_b64})
    return jsonify({"status": "ok"})

@app.route("/api/status", methods=["POST"])
def api_status():
    payload = request.get_json(force=True)
    sid = payload.get("sensor_id", "unknown")
    with state_lock:
        state["sensors"][sid] = {
            "status": payload.get("status", "online"),
            "zone": payload.get("zone", ""),
            "last_seen": datetime.now(timezone.utc).isoformat(),
        }
    socketio.emit("sensor_status", {"sensor_id": sid, **state["sensors"][sid]})
    return jsonify({"status": "ok"})

@app.route("/api/alert", methods=["POST"])
def api_alert():
    payload = request.get_json(force=True)
    _handle_alert_message("liberty_twin/alerts/http", payload)
    return jsonify({"status": "ok"})

@app.route("/api/history", methods=["GET"])
def api_history():
    minutes = int(request.args.get("minutes", 60))

    try:
        from influxdb_client import InfluxDBClient

        influx_url = os.environ.get("INFLUXDB_URL", "http://localhost:8086")
        influx_token = os.environ.get("INFLUXDB_TOKEN", "")
        influx_org = os.environ.get("INFLUXDB_ORG", "liberty")
        influx_bucket = os.environ.get("INFLUXDB_BUCKET", "liberty_twin")

        if influx_token:
            client = InfluxDBClient(
                url=influx_url, token=influx_token, org=influx_org
            )
            query_api = client.query_api()
            query = f"""
                from(bucket: "{influx_bucket}")
                  |> range(start: -{minutes}m)
                  |> filter(fn: (r) => r._measurement == "occupancy")
                  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
                  |> sort(columns: ["_time"])
    with state_lock:
        return jsonify({
            "sensors": state["sensors"],
            "zones": state["zones"],
            "seats": state["seats"],
            "stats": state["stats"],
            "alerts": state["alerts"][:20],
            "camera_frames": {
                k: v[:40] + "..." if v else ""
                for k, v in state["camera_frames"].items()
            },
        })

@socketio.on("connect")
def handle_connect():
    log.info("Browser client connected")
    with state_lock:
        socketio.emit("stats", state["stats"])
        socketio.emit("seat_state", {"seats": state["seats"]})
        for zone_name, zone_data in state["zones"].items():
            socketio.emit("telemetry", {
                "zone": zone_name,
                "zone_data": zone_data,
                "stats": state["stats"],
            })
        for sid, sdata in state["sensors"].items():
            socketio.emit("sensor_status", {"sensor_id": sid, **sdata})
        for alert in state["alerts"][:20]:
            socketio.emit("ghost_alert", alert)
        for sid, frame in state["camera_frames"].items():
            socketio.emit("camera_frame", {"sensor_id": sid, "image": frame})

@socketio.on("request_history")
def handle_history_request(data):
    minutes = data.get("minutes", 60) if data else 60
    with state_lock:
        cutoff = time.time() - minutes * 60
        history = [
            p for p in state["history"]
            if datetime.fromisoformat(p["ts"]).timestamp() > cutoff
        ]
    socketio.emit("history_data", history)

if __name__ == "__main__":
    _start_mqtt()
    port = int(os.environ.get("PORT", 5000))
    log.info("Starting Liberty Twin Dashboard on port %s", port)
    socketio.run(app, host="0.0.0.0", port=port, debug=True, allow_unsafe_werkzeug=True)
