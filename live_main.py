import sys
import multiprocessing
sys.stdout.reconfigure(encoding='utf-8')

from agents.live_traffic_collector import LiveTrafficCollector
from agents.live_detector import LiveDetector
from agents.alert_agent import AlertAgent


def run_collector():
    collector = LiveTrafficCollector()
    collector.capture()


def run_detector():
    detector = LiveDetector()
    detector.run()


def run_alerter():
    alerter = AlertAgent()
    alerter.run()


if __name__ == "__main__":

    processes = [
        multiprocessing.Process(target=run_collector, name="Collector"),
        multiprocessing.Process(target=run_detector, name="Detector"),
        multiprocessing.Process(target=run_alerter,  name="Alerter"),
    ]

    for p in processes:
        p.daemon = True
        p.start()
        print(f"[MAIN] Started {p.name}")

    for p in processes:
        p.join()