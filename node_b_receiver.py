# ============================================================
#  AKSYN CODING CHALLENGE - NODE B (RECEIVER)
#  Receives UDP audio packets, plays in real-time + saves file
#
#  Install: pip install pyaudio
#  Run:     python node_b_receiver.py
#  Start this BEFORE node_a_sender.py
# ============================================================

import socket
import pyaudio
import struct
import time
import wave
import threading
import datetime
import os

# ── Configuration ────────────────────────────────────────────
LISTEN_PORT   = 5005
CHUNK         = 1024
FORMAT        = pyaudio.paInt16
CHANNELS      = 1
RATE          = 44100

# Packet header format (must match Node A)
HEADER_FORMAT = '!IQI'
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)

# Output file
timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
OUTPUT_FILE   = f"received_audio_{timestamp_str}.wav"

# ── Delay Measurement ────────────────────────────────────────
delay_measurements = []

# ── Stats ────────────────────────────────────────────────────
stats = {
    'packets_received': 0,
    'packets_lost': 0,
    'bytes_received': 0,
    'last_seq': -1,
    'start_time': None,
    'min_delay': float('inf'),
    'max_delay': 0,
    'total_delay': 0
}

def parse_packet(data):
    """Parse header and audio data from packet"""
    if len(data) < HEADER_SIZE:
        return None, None, None
    header = data[:HEADER_SIZE]
    audio  = data[HEADER_SIZE:]
    seq_num, timestamp_ms, chunk_size = struct.unpack(HEADER_FORMAT, header)
    return seq_num, timestamp_ms, audio

def measure_delay(sent_timestamp_ms):
    """Calculate one-way delay (requires clocks to be synced)"""
    recv_time_ms = int(time.time() * 1000)
    delay = recv_time_ms - sent_timestamp_ms
    return delay

def print_stats():
    """Print receiving statistics every 5 seconds"""
    while True:
        time.sleep(5)
        if stats['packets_received'] == 0:
            continue
        elapsed = time.time() - stats['start_time']
        pps = stats['packets_received'] / elapsed
        loss_rate = (stats['packets_lost'] / max(1, stats['packets_received'] + stats['packets_lost'])) * 100
        avg_delay = stats['total_delay'] / stats['packets_received'] if stats['packets_received'] > 0 else 0

        print(f"\n[STATS] ─────────────────────────────────")
        print(f"  Received:   {stats['packets_received']} packets")
        print(f"  Lost:       {stats['packets_lost']} packets ({loss_rate:.1f}% loss)")
        print(f"  Rate:       {pps:.1f} pkt/s")
        print(f"  Delay avg:  {avg_delay:.1f} ms")
        print(f"  Delay min:  {stats['min_delay']:.1f} ms")
        print(f"  Delay max:  {stats['max_delay']:.1f} ms")
        print(f"  Runtime:    {elapsed:.0f}s")
        print(f"[STATS] ─────────────────────────────────\n")

def main():
    print("=" * 55)
    print("   AKSYN AUDIO PIPELINE - NODE B (RECEIVER)")
    print("=" * 55)
    print(f"[CONFIG] Listening on port: {LISTEN_PORT}")
    print(f"[CONFIG] Sample rate:       {RATE} Hz")
    print(f"[CONFIG] Output file:       {OUTPUT_FILE}")
    print(f"[CONFIG] Protocol:          UDP")
    print()

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Show available output devices
    print("[DEVICES] Available audio output devices:")
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        if dev['maxOutputChannels'] > 0:
            print(f"  [{i}] {dev['name']}")

    dev_index = input("\nEnter output device index (or press Enter for default): ").strip()
    dev_index = int(dev_index) if dev_index else None

    # Open playback stream
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        output=True,
        output_device_index=dev_index,
        frames_per_buffer=CHUNK
    )

    # UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
    sock.bind(('0.0.0.0', LISTEN_PORT))
    sock.settimeout(1.0)

    # WAV file for saving
    wav_file = wave.open(OUTPUT_FILE, 'wb')
    wav_file.setnchannels(CHANNELS)
    wav_file.setsampwidth(p.get_sample_size(FORMAT))
    wav_file.setframerate(RATE)

    print(f"\n[READY] Listening for audio on port {LISTEN_PORT}...")
    print("[INFO] Start node_a_sender.py now!")
    print("[INFO] Press Ctrl+C to stop and save\n")

    # Start stats thread
    stats['start_time'] = time.time()
    t = threading.Thread(target=print_stats, daemon=True)
    t.start()

    try:
        while True:
            try:
                data, addr = sock.recvfrom(65536)
            except socket.timeout:
                continue

            # First packet — announce sender
            if stats['packets_received'] == 0:
                print(f"[CONNECTED] Receiving audio from {addr[0]}:{addr[1]}")

            # Parse packet
            seq_num, timestamp_ms, audio_data = parse_packet(data)
            if audio_data is None:
                continue

            # Detect lost packets
            if stats['last_seq'] >= 0:
                expected = stats['last_seq'] + 1
                if seq_num > expected:
                    lost = seq_num - expected
                    stats['packets_lost'] += lost
                    print(f"[WARN] {lost} packet(s) lost (seq {expected}→{seq_num})")

            stats['last_seq'] = seq_num
            stats['packets_received'] += 1
            stats['bytes_received'] += len(data)

            # Measure delay
            delay = measure_delay(timestamp_ms)
            if 0 < delay < 5000:  # Sanity check (ignore clock drift >5s)
                stats['total_delay'] += delay
                stats['min_delay'] = min(stats['min_delay'], delay)
                stats['max_delay'] = max(stats['max_delay'], delay)
                delay_measurements.append(delay)

            # Play audio in real-time
            stream.write(audio_data)

            # Save to WAV file
            wav_file.writeframes(audio_data)

    except KeyboardInterrupt:
        print(f"\n[STOPPED] Received {stats['packets_received']} packets.")

        # Final delay report
        if delay_measurements:
            avg = sum(delay_measurements) / len(delay_measurements)
            print(f"\n[DELAY REPORT] ──────────────────────────")
            print(f"  Estimated delay:  60-80 ms")
            print(f"  Measured avg:     {avg:.1f} ms")
            print(f"  Measured min:     {min(delay_measurements):.1f} ms")
            print(f"  Measured max:     {max(delay_measurements):.1f} ms")
            print(f"  Packets received: {stats['packets_received']}")
            print(f"  Packets lost:     {stats['packets_lost']}")
            loss = (stats['packets_lost'] / max(1, stats['packets_received'] + stats['packets_lost'])) * 100
            print(f"  Packet loss:      {loss:.1f}%")
            print(f"  Difference (est vs actual): {avg - 70:.1f} ms")
            print(f"[DELAY REPORT] ──────────────────────────")

        print(f"\n[SAVED] Audio saved to: {OUTPUT_FILE}")

    finally:
        stream.stop_stream()
        stream.close()
        wav_file.close()
        p.terminate()
        sock.close()

        if os.path.exists(OUTPUT_FILE):
            size = os.path.getsize(OUTPUT_FILE)
            print(f"[FILE] {OUTPUT_FILE} ({size} bytes)")

if __name__ == "__main__":
    main()
