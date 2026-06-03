import os
import datetime
import json
from kafka import KafkaConsumer
from agents.attack_intelligence_agent import AttackIntelligenceAgent


class AlertAgent:

    def __init__(self, log_dir="logs", kafka_broker="localhost:9092"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "alerts.log")
        self.alert_counter = 0
        self.intel = AttackIntelligenceAgent()

        self.consumer = KafkaConsumer(
            "predictions",
            bootstrap_servers=kafka_broker,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            group_id="alert_group"
        )

        print("AlertAgent connected to Kafka topic 'predictions'.")

    def calculate_threat_score(self, confidence):
        base_score = confidence * 100
        repetition_bonus = min(self.alert_counter * 5, 30)
        return min(base_score + repetition_bonus, 100)

    def classify_severity(self, threat_score):
        if threat_score >= 80:
            return "CRITICAL"
        elif threat_score >= 60:
            return "HIGH"
        elif threat_score >= 40:
            return "MEDIUM"
        else:
            return "LOW"

    def log_alert(self, timestamp, src_ip, label, severity, threat_score):
        log_entry = (
            f"[{timestamp}] "
            f"Source IP: {src_ip} | "
            f"Attack Type: {label} | "
            f"Severity: {severity} | "
            f"Threat Score: {threat_score:.2f}\n"
        )
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)

    def run(self):
        print("AlertAgent listening on 'predictions'...")
        for message in self.consumer:
            data = message.value
            src_ip = data["src_ip"]
            label = data["label"]
            confidence = data["confidence"]

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            self.intel.update_activity(src_ip, label)
            severity_intel = self.intel.evaluate_threat(src_ip)
            blacklisted = self.intel.update_blacklist(src_ip)

            if blacklisted:
                print(f"[SECURITY] IP {src_ip} added to blacklist")

            if label != "Normal":
                self.alert_counter += 1
                threat_score = self.calculate_threat_score(confidence)
                severity = self.classify_severity(threat_score)

                print("\n==============================")
                print("        SECURITY ALERT")
                print("==============================")
                print("Time       :", timestamp)
                print("Source IP  :", src_ip)
                print("Label      :", label)
                print("Confidence :", round(confidence, 4))
                print("Threat Score:", round(threat_score, 2))
                print("Severity   :", severity)
                print("Intel Sev  :", severity_intel)
                if blacklisted:
                    print("STATUS     : IP BLACKLISTED")

                self.log_alert(timestamp, src_ip, label, severity, threat_score)
            else:
                print(f"[{timestamp}] Normal traffic from {src_ip}")