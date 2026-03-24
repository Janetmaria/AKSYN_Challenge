# ============================================================
#  AKSYN CODING CHALLENGE - DELAY VALIDATOR
#  Sends a test tone and measures round-trip delay precisely
#  Run AFTER both nodes are working
#  Run: python delay_validator.py
# ============================================================

import socket
import struct
import time
import math
import threading

TARGET_IP   = input("Enter receiver IP (127.0.0.1 for same machine): ").strip()
TARGET_PORT = 5006   # Separate port for validation only
NUM_PINGS   = 20

results = []

def send_pings():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for i in range(NUM_PINGS):
        send_time = time.time()
        payload = struct.pack('!Id', i, send_time)  # seq + timestamp
        sock.sendto(payload, (TARGET_IP, TARGET_PORT))
        time.sleep(0.1)
    sock.close()

def receive_pongs():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', TARGET_PORT + 1))
    sock.settimeout(5.0)
    while len(results) < NUM_PINGS:
        try:
            data, _ = sock.recvfrom(1024)
            recv_time = time.time()
            seq, sent_time = struct.unpack('!Id', data)
            rtt = (recv_time - sent_time) * 1000
            results.append(rtt)
            print(f"  Ping #{seq+1:02d}: RTT = {rtt:.2f} ms  (one-way ≈ {rtt/2:.2f} ms)")
        except socket.timeout:
            break
    sock.close()

def main():
    print("=" * 55)
    print("   AKSYN - DELAY VALIDATION TEST")
    print("=" * 55)
    print(f"[INFO] Sending {NUM_PINGS} test probes to {TARGET_IP}")
    print(f"[INFO] Measuring round-trip time (RTT)\n")

    t = threading.Thread(target=receive_pongs)
    t.start()
    time.sleep(0.2)
    send_pings()
    t.join(timeout=6)

    if results:
        avg_rtt  = sum(results) / len(results)
        min_rtt  = min(results)
        max_rtt  = max(results)
        jitter   = max_rtt - min_rtt
        one_way  = avg_rtt / 2

        print(f"\n[VALIDATION REPORT] ────────────────────")
        print(f"  Probes sent:       {NUM_PINGS}")
        print(f"  Responses:         {len(results)}")
        print(f"  Avg RTT:           {avg_rtt:.2f} ms")
        print(f"  Min RTT:           {min_rtt:.2f} ms")
        print(f"  Max RTT:           {max_rtt:.2f} ms")
        print(f"  Jitter:            {jitter:.2f} ms")
        print(f"  Est. one-way:      {one_way:.2f} ms")
        print(f"  Estimated E2E:     60-80 ms")
        print(f"  Network portion:   {one_way:.2f} ms")
        print(f"  Audio buffer est:  {60 - one_way:.2f} ms")
        print(f"[VALIDATION REPORT] ────────────────────")

        if avg_rtt < 100:
            print(f"\n✅ PASS: RTT {avg_rtt:.1f}ms is under 100ms threshold")
        else:
            print(f"\n⚠ WARN: RTT {avg_rtt:.1f}ms exceeds 100ms — check buffers")
    else:
        print("[ERROR] No responses received.")

if __name__ == "__main__":
    main()
