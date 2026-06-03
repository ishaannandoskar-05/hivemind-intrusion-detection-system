import sys
sys.stdout.reconfigure(encoding='utf-8')

from scapy.all import send, IP, TCP, UDP
import time
import random

TARGET = "192.168.0.102"

def port_scan():
    print("[*] Simulating Port Scan...")
    for port in range(1, 1000):
        send(IP(dst=TARGET)/TCP(dport=port, flags="S"), verbose=False)
    print("[+] Port scan done")

def ddos():
    print("[*] Simulating DDoS...")
    for i in range(2000):
        send(IP(dst=TARGET)/TCP(dport=80, flags="S"), verbose=False)
    print("[+] DDoS done")

def syn_flood():
    print("[*] Simulating SYN Flood...")
    for i in range(1000):
        sport = random.randint(1024, 65535)
        send(IP(dst=TARGET)/TCP(sport=sport, dport=443, flags="S"), verbose=False)
    print("[+] SYN flood done")

def ftp_bruteforce():
    print("[*] Simulating FTP Brute Force...")
    for i in range(500):
        send(IP(dst=TARGET)/TCP(dport=21, flags="S"), verbose=False)
        send(IP(dst=TARGET)/TCP(dport=21, flags="A"), verbose=False)
    print("[+] FTP brute force done")

def udp_flood():
    print("[*] Simulating UDP Flood...")
    for i in range(1000):
        dport = random.randint(1, 65535)
        send(IP(dst=TARGET)/UDP(dport=dport), verbose=False)
    print("[+] UDP flood done")

if __name__ == "__main__":
    print("=" * 40)
    print("  HIDS Attack Simulator")
    print("=" * 40)
    print("Target:", TARGET)
    print("Run this while live_main.py is active")
    print("Alerts appear after ~10 seconds (flow timeout)")
    print("=" * 40)

    port_scan()
    time.sleep(2)

    ddos()
    time.sleep(2)

    syn_flood()
    time.sleep(2)

    ftp_bruteforce()
    time.sleep(2)

    udp_flood()

    print("\n[✓] All attacks simulated.")
    print("[*] Wait 10-15 seconds for flows to expire and alerts to appear.")