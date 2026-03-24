# AKSYN Audio Pipeline — Engineering Document

## 1. Requirement Decomposition

### Customer Goal
Transfer live audio over a network in near real-time with measurable, verifiable delay.

### Sub-Requirements (SR)

| ID | Sub-Requirement | Why It Matters |
|----|----------------|----------------|
| SR1 | Audio must be captured and transmitted continuously without gaps | Gaps = unusable for safety-critical environments |
| SR2 | End-to-end delay must be < 100ms | Human perception threshold for audio sync |
| SR3 | Packet loss must be < 5% | >5% causes audible artifacts |
| SR4 | Received audio must be saved to disk | Audit trail for safety-critical systems |
| SR5 | System must handle network jitter gracefully | Real networks are not ideal |
| SR6 | Delay must be estimated BEFORE implementation | Engineering discipline, not trial and error |
| SR7 | Actual delay must be measured and compared to estimate | Validation closes the engineering loop |

---

## 2. Delay Model (Pre-Implementation Estimate)

### Delay Contributors

| Component | Formula | Value |
|-----------|---------|-------|
| Audio capture frame | CHUNK/RATE = 1024/44100 | ~23 ms |
| PyAudio input buffer | 1 extra frame | ~23 ms |
| UDP transmission (LAN) | packet_size / bandwidth | ~1-3 ms |
| Network queuing jitter | measured empirically | ~2-5 ms |
| PyAudio output buffer | 1 extra frame | ~23 ms |
| **Total estimated E2E** | sum of above | **~72-77 ms** |

### Key Design Decision: UDP over TCP
- TCP guarantees delivery but retransmits lost packets → variable delay spikes
- UDP allows packet loss but maintains consistent low latency
- For real-time audio: a slightly degraded frame is better than a late frame
- This matches industry practice (VoIP, WebRTC all use UDP)

---

## 3. System Architecture

```
┌─────────────────────────────┐         ┌─────────────────────────────┐
│         NODE A              │         │         NODE B              │
│      (Sender)               │         │      (Receiver)             │
│                             │  UDP    │                             │
│  Microphone                 │ ──────► │  UDP Socket                 │
│      ↓                      │         │      ↓                      │
│  PyAudio capture            │         │  Packet parser              │
│  (CHUNK=1024, 44100Hz)      │         │      ↓                      │
│      ↓                      │         │  ┌──────────┬───────────┐   │
│  Packet builder             │         │  │ Playback │  WAV Save │   │
│  [seq|timestamp|size|audio] │         │  │(real-time│  (to disk)│   │
│      ↓                      │         │  └──────────┴───────────┘   │
│  UDP socket sendto()        │         │      ↓                      │
│  Port 5005                  │         │  Delay measurement          │
│                             │         │  Loss detection             │
└─────────────────────────────┘         └─────────────────────────────┘
```

### Packet Structure (16 bytes header + audio payload)
```
┌────────────┬────────────────┬────────────┬──────────────────┐
│  seq_num   │  timestamp_ms  │ chunk_size │   audio_data     │
│  (4 bytes) │   (8 bytes)    │  (4 bytes) │  (2048 bytes)    │
└────────────┴────────────────┴────────────┴──────────────────┘
```
- **seq_num**: detects lost/reordered packets
- **timestamp_ms**: enables one-way delay measurement
- **chunk_size**: receiver knows exact payload size

---

## 4. Third-Party C++ Libraries Required

| Library | Purpose | Why |
|---------|---------|-----|
| **PortAudio** | Audio capture/playback | Cross-platform, industry standard |
| **libsndfile** | Save audio to WAV/FLAC | Reliable file I/O for audio |
| **Boost.Asio** | Async UDP networking | High-performance socket I/O |
| **nlohmann/json** | Config/status messages | Easy packet metadata serialization |

---

## 5. Validation Plan

| Test | Method | Pass Criteria |
|------|--------|--------------|
| Audio transfer working | Play known tone at Node A, verify at Node B | Audible + saved to file |
| Delay measurement | timestamp diff (send→recv) | Avg < 100ms |
| Packet loss | seq_num gap detection | < 5% loss |
| Jitter handling | max_delay - min_delay | < 30ms jitter |
| Network variation | Stress test with large file transfer running | Still < 150ms under load |

---

## 6. Difference: Estimated vs Actual Delay

Expected sources of difference:
- **Clock sync error**: sender and receiver clocks may differ by 1-50ms
  → Mitigation: use relative timestamps, measure RTT/2 for validation
- **OS scheduling jitter**: Python GIL and OS preemption add ~5-10ms variability
  → Mitigation: use threads, increase process priority
- **Network path**: actual routing may add hops
  → Mitigation: test on LAN only (direct WiFi)

---

## 7. How to Run

### Terminal 1 — Node B first (receiver must be ready before sender)
```bash
python node_b_receiver.py
# Enter output device index when prompted
```

### Terminal 2 — Node A (sender)
```bash
python node_a_sender.py
# Enter: 127.0.0.1 (same machine) or receiver's IP
# Enter microphone device index when prompted
```

### Terminal 3 — Validation (optional)
```bash
python delay_validator.py
```

### Install dependencies
```bash
pip install pyaudio
```
Windows extra step if pyaudio fails:
```bash
pip install pipwin
pipwin install pyaudio
```
