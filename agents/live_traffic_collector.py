from scapy.all import sniff, IP, TCP, UDP
from kafka import KafkaProducer
import time
import numpy as np
import json
import threading


class LiveTrafficCollector:

    def __init__(self, flow_timeout=10, kafka_broker="localhost:9092"):
        self.flows = {}
        self.flow_timeout = flow_timeout
        self.lock = threading.Lock()
        self.producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda v: json.dumps(v).encode("utf-8")
        )
        print("Kafka producer connected.")

    def get_flow_key(self, packet):
        if IP in packet:
            src = packet[IP].src
            dst = packet[IP].dst
            proto = packet[IP].proto
            if TCP in packet:
                sport = packet[TCP].sport
                dport = packet[TCP].dport
            elif UDP in packet:
                sport = packet[UDP].sport
                dport = packet[UDP].dport
            else:
                sport = 0
                dport = 0
            return (src, dst, sport, dport, proto)
        return None

    def process_packet(self, packet):
        flow_key = self.get_flow_key(packet)
        if flow_key is None:
            return

        reverse_key = (
            flow_key[1], flow_key[0],
            flow_key[3], flow_key[2],
            flow_key[4]
        )

        timestamp = time.time()
        pkt_len = len(packet)

        with self.lock:
            if flow_key not in self.flows and reverse_key not in self.flows:
                self.flows[flow_key] = {
                    "timestamps": [],
                    "packet_sizes": [],
                    "fwd_packets": 0,
                    "bwd_packets": 0,
                    "fwd_bytes": 0,
                    "syn": 0, "ack": 0, "fin": 0, "rst": 0,
                    "start_time": timestamp
                }
                flow = self.flows[flow_key]
                direction = "fwd"
            else:
                if flow_key in self.flows:
                    flow = self.flows[flow_key]
                    direction = "fwd"
                else:
                    flow = self.flows[reverse_key]
                    direction = "bwd"

            flow["timestamps"].append(timestamp)
            flow["packet_sizes"].append(pkt_len)

            if direction == "fwd":
                flow["fwd_packets"] += 1
                flow["fwd_bytes"] += pkt_len
            else:
                flow["bwd_packets"] += 1

            if TCP in packet:
                flags = packet[TCP].flags
                if flags & 0x02: flow["syn"] += 1
                if flags & 0x10: flow["ack"] += 1
                if flags & 0x01: flow["fin"] += 1
                if flags & 0x04: flow["rst"] += 1

    def flush_expired_flows(self):
        # Runs in background thread every 5 seconds
        while True:
            time.sleep(5)
            current_time = time.time()
            with self.lock:
                expired = [
                    key for key, flow in self.flows.items()
                    if current_time - flow["start_time"] >= self.flow_timeout
                ]
                for key in expired:
                    flow = self.flows.pop(key)
                    features = self.extract_flow_features(key, flow)
                    if features:
                        self.producer.send("raw_flows", value=features)
                        self.producer.flush()
                        print(f"[COLLECTOR] Flushed flow: {key[0]} → {key[1]} ({len(flow['timestamps'])} packets)")

    def extract_flow_features(self, flow_key, flow):
        timestamps = flow["timestamps"]
        sizes = flow["packet_sizes"]

        if len(timestamps) < 2:
            return None

        duration = max(timestamps) - min(timestamps)
        total_packets = len(sizes)
        total_bytes = sum(sizes)

        bytes_per_sec = total_bytes / duration if duration > 0 else 0
        packets_per_sec = total_packets / duration if duration > 0 else 0

        avg_pkt_size = float(np.mean(sizes))
        pkt_size_var = float(np.var(sizes))

        iat = np.diff(sorted(timestamps))
        avg_iat = float(np.mean(iat)) if len(iat) > 0 else 0

        fwd_packets = flow["fwd_packets"]
        bwd_packets = flow["bwd_packets"]
        syn = flow["syn"]
        ack = flow["ack"]

        fwd_bwd_ratio  = fwd_packets / (bwd_packets + 1)
        bytes_per_packet = bytes_per_sec / (packets_per_sec + 1)
        syn_ack_ratio  = syn / (ack + 1)

        return {
            "src_ip": flow_key[0],
            "features": [
                duration, fwd_packets, bwd_packets,
                bytes_per_sec, packets_per_sec,
                avg_pkt_size, pkt_size_var, avg_iat,
                syn, ack, flow["fin"], flow["rst"],
                fwd_bwd_ratio, bytes_per_packet, syn_ack_ratio
            ]
        }

    def capture(self):
        print("Starting continuous capture — publishing to Kafka topic 'raw_flows'...")

        # Start background flush thread
        flush_thread = threading.Thread(target=self.flush_expired_flows, daemon=True)
        flush_thread.start()
        print("Flow flush thread started (every 5 seconds).")

        # Sniff forever
        sniff(prn=self.process_packet, store=False, iface="Wi-Fi")
