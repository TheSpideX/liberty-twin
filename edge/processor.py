#!/usr/bin/env python3

import base64
import json
import logging
import signal
import sys
import threading
import time
from io import BytesIO
from typing import Dict, List, Optional

import numpy as np

from config import (
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_CLIENT_ID,
    MQTT_KEEPALIVE,
    MQTT_TOPIC_SENSOR,
    MQTT_TOPIC_STATE_SEAT,
    MQTT_TOPIC_ALERTS_GHOST,
    INFLUXDB_URL,
    INFLUXDB_TOKEN,
    INFLUXDB_ORG,
    INFLUXDB_BUCKET,
    ZONE_TO_SEATS,
    SEAT_TO_ZONE,
    HTTP_FALLBACK_PORT,
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_CLASSES_OF_INTEREST,
    LOG_LEVEL,
    LOG_FORMAT,
    TOTAL_SEATS,
)
from sensor_fusion import SensorFusion, CameraResult, RadarResult, FusedResult
from ghost_detector import GhostDetector, GhostAlert

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=LOG_FORMAT)
logger = logging.getLogger("processor")

mqtt_client = None
influx_write_api = None
_yolo_model = None
_cv2 = None

def _init_mqtt() -> bool:
    global mqtt_client
    try:
        import paho.mqtt.client as paho_mqtt

        def on_connect(client, userdata, flags, reason_code, properties=None):
            if reason_code == 0 or str(reason_code) == "Success":
                logger.info("MQTT connected to %s:%s", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
                client.subscribe(MQTT_TOPIC_SENSOR)
                logger.info("Subscribed to %s", MQTT_TOPIC_SENSOR)
            else:
                logger.warning("MQTT connection refused: %s", reason_code)

        def on_disconnect(client, userdata, flags, reason_code, properties=None):
            logger.warning("MQTT disconnected (rc=%s). Will retry.", reason_code)

        def on_message(client, userdata, msg):
            _handle_mqtt_message(msg.topic, msg.payload)

        client = paho_mqtt.Client(
            client_id=MQTT_CLIENT_ID,
            callback_api_version=paho_mqtt.CallbackAPIVersion.VERSION2,
        )
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        client.on_message = on_message
        client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, MQTT_KEEPALIVE)
        client.loop_start()
        mqtt_client = client
        return True
    except ImportError:
        logger.warning("paho-mqtt not installed. MQTT disabled; using HTTP fallback only.")
        return False
    except Exception as exc:
        logger.warning("Cannot connect to MQTT broker at %s:%s (%s). Using HTTP fallback.",
                        MQTT_BROKER_HOST, MQTT_BROKER_PORT, exc)
        return False

def _init_influxdb() -> bool:
    global influx_write_api
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.write_api import SYNCHRONOUS

        client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
        health = client.health()
        if health.status != "pass":
            logger.warning("InfluxDB health check did not pass: %s", health.message)
        influx_write_api = client.write_api(write_options=SYNCHRONOUS)
        logger.info("InfluxDB connected at %s (org=%s, bucket=%s)",
                     INFLUXDB_URL, INFLUXDB_ORG, INFLUXDB_BUCKET)
        return True
    except ImportError:
        logger.warning("influxdb-client not installed. InfluxDB writes disabled.")
        return False
    except Exception as exc:
        logger.warning("Cannot connect to InfluxDB at %s (%s). Writes disabled.",
                        INFLUXDB_URL, exc)
        return False

def _init_object_detector():
    global _yolo_model, _cv2

    try:
        from ultralytics import YOLO
        _yolo_model = YOLO(YOLO_MODEL)
        logger.info("YOLOv8 model loaded: %s", YOLO_MODEL)
        return
    except ImportError:
        logger.info("ultralytics not installed. Falling back to OpenCV detection.")
    except Exception as exc:
        logger.info("Could not load YOLOv8 model (%s). Falling back to OpenCV.", exc)

    try:
        import cv2
        _cv2 = cv2
        logger.info("OpenCV %s loaded for fallback detection.", cv2.__version__)
        return
    except ImportError:
        logger.info("OpenCV not installed. Using threshold-only fallback detector.")

    logger.info("Object detection: threshold-only mode (no YOLO, no OpenCV).")

fusion = SensorFusion()
ghost_detector = GhostDetector()

_camera_detections: Dict[str, List[CameraResult]] = {}

_stats = {
    "telemetry_count": 0,
    "camera_count": 0,
    "ghost_alerts": 0,
    "mqtt_publishes": 0,
    "influx_writes": 0,
}

def detect_objects_in_frame(frame_bytes: bytes, sensor_name: str = "") -> List[dict]:
    detections = []

    if _yolo_model is not None:
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            import cv2 as _cv
            img = _cv.imdecode(nparr, _cv.IMREAD_COLOR)
            if img is None:
                logger.warning("Failed to decode camera frame from %s", sensor_name)
                return detections

            results = _yolo_model(img, conf=YOLO_CONFIDENCE, verbose=False)
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    label = YOLO_CLASSES_OF_INTEREST.get(cls_id)
                    if label is None:
                        label = r.names.get(cls_id, f"class_{cls_id}")
                    coords = box.xyxy[0].tolist()
                    detections.append({
                        "class": label,
                        "confidence": round(conf, 3),
                        "bbox": [round(c, 1) for c in coords],
                    })
            logger.debug("YOLO detected %d objects from %s", len(detections), sensor_name)
            return detections
        except Exception as exc:
            logger.warning("YOLO inference failed (%s), trying fallback.", exc)

    if _cv2 is not None:
        try:
            nparr = np.frombuffer(frame_bytes, np.uint8)
            img = _cv2.imdecode(nparr, _cv2.IMREAD_COLOR)
            if img is None:
                return detections
            gray = _cv2.cvtColor(img, _cv2.COLOR_BGR2GRAY)
            blurred = _cv2.GaussianBlur(gray, (11, 11), 0)
            thresh = _cv2.adaptiveThreshold(
                blurred, 255, _cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                _cv2.THRESH_BINARY_INV, 25, 8,
            )
            contours, _ = _cv2.findContours(thresh, _cv2.RETR_EXTERNAL, _cv2.CHAIN_APPROX_SIMPLE)
            h, w = img.shape[:2]
            min_area = (h * w) * 0.01

            for cnt in contours:
                area = _cv2.contourArea(cnt)
                if area < min_area:
                    continue
                x, y, bw, bh = _cv2.boundingRect(cnt)
                aspect = bh / max(bw, 1)
                fill_ratio = area / max(bw * bh, 1)
                conf = min(1.0, (area / (h * w)) * 3)
                if aspect > 1.5 and fill_ratio > 0.3:
                    label = "person"
                    conf = min(1.0, conf * 1.2)
                elif area > min_area * 2:
                    label = "object"
                else:
                    label = "unknown"

                detections.append({
                    "class": label,
                    "confidence": round(conf, 3),
                    "bbox": [x, y, x + bw, y + bh],
                })

            logger.debug("OpenCV detected %d contours from %s", len(detections), sensor_name)
            return detections
        except Exception as exc:
            logger.warning("OpenCV detection failed (%s).", exc)

    try:
        nparr = np.frombuffer(frame_bytes, np.uint8)
        mean_val = float(np.mean(nparr))
        if mean_val > 60:
            detections.append({
                "class": "object",
                "confidence": round(min(1.0, mean_val / 180), 3),
                "bbox": [0, 0, 0, 0],
            })
        logger.debug("Threshold fallback: mean=%.1f, detections=%d", mean_val, len(detections))
    except Exception as exc:
        logger.warning("Threshold detection failed: %s", exc)

    return detections

def _zone_from_sensor_name(sensor_name: str, detections: List[dict]) -> Dict[str, CameraResult]:
    results: Dict[str, CameraResult] = {}
    is_back = "Back" in sensor_name or "back" in sensor_name

    zones = ["Z1", "Z2", "Z3", "Z4"] if is_back else ["Z5", "Z6", "Z7"]

    best_person = CameraResult("empty", 0.0)
    best_object = CameraResult("empty", 0.0)

    for det in detections:
        cls = det["class"]
        conf = det["confidence"]
        if cls == "person" and conf > best_person.confidence:
            best_person = CameraResult("person", conf)
        elif cls != "person" and cls != "empty" and conf > best_object.confidence:
            best_object = CameraResult(cls, conf)

    best = best_person if best_person.confidence > best_object.confidence else best_object
    if best.confidence == 0.0:
        best = CameraResult("empty", 0.0)

    for z in zones:
        results[z] = best

    return results

def process_telemetry(data: dict):
    _stats["telemetry_count"] += 1
    zone_id = data.get("zone_id", "")
    sensor_name = data.get("sensor", "unknown")
    seats_data = data.get("seats", {})
    ts_epoch = data.get("timestamp", time.time())

    logger.info(
        "Telemetry #%d from %s zone %s (%d seats)",
        _stats["telemetry_count"], sensor_name, zone_id, len(seats_data),
    )

    alerts: List[GhostAlert] = []
    state_updates: Dict[str, dict] = {}

    for seat_id, info in seats_data.items():
        radar = RadarResult(
            presence=float(info.get("presence", 0)),
            motion=float(info.get("motion", 0)),
            micro_motion=bool(info.get("micro_motion", False)),
        )

        cam = None
        if zone_id in _camera_detections:
            zone_cams = _camera_detections[zone_id]
            if zone_cams:
                cam = zone_cams[0]
        if cam is None:
            obj_type = info.get("object_type", "empty")
            conf = float(info.get("confidence", 0))
            cam = CameraResult(object_type=obj_type, confidence=conf)

        fused = fusion.fuse(camera_result=cam, radar_result=radar)

        alert = ghost_detector.update(seat_id, fused)
        if alert is not None:
            alerts.append(alert)

        seat_state = ghost_detector.get_state(seat_id).value
        state_updates[seat_id] = {
            "seat_id": seat_id,
            "zone_id": SEAT_TO_ZONE.get(seat_id, zone_id),
            "state": seat_state,
            "occupancy_score": fused.occupancy_score,
            "object_type": fused.object_type,
            "confidence": fused.confidence,
            "is_present": fused.is_present,
            "has_motion": fused.has_motion,
            "radar_presence": fused.radar_presence,
            "radar_motion": fused.radar_motion,
            "radar_micro_motion": fused.radar_micro_motion,
            "timestamp": ts_epoch,
        }

    _publish_state_updates(state_updates)
    for alert in alerts:
        _publish_ghost_alert(alert)

    _write_to_influxdb(state_updates, alerts)

def process_camera_frame(data: dict):
    _stats["camera_count"] += 1
    sensor_name = data.get("sensor", "unknown")
    frame_b64 = data.get("frame", "")

    if not frame_b64:
        logger.warning("Empty camera frame from %s", sensor_name)
        return

    try:
        frame_bytes = base64.b64decode(frame_b64)
    except Exception as exc:
        logger.warning("Failed to decode base64 frame from %s: %s", sensor_name, exc)
        return

    logger.info(
        "Camera frame #%d from %s (%d bytes)",
        _stats["camera_count"], sensor_name, len(frame_bytes),
    )

    detections = detect_objects_in_frame(frame_bytes, sensor_name)

    zone_results = _zone_from_sensor_name(sensor_name, detections)
    for zone_id, cam_result in zone_results.items():
        _camera_detections[zone_id] = [cam_result]

    if detections:
        logger.info(
            "Detected %d objects from %s: %s",
            len(detections), sensor_name,
            ", ".join(f"{d['class']}({d['confidence']:.0%})" for d in detections[:5]),
        )

def _handle_mqtt_message(topic: str, payload: bytes):
    try:
        data = json.loads(payload.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        logger.warning("Invalid MQTT payload on %s: %s", topic, exc)
        return

    if topic.endswith("/telemetry"):
        process_telemetry(data)
    elif topic.endswith("/camera"):
        process_camera_frame(data)
    else:
        logger.debug("Unhandled MQTT topic: %s", topic)

def _publish_state_updates(updates: Dict[str, dict]):
    for seat_id, state_data in updates.items():
        topic = MQTT_TOPIC_STATE_SEAT.replace("{seat_id}", seat_id)
        payload = json.dumps(state_data)

        if mqtt_client is not None and mqtt_client.is_connected():
            try:
                mqtt_client.publish(topic, payload, qos=1)
                _stats["mqtt_publishes"] += 1
            except Exception as exc:
                logger.warning("MQTT publish failed for %s: %s", topic, exc)
        else:
            logger.debug("MQTT unavailable. State for %s: %s", seat_id, state_data["state"])

def _publish_ghost_alert(alert: GhostAlert):
    _stats["ghost_alerts"] += 1
    payload = json.dumps(alert.to_dict())

    logger.warning(
        "GHOST ALERT [%s] seat=%s zone=%s: %s",
        alert.alert_type, alert.seat_id, alert.zone_id, alert.details,
    )

    if mqtt_client is not None and mqtt_client.is_connected():
        try:
            mqtt_client.publish(MQTT_TOPIC_ALERTS_GHOST, payload, qos=1)
            _stats["mqtt_publishes"] += 1
        except Exception as exc:
            logger.warning("MQTT publish failed for ghost alert: %s", exc)

def _write_to_influxdb(updates: Dict[str, dict], alerts: List[GhostAlert]):
    if influx_write_api is None:
        return

    try:
        from influxdb_client import Point

        points = []

        for seat_id, state_data in updates.items():
            p = (
                Point("seat_state")
                .tag("seat_id", seat_id)
                .tag("zone_id", state_data.get("zone_id", ""))
                .tag("state", state_data.get("state", ""))
                .field("occupancy_score", float(state_data.get("occupancy_score", 0)))
                .field("confidence", float(state_data.get("confidence", 0)))
                .field("is_present", bool(state_data.get("is_present", False)))
                .field("has_motion", bool(state_data.get("has_motion", False)))
                .field("radar_presence", float(state_data.get("radar_presence", 0)))
                .field("radar_motion", float(state_data.get("radar_motion", 0)))
                .field("object_type", str(state_data.get("object_type", "empty")))
            )
            points.append(p)

        for alert in alerts:
            p = (
                Point("ghost_alert")
                .tag("seat_id", alert.seat_id)
                .tag("zone_id", alert.zone_id)
                .tag("alert_type", alert.alert_type)
                .field("details", alert.details)
                .field("previous_state", alert.previous_state)
                .field("new_state", alert.new_state)
            )
            points.append(p)

        if points:
            influx_write_api.write(bucket=INFLUXDB_BUCKET, record=points)
            _stats["influx_writes"] += len(points)
            logger.debug("Wrote %d points to InfluxDB", len(points))

    except Exception as exc:
        logger.warning("InfluxDB write failed: %s", exc)

def _run_http_server():
    try:
        from flask import Flask, request, jsonify
    except ImportError:
        logger.warning("Flask not installed. HTTP fallback server disabled.")
        return

    app = Flask("liberty_twin_edge")
    app.logger.setLevel(logging.WARNING)

    @app.route("/api/telemetry", methods=["POST"])
    def api_telemetry():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "no JSON body"}), 400
        try:
            process_telemetry(data)
        except Exception as exc:
            logger.error("Error processing telemetry: %s", exc, exc_info=True)
            return jsonify({"error": str(exc)}), 500
        return jsonify({"ok": True})

    @app.route("/api/camera", methods=["POST"])
    def api_camera():
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"error": "no JSON body"}), 400
        try:
            process_camera_frame(data)
        except Exception as exc:
            logger.error("Error processing camera frame: %s", exc, exc_info=True)
            return jsonify({"error": str(exc)}), 500
        return jsonify({"ok": True})

    @app.route("/api/status", methods=["GET"])
    def api_status():
        return jsonify({
            "stats": _stats,
            "seat_states": ghost_detector.get_all_states(),
            "total_seats": TOTAL_SEATS,
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "ok",
            "mqtt_connected": mqtt_client is not None and mqtt_client.is_connected(),
            "influxdb_connected": influx_write_api is not None,
            "yolo_loaded": _yolo_model is not None,
            "opencv_loaded": _cv2 is not None,
        })

    logger.info("HTTP fallback server starting on port %d", HTTP_FALLBACK_PORT)
    app.run(host="0.0.0.0", port=HTTP_FALLBACK_PORT, threaded=True, debug=False)

def _log_stats_periodically(interval: float = 30.0):
    while True:
        time.sleep(interval)
        states = ghost_detector.get_all_states()
        occupied = sum(1 for v in states.values() if v == "occupied")
        ghosts_s = sum(1 for v in states.values() if v == "suspected_ghost")
        ghosts_c = sum(1 for v in states.values() if v == "confirmed_ghost")
        empty = TOTAL_SEATS - occupied - ghosts_s - ghosts_c

        logger.info(
            "Stats | telemetry=%d camera=%d alerts=%d mqtt_pub=%d influx=%d | "
            "occupied=%d empty=%d suspected=%d confirmed=%d",
            _stats["telemetry_count"], _stats["camera_count"],
            _stats["ghost_alerts"], _stats["mqtt_publishes"], _stats["influx_writes"],
            occupied, empty, ghosts_s, ghosts_c,
        )

def main():
    print("=" * 60)
    print("  LIBERTY TWIN - Edge Processor")
    print("=" * 60)

    mqtt_ok = _init_mqtt()
    influx_ok = _init_influxdb()
    _init_object_detector()

    print()
    print(f"  MQTT:     {'CONNECTED' if mqtt_ok else 'UNAVAILABLE (using HTTP fallback)'}")
    print(f"  InfluxDB: {'CONNECTED' if influx_ok else 'UNAVAILABLE (writes disabled)'}")
    print(f"  Detector: ", end="")
    if _yolo_model is not None:
        print("YOLOv8-nano")
    elif _cv2 is not None:
        print(f"OpenCV ({_cv2.__version__})")
    else:
        print("threshold-only fallback")
    print(f"  HTTP API: http://0.0.0.0:{HTTP_FALLBACK_PORT}")
    print(f"  Seats:    {TOTAL_SEATS} across {len(ZONE_TO_SEATS)} zones")
    print("=" * 60)
    print()

    stats_thread = threading.Thread(target=_log_stats_periodically, daemon=True)
    stats_thread.start()

    def _shutdown(signum, frame):
        logger.info("Shutting down edge processor...")
        if mqtt_client is not None:
            try:
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
            except Exception:
                pass
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    _run_http_server()

if __name__ == "__main__":
    main()
