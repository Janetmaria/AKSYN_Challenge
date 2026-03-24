# ============================================================
#  AKSYN CODING CHALLENGE - NODE A (SENDER)
#  Captures audio from microphone and sends over UDP
#  
#  Install: pip install pyaudio
#  Run:     python node_a_sender.py
# ============================================================

import socket
import pyaudio
import struct
import time
import threading
import datetime

# ── Configuration ────────────────────────────────────────────
RECEIVER_IP   = input("Enter Node B IP (or 127.0.0.1 for same machine): ").strip()
RECEIVER_PORT = 5005

# Audio parameters
CHUNK         = 1024       # Frames per buffer (~23ms at 44100Hz)
FORMAT        = pyaudio.paInt16
CHANNELS      = 1          # Mono (lower bandwidth)
RATE          = 44100      # 44.1kHz sample rate

# ── Packet Design ────────────────────────────────────────────
# Each UDP packet = [HEADER(16 bytes)] + [AUDIO_DATA]
# Header: | seq_num(4) | timestamp_ms(8) | chunk_size(4) |
HEADER_FORMAT = '!IQI'     # unsigned int, unsigned long long, unsigned int
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)

# ── Stats ────────────────────────────────────────────────────
stats = {
    'packets_sent': 0,
    'bytes_sent': 0,
    'start_time': None
}

def build_packet(seq_num, audio_data):
    """Build a structured audio packet with header"""
    timestamp_ms = int(time.time() * 1000)  # Current time in milliseconds
    chunk_size = len(audio_data)
    header = struct.pack(HEADER_FORMAT, seq_num, timestamp_ms, chunk_size)
    return header + audio_data

def print_stats():
    """Print sending statistics every 5 seconds"""
    while True:
        time.sleep(5)
        elapsed = time.time() - stats['start_time'] if stats['start_time'] else 1
        pps = stats['packets_sent'] / elapsed
        kbps = (stats['bytes_sent'] * 8) / (elapsed * 1000)
        print(f"[STATS] Sent: {stats['packets_sent']} pkts | "
              f"{pps:.1f} pkt/s | {kbps:.1f} kbps | "
              f"Runtime: {elapsed:.0f}s")

def main():
    print("=" * 55)
    print("   AKSYN AUDIO PIPELINE - NODE A (SENDER)")
    print("=" * 55)
    print(f"[CONFIG] Target:    {RECEIVER_IP}:{RECEIVER_PORT}")
    print(f"[CONFIG] Sample rate: {RATE} Hz")
    print(f"[CONFIG] Chunk size:  {CHUNK} frames")
    print(f"[CONFIG] Frame dur:   {(CHUNK/RATE)*1000:.1f} ms")
    print(f"[CONFIG] Protocol:    UDP (low latency)")
    print(f"[CONFIG] Packet header: {HEADER_SIZE} bytes")
    print(f"[ESTIMATE] Expected E2E delay: ~60-80ms")
    print()

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Show available input devices
    print("[DEVICES] Available audio input devices:")
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxInputChannels'] > 0:
            print(f"  [{i}] {dev['name']}")

    dev_index = input("\nEnter device index (or press Enter for default): ").strip()
    dev_index = int(dev_index) if dev_index else None

    # Open audio stream
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        input_device_index=dev_index,
        frames_per_buffer=CHUNK
    )

    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)

    print(f"\n[LIVE] Streaming audio to {RECEIVER_IP}:{RECEIVER_PORT}")
    print("[INFO] Press Ctrl+C to stop\n")

    # Start stats thread
    stats['start_time'] = time.time()
    t = threading.Thread(target=print_stats, daemon=True)
    t.start()

    seq_num = 0
    try:
        while True:
            # Capture audio frame
            audio_data = stream.read(CHUNK, exception_on_overflow=False)

            # Build and send packet
            packet = build_packet(seq_num, audio_data)
            sock.sendto(packet, (RECEIVER_IP, RECEIVER_PORT))

            stats['packets_sent'] += 1
            stats['bytes_sent'] += len(packet)
            seq_num += 1

    except KeyboardInterrupt:
        print(f"\n[STOPPED] Sent {stats['packets_sent']} packets total.")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        sock.close()

if __name__ == "__main__":
    main()
