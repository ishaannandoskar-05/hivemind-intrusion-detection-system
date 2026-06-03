import sys
sys.stdout.reconfigure(encoding='utf-8')

from agents.traffic_collector import TrafficCollectorAgent
from agents.preprocessing_agent import PreprocessingAgent
from agents.detection_agent import DetectionAgent

important_columns = [
    "Flow Duration",
    "Total Fwd Packets",
    "Total Backward Packets",
    "Flow Bytes/s",
    "Flow Packets/s",
    "Average Packet Size",
    "Packet Size Variance",
    "Average IAT",
    "SYN Flag Count",
    "ACK Flag Count",
    "FIN Flag Count",
    "RST Flag Count",
    "Fwd_Bwd_Ratio",
    "Bytes_per_packet",
    "SYN_ACK_Ratio",
    "Label"
]

collector = TrafficCollectorAgent("dataset/", important_columns)
df = collector.collect()

print("Dataset shape:", df.shape)
print("Label distribution:")
print(df["Label"].value_counts())

preprocessor = PreprocessingAgent()
X_train, X_test, y_train, y_test, class_weight_dict = preprocessor.process(df)

detector = DetectionAgent()
detector.train(X_train, y_train, class_weight_dict)
detector.evaluate(X_test, y_test)