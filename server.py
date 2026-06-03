import sys
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, jsonify, request, Response
from flask_cors import CORS
from kafka import KafkaConsumer
from pymongo import MongoClient, DESCENDING, InsertOne
import joblib
import json
import threading
import os
import queue
import re
import time
from dotenv import load_dotenv
from datetime import datetime
from collections import defaultdict

load_dotenv()

MONGO_URL      = os.getenv("MONGO_URL",    "mongodb://localhost:27017/")
MONGO_DB       = os.getenv("MONGO_DB",     "hids_db")
KAFKA_BROKER   = os.getenv("KAFKA_BROKER", "localhost:9092")
FLASK_PORT     = int(os.getenv("FLASK_PORT", 5000))
FLUSH_INTERVAL = int(os.getenv("FLUSH_INTERVAL", 20))   # seconds between batch writes

# ── MongoDB ───────────────────────────────────────────────────────────────────
mongo_client  = MongoClient(MONGO_URL)
db            = mongo_client[MONGO_DB]
sessions_col  = db["sessions"]
alerts_col    = db["alerts"]
traffic_col   = db["traffic"]

# Indexes for fast queries
alerts_col.create_index([("timestamp", DESCENDING)])
alerts_col.create_index("src_ip")
traffic_col.create_index([("timestamp", DESCENDING)])
sessions_col.create_index("session_id", unique=True)

app = Flask(__name__)
CORS(app, origins=["http://localhost:3000"], supports_credentials=True)

# ── SSE subscriber queues ─────────────────────────────────────────────────────
_sse_clients: list[queue.Queue] = []
_sse_lock = threading.Lock()

def _push_event(event_type: str, payload: dict):
    """Broadcast a SSE event to all connected clients immediately."""
    data = json.dumps({"type": event_type, **payload})
    dead = []
    with _sse_lock:
        for q in _sse_clients:
            try:
                q.put_nowait(data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


# ── Shared state ──────────────────────────────────────────────────────────────
state = {
    "kafka_status": {"raw_flows": "connecting", "predictions": "connecting"},
    "kafka_raw":    [],   # last 50 raw flows (RAM only, for /api/kafka snapshot)
    "kafka_pred":   [],   # last 50 predictions
}
lock = threading.Lock()

# ── Write buffers (filled on detection, flushed to Mongo every FLUSH_INTERVAL s)
_alert_buffer:   list[dict] = []
_traffic_buffer: list[dict] = []
_buffer_lock = threading.Lock()

# In-RAM view of recent alerts (populated instantly + seeded from Mongo on boot)
_ram_alerts:  list[dict] = []   # newest first, capped at 200
_ram_traffic: list[dict] = []   # newest first, capped at 200
_ram_lock = threading.Lock()


def classify_severity(confidence: float) -> str:
    score = confidence * 100
    if score >= 80: return "CRITICAL"
    if score >= 60: return "HIGH"
    if score >= 40: return "MEDIUM"
    return "LOW"


# ── Seed RAM caches from MongoDB on startup ───────────────────────────────────
def _seed_ram_cache():
    """
    Pre-fill _ram_alerts / _ram_traffic from the last 200 persisted records
    so HTTP clients and SSE reconnects get history immediately on boot —
    without waiting for the first Kafka message or a Mongo flush.
    """
    global _ram_alerts, _ram_traffic
    try:
        alerts = list(
            alerts_col.find({}, {"_id": 0})
                      .sort("timestamp", DESCENDING)
                      .limit(200)
        )
        traffic = list(
            traffic_col.find({}, {"_id": 0})
                       .sort("timestamp", DESCENDING)
                       .limit(200)
        )
        with _ram_lock:
            _ram_alerts  = alerts
            _ram_traffic = traffic
        print(f"[boot] RAM seeded: {len(alerts)} alerts, {len(traffic)} normal flows")
    except Exception as e:
        print(f"[boot] RAM seed failed: {e}")

# Seed BEFORE any threads start so the first HTTP request sees history
_seed_ram_cache()


# ── Periodic batch-flush to MongoDB ──────────────────────────────────────────
def _flush_buffers():
    """
    Runs every FLUSH_INTERVAL seconds in its own daemon thread.
    Drains _alert_buffer and _traffic_buffer into MongoDB via bulk_write.
    Failures are re-queued so no events are silently dropped.
    """
    while True:
        time.sleep(FLUSH_INTERVAL)
        with _buffer_lock:
            alert_batch   = _alert_buffer.copy()
            traffic_batch = _traffic_buffer.copy()
            _alert_buffer.clear()
            _traffic_buffer.clear()

        flushed_alerts  = 0
        flushed_traffic = 0

        if alert_batch:
            try:
                ops = [InsertOne(doc) for doc in alert_batch]
                alerts_col.bulk_write(ops, ordered=False)
                flushed_alerts = len(alert_batch)
            except Exception as e:
                print(f"[flush] alerts bulk_write error: {e}")
                # Re-queue failed docs so they are not lost
                with _buffer_lock:
                    _alert_buffer.extend(alert_batch)

        if traffic_batch:
            try:
                ops = [InsertOne(doc) for doc in traffic_batch]
                traffic_col.bulk_write(ops, ordered=False)
                flushed_traffic = len(traffic_batch)
            except Exception as e:
                print(f"[flush] traffic bulk_write error: {e}")
                with _buffer_lock:
                    _traffic_buffer.extend(traffic_batch)

        if flushed_alerts or flushed_traffic:
            print(
                f"[flush] ✓ {flushed_alerts} alerts + "
                f"{flushed_traffic} normal flows → MongoDB"
            )
            _push_event("flush", {
                "alerts_saved":  flushed_alerts,
                "traffic_saved": flushed_traffic,
                "flushed_at":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })


# ── Kafka consumers ───────────────────────────────────────────────────────────
def consume_predictions():
    try:
        consumer = KafkaConsumer(
            "predictions",
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            group_id="dashboard_pred",
            consumer_timeout_ms=1000,
        )
        with lock:
            state["kafka_status"]["predictions"] = "connected"

        while True:
            for msg in consumer:
                data = msg.value
                ts   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                data["timestamp"] = ts

                with lock:
                    state["kafka_pred"].insert(0, data)
                    state["kafka_pred"] = state["kafka_pred"][:50]

                if data.get("label") == "Attack":
                    severity  = classify_severity(data.get("confidence", 0))
                    alert_doc = {
                        "timestamp":  ts,
                        "src_ip":     data.get("src_ip", "unknown"),
                        "label":      "Attack",
                        "confidence": data.get("confidence", 0),
                        "severity":   severity,
                    }

                    # ── STEP 1: display instantly via SSE ──────────────────
                    _push_event("alert", alert_doc)

                    # ── STEP 2: into RAM so /api/alerts responds instantly ──
                    with _ram_lock:
                        _ram_alerts.insert(0, alert_doc)
                        del _ram_alerts[200:]

                    # ── STEP 3: queue for batch write (Mongo, 20 s later) ──
                    with _buffer_lock:
                        _alert_buffer.append(alert_doc)

                else:
                    traffic_doc = {
                        "timestamp":  ts,
                        "src_ip":     data.get("src_ip", "unknown"),
                        "label":      "Normal",
                        "confidence": data.get("confidence", 0),
                    }

                    # ── STEP 1: display instantly via SSE ──────────────────
                    _push_event("traffic", traffic_doc)

                    # ── STEP 2: RAM cache ──────────────────────────────────
                    with _ram_lock:
                        _ram_traffic.insert(0, traffic_doc)
                        del _ram_traffic[200:]

                    # ── STEP 3: queue for batch write ──────────────────────
                    with _buffer_lock:
                        _traffic_buffer.append(traffic_doc)

    except Exception as e:
        with lock:
            state["kafka_status"]["predictions"] = f"error: {str(e)}"


def consume_raw_flows():
    try:
        consumer = KafkaConsumer(
            "raw_flows",
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            group_id="dashboard_raw",
            consumer_timeout_ms=1000,
        )
        with lock:
            state["kafka_status"]["raw_flows"] = "connected"

        while True:
            for msg in consumer:
                data = msg.value
                data["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with lock:
                    state["kafka_raw"].insert(0, data)
                    state["kafka_raw"] = state["kafka_raw"][:50]

                _push_event("raw_flow", data)

    except Exception as e:
        with lock:
            state["kafka_status"]["raw_flows"] = f"error: {str(e)}"


# ── SSE endpoint ──────────────────────────────────────────────────────────────
@app.route("/api/stream")
def stream():
    """
    Server-Sent Events endpoint — connect from React with:
        const es = new EventSource("http://localhost:5000/api/stream");
        es.onmessage = (e) => { const d = JSON.parse(e.data); ... };

    On (re)connect the endpoint replays the last 50 RAM alerts so the
    client is immediately up-to-date without a separate /api/alerts call.
    """
    client_q: queue.Queue = queue.Queue(maxsize=200)
    with _sse_lock:
        _sse_clients.append(client_q)

    def generate():
        try:
            # ── initial handshake ──────────────────────────────────────────
            yield "data: {\"type\": \"connected\"}\n\n"

            # ── replay recent RAM alerts so client is immediately current ──
            with _ram_lock:
                recent = list(_ram_alerts[:50])   # newest-first, up to 50
            for doc in reversed(recent):           # send oldest→newest order
                payload = json.dumps({"type": "alert_replay", **doc})
                yield f"data: {payload}\n\n"

            # ── live stream ────────────────────────────────────────────────
            while True:
                try:
                    msg = client_q.get(timeout=25)
                    yield f"data: {msg}\n\n"
                except queue.Empty:
                    yield "data: {\"type\": \"heartbeat\"}\n\n"
        finally:
            with _sse_lock:
                try:
                    _sse_clients.remove(client_q)
                except ValueError:
                    pass

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Stats ─────────────────────────────────────────────────────────────────────
@app.route("/api/stats")
def get_stats():
    persisted_alerts  = alerts_col.count_documents({})
    persisted_normal  = traffic_col.count_documents({})

    with _buffer_lock:
        pending_alerts  = len(_alert_buffer)
        pending_traffic = len(_traffic_buffer)

    total_alerts = persisted_alerts + pending_alerts
    total_normal = persisted_normal + pending_traffic

    with _ram_lock:
        ram_ips = {a["src_ip"] for a in _ram_alerts}
    persisted_ips = set(alerts_col.distinct("src_ip"))
    blacklisted   = len(persisted_ips | ram_ips)

    with lock:
        kafka_status = state["kafka_status"]

    return jsonify({
        "total_alerts":    total_alerts,
        "total_normal":    total_normal,
        "blacklisted":     blacklisted,
        "pending_alerts":  pending_alerts,
        "pending_traffic": pending_traffic,
        "kafka_status":    kafka_status,
        "flush_interval":  FLUSH_INTERVAL,
    })


# ── Alerts — RAM-first (instant), MongoDB for older records ──────────────────
@app.route("/api/alerts")
def get_alerts():
    limit    = int(request.args.get("limit",  200))
    skip     = int(request.args.get("skip",   0))
    severity = request.args.get("severity")

    with _ram_lock:
        ram = list(_ram_alerts)

    if severity:
        ram = [a for a in ram if a.get("severity") == severity.upper()]

    # RAM fully covers the requested window — no Mongo round-trip needed
    if skip + limit <= len(ram):
        return jsonify(ram[skip: skip + limit])

    # Supplement with older records from MongoDB
    mongo_query: dict = {}
    if severity:
        mongo_query["severity"] = severity.upper()
    if ram:
        mongo_query["timestamp"] = {"$lt": ram[-1]["timestamp"]}

    mongo_skip  = max(0, skip - len(ram))
    mongo_limit = limit - min(max(len(ram) - skip, 0), limit)

    mongo_alerts = list(
        alerts_col.find(mongo_query, {"_id": 0})
                  .sort("timestamp", DESCENDING)
                  .skip(mongo_skip)
                  .limit(mongo_limit)
    )

    combined = (ram[skip:] + mongo_alerts)[:limit]
    return jsonify(combined)


# ── Blacklist ─────────────────────────────────────────────────────────────────
@app.route("/api/blacklist")
def get_blacklist():
    # Merge persisted + pending buffer so the list is always current
    with _buffer_lock:
        pending = list(_alert_buffer)

    pipeline = [
        {"$group": {
            "_id":        "$src_ip",
            "count":      {"$sum": 1},
            "first_seen": {"$min": "$timestamp"},
            "last_seen":  {"$max": "$timestamp"},
        }},
        {"$sort": {"count": -1}},
        {"$project": {"_id": 0, "ip": "$_id", "count": 1, "first_seen": 1, "last_seen": 1}},
    ]
    persisted = {r["ip"]: r for r in alerts_col.aggregate(pipeline)}

    # Merge pending (not-yet-flushed) counts into the result
    for doc in pending:
        ip = doc.get("src_ip", "unknown")
        if ip in persisted:
            persisted[ip]["count"] += 1
            persisted[ip]["last_seen"] = max(persisted[ip]["last_seen"], doc["timestamp"])
        else:
            persisted[ip] = {
                "ip":         ip,
                "count":      1,
                "first_seen": doc["timestamp"],
                "last_seen":  doc["timestamp"],
            }

    result = sorted(persisted.values(), key=lambda x: x["count"], reverse=True)
    return jsonify(result)


# ── Kafka raw snapshot ────────────────────────────────────────────────────────
@app.route("/api/kafka")
def get_kafka():
    with lock:
        return jsonify({
            "raw_flows":   state["kafka_raw"],
            "predictions": state["kafka_pred"],
            "status":      state["kafka_status"],
        })


# ── Logs ──────────────────────────────────────────────────────────────────────
def parse_logs(limit=100):
    log_file = os.path.join("logs", "alerts.log")
    if not os.path.exists(log_file):
        return []
    entries = []
    pattern = re.compile(
        r"\[(.+?)\] Source IP: (.+?) \| Attack Type: (.+?) \| Severity: (.+?) \| Threat Score: (.+)"
    )
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines[-limit:]):
            m = pattern.match(line.strip())
            if m:
                entries.append({
                    "timestamp":    m.group(1),
                    "src_ip":       m.group(2),
                    "attack_type":  m.group(3),
                    "severity":     m.group(4),
                    "threat_score": float(m.group(5)),
                })
    except Exception:
        pass
    return entries


@app.route("/api/logs")
def get_logs():
    return jsonify(parse_logs(100))


# ── Models ────────────────────────────────────────────────────────────────────
def load_model_info():
    models = []
    model_dir = "models"
    model_files = {
        "Random Forest":  "rf_model.pkl",
        "SGD Classifier": "sgd_model.pkl",
        "Extra Trees":    "et_model.pkl",
    }
    for name, fname in model_files.items():
        path = os.path.join(model_dir, fname)
        info = {"name": name, "status": "not found", "params": {}}
        if os.path.exists(path):
            try:
                model = joblib.load(path)
                info["status"] = "loaded"
                info["params"] = {
                    k: str(v)
                    for k, v in model.get_params().items()
                    if k in [
                        "n_estimators", "max_depth", "min_samples_split",
                        "class_weight", "random_state", "loss",
                        "max_iter", "tol", "n_jobs"
                    ]
                }
                info["size_mb"] = round(os.path.getsize(path) / 1e6, 2)
            except Exception as e:
                info["status"] = f"error: {str(e)}"
        models.append(info)
    return models


@app.route("/api/models")
def get_models():
    return jsonify(load_model_info())


@app.route("/api/accuracy")
def get_accuracy():
    return jsonify({
        "ensemble": {
            "accuracy":  0.9938,
            "f1_score":  0.9736,
            "roc_auc":   0.9773,
            "precision": 0.99,
            "recall":    0.96,
        },
        "confusion_matrix": {"tn": 339306, "fp": 343, "fn": 2060, "tp": 44337},
        "individual": [
            {"name": "Random Forest",  "role": "Ensemble member", "weight": "1/3 vote"},
            {"name": "SGD Classifier", "role": "Ensemble member", "weight": "1/3 vote"},
            {"name": "Extra Trees",    "role": "Ensemble member", "weight": "1/3 vote"},
        ],
        "voting": "Strict — all 3 must agree for Attack",
    })


# ── MongoDB stats ─────────────────────────────────────────────────────────────
@app.route("/api/db/stats")
def get_db_stats():
    total_attacks  = alerts_col.count_documents({})
    total_normal   = traffic_col.count_documents({})
    total_sessions = sessions_col.count_documents({})

    recent_attacks = list(
        alerts_col.find({}, {"_id": 0}).sort("timestamp", DESCENDING).limit(10)
    )
    return jsonify({
        "total_attacks_stored":  total_attacks,
        "total_normal_stored":   total_normal,
        "total_sessions":        total_sessions,
        "recent_attacks":        recent_attacks,
    })


# ── Session routes ────────────────────────────────────────────────────────────
@app.route("/api/session/load", methods=["POST"])
def load_session():
    data       = request.json
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "no session_id"}), 400

    session = sessions_col.find_one({"session_id": session_id})
    if not session:
        sessions_col.insert_one({
            "session_id":  session_id,
            "created_at":  datetime.now().isoformat(),
            "last_seen":   datetime.now().isoformat(),
            "visit_count": 1,
        })
        return jsonify({"new": True, "visit_count": 1})

    sessions_col.update_one(
        {"session_id": session_id},
        {"$set": {"last_seen": datetime.now().isoformat()}, "$inc": {"visit_count": 1}},
    )
    return jsonify({
        "new":         False,
        "visit_count": session.get("visit_count", 1) + 1,
        "created_at":  session.get("created_at"),
        "last_seen":   session.get("last_seen"),
    })


@app.route("/api/session/history", methods=["GET"])
def get_session_history():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"alerts": [], "normal": [], "stats": {}})

    past_attacks = list(
        alerts_col.find({"session_id": session_id}, {"_id": 0})
                  .sort("timestamp", DESCENDING).limit(200)
    )
    past_normal = list(
        traffic_col.find({"session_id": session_id}, {"_id": 0})
                   .sort("timestamp", DESCENDING).limit(100)
    )
    session = sessions_col.find_one({"session_id": session_id}, {"_id": 0})

    return jsonify({
        "alerts":  past_attacks,
        "normal":  past_normal,
        "session": session or {},
        "stats": {
            "total_attacks": len(past_attacks),
            "total_normal":  len(past_normal),
        },
    })


@app.route("/api/session/save_alert", methods=["POST"])
def save_alert():
    data       = request.json
    session_id = data.get("session_id")
    if not session_id:
        return jsonify({"error": "no session_id"}), 400

    alerts_col.insert_one({
        "session_id": session_id,
        "timestamp":  datetime.now().isoformat(),
        "src_ip":     data.get("src_ip"),
        "label":      data.get("label"),
        "severity":   data.get("severity"),
        "confidence": data.get("confidence"),
    })
    return jsonify({"ok": True})


# ── Start ─────────────────────────────────────────────────────────────────────
threading.Thread(target=consume_predictions, daemon=True).start()
threading.Thread(target=consume_raw_flows,   daemon=True).start()
threading.Thread(target=_flush_buffers,      daemon=True).start()

if __name__ == "__main__":
    print(f"HIDS Dashboard running at http://localhost:{FLASK_PORT}")
    print(f"MongoDB: {MONGO_URL} → {MONGO_DB}")
    app.run(debug=False, port=FLASK_PORT, threaded=True)