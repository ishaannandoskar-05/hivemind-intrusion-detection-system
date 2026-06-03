import joblib
import numpy as np
import json
from kafka import KafkaConsumer, KafkaProducer


class LiveDetector:

    def __init__(self, model_dir="models", kafka_broker="localhost:9092"):
        self.rf_model = joblib.load(f"{model_dir}/rf_model.pkl")
        self.sgd_model = joblib.load(f"{model_dir}/sgd_model.pkl")
        self.et_model = joblib.load(f"{model_dir}/et_model.pkl")
        self.scaler = joblib.load(f"{model_dir}/scaler.pkl")

        self.consumer = KafkaConsumer(
            "raw_flows",
            bootstrap_servers=kafka_broker,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            group_id="detector_group"
        )

        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )

        print("LiveDetector connected to Kafka.")
        print("Scaler expects features:", self.scaler.n_features_in_)

    def hivemind_vote(self, rf_pred, sgd_pred, et_pred):
        # All three are single scalars here — sum directly
        votes = int(rf_pred) + int(sgd_pred) + int(et_pred)
        return 1 if votes == 3 else 0

    def predict_one(self, features):
        features = np.array(features).reshape(1, -1)
        features_scaled = self.scaler.transform(features)

        rf_pred = self.rf_model.predict(features_scaled)[0]
        sgd_pred = self.sgd_model.predict(features_scaled)[0]
        et_pred = self.et_model.predict(features_scaled)[0]

        final_pred = self.hivemind_vote(rf_pred, sgd_pred, et_pred)
        probabilities = self.rf_model.predict_proba(features_scaled)

        label = "Attack" if final_pred == 1 else "Normal"
        confidence = float(np.max(probabilities))

        return label, confidence

    def run(self):
        print("Detector listening on 'raw_flows'...")
        for message in self.consumer:
            data = message.value
            src_ip = data["src_ip"]
            features = data["features"]

            label, confidence = self.predict_one(features)

            result = {
                "src_ip": src_ip,
                "label": label,
                "confidence": confidence
            }

            self.producer.send("predictions", value=result)
            self.producer.flush()
            print(f"[DETECTOR] {src_ip} → {label} (confidence: {confidence:.4f})")