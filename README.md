# AKSYN Audio Pipeline — Real-Time Audio Transfer over Network

A software prototype that transfers live audio over a network in near real-time, with measurable and verifiable end-to-end delay.

## Problem Statement
Transfer real-time audio from a source node (Node A) to a receiver node (Node B) over a network, estimate expected delay, measure actual delay, and explain the difference.

## Architecture
```
Node A (Sender)                         Node B (Receiver)
──────────────────                      ──────────────────
Microphone input                        UDP Socket listener
    ↓                                       ↓
PyAudio capture                         Packet parser
(1024 frames @ 44100Hz)                     ↓
    ↓                                   ┌───────────────┐
Custom packet builder                   │ Real-time     │
[seq|timestamp|size|audio]              │ playback      │
    ↓                                   │ + WAV save    │
UDP sendto() → Port 5005                └───────────────┘
                                            ↓
                                        Delay measurement
                                        Loss detection
```

## Packet Structure
```
┌────────────┬────────────────┬────────────┬──────────────────┐
│  seq_num   │  timestamp_ms  │ chunk_size │   audio_data     │
│  (4 bytes) │   (8 bytes)    │  (4 bytes) │  (~2048 bytes)   │
└────────────┴────────────────┴────────────┴──────────────────┘
```

## Results Achieved
| Metric | Estimated | Actual |
|--------|-----------|--------|
| E2E Delay (avg) | 60-80ms | 1.1ms (loopback) |
| Packet Loss | <5% | 0.0% |
| Packets Transferred | - | 3258 |
| Audio Saved | - | 6.67MB WAV |
| Bitrate | - | ~710 kbps stable |

## Files
| File | Description |
|------|-------------|
| `node_a_sender.py` | Node A — captures mic audio, sends via UDP |
| `node_b_receiver.py` | Node B — receives audio, plays + saves WAV |
| `delay_validator.py` | Measures round-trip network delay |
| `requirements_doc.md` | Full engineering document |

## How to Run

### Install dependencies
```bash
pip install pyaudio
```
If pyaudio fails on Windows:
```bash
pip install pipwin
pipwin install pyaudio
```

### Step 1 — Start Node B first (receiver)
```bash
python node_b_receiver.py
# Enter: 127.0.0.1 for same machine, or receiver IP for network
# Press Enter for default audio output device
```

### Step 2 — Start Node A (sender)
```bash
python node_a_sender.py
# Enter: 127.0.0.1 for same machine, or Node B IP for network
# Press Enter for default microphone
```

### Step 3 — Speak into microphone
You will hear your voice played back in real-time through speakers.
A WAV file is automatically saved to the AKSYN_Challenge folder.

### Step 4 — Stop and view results
Press Ctrl+C on both terminals.
Node B will print the full delay report.

### Step 5 — Validate delay (optional)
```bash
python delay_validator.py
```

## Engineering Decisions

### Why UDP over TCP?
TCP guarantees delivery but retransmits lost packets, causing variable delay spikes.
For real-time audio, a slightly degraded frame is better than a late frame.
This matches industry practice — VoIP and WebRTC both use UDP.

### Delay Model (Pre-Implementation Estimate)
| Component | Value |
|-----------|-------|
| Audio capture frame (1024/44100) | 23ms |
| PyAudio input buffer | 23ms |
| UDP transmission (LAN) | 1-3ms |
| Network jitter | 2-5ms |
| PyAudio output buffer | 23ms |
| **Total estimated** | **~72-77ms** |

### Why Actual < Estimated?
Loopback (127.0.0.1) bypasses the physical network entirely.
On real WiFi between two devices, the full 60-80ms estimate applies.
The loopback test validates the implementation is correct — the network is the variable.

## C++ Libraries Required (for production implementation)
| Library | Purpose |
|---------|---------|
| PortAudio | Cross-platform audio capture/playback |
| Boost.Asio | Async UDP networking |
| libsndfile | WAV/FLAC file saving |
| nlohmann/json | Packet metadata serialization |

## Author
Built for AKSYN Internship Coding Challenge — Round 1 (March 24, 2026)
