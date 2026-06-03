from kafka import KafkaProducer
import json
import time
import random

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8")
)

src_ips = [
    "192.168.0.105",
    "10.0.0.45",
    "172.16.0.22",
    "192.168.1.200",
    "45.33.32.156",
]

# 🔹 Generate confidence based on desired severity
def generate_confidence(severity):
    if severity == "LOW":
        return round(random.uniform(0.30, 0.55), 4)
    elif severity == "MEDIUM":
        return round(random.uniform(0.55, 0.75), 4)
    elif severity == "HIGH":
        return round(random.uniform(0.75, 0.90), 4)
    else:  # CRITICAL
        return round(random.uniform(0.90, 0.99), 4)

# 🔹 Inject prediction
def inject_prediction(src_ip, severity):
    confidence = generate_confidence(severity)

    msg = {
        "src_ip": src_ip,
        "label": "Attack",
        "confidence": confidence
    }

    producer.send("predictions", value=msg)

# 🔹 Inject raw flow
def inject_raw_flow(src_ip):
    msg = {
        "src_ip": src_ip,
        "features": [
            random.uniform(0.1, 10.0),
            random.randint(100, 5000),
            random.randint(10, 500),
            random.uniform(1000, 90000),
            random.uniform(10, 500),
            random.uniform(40, 1500),
            random.uniform(0, 5000),
            random.uniform(0, 0.5),
            random.randint(0, 100),
            random.randint(0, 100),
            random.randint(0, 10),
            random.randint(0, 10),
            random.uniform(0.1, 10.0),
            random.uniform(0.1, 500.0),
            random.uniform(0.0, 5.0),
        ]
    }

    producer.send("raw_flows", value=msg)

# 🔹 Main
if __name__ == "__main__":
    print("Injecting 500+ attacks with REAL severity variation...")
    print("=" * 50)

    TOTAL_EVENTS = 500

    # Balanced distribution
    severity_distribution = (
        ["LOW"] * 125 +
        ["MEDIUM"] * 125 +
        ["HIGH"] * 125 +
        ["CRITICAL"] * 125
    )

    random.shuffle(severity_distribution)

    for i in range(TOTAL_EVENTS):
        ip = random.choice(src_ips)
        severity = severity_distribution[i]

        inject_prediction(ip, severity)
        inject_raw_flow(ip)

        if i % 50 == 0:
            producer.flush()
            print(f"Injected {i} events...")

    producer.flush()

    print("\n[✓] Done — Proper mixed severity generated")