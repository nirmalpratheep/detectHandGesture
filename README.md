# detectHandGesture

Real-time hand gesture recognition — browser captures webcam frames, streams them to a Python FastAPI server, MediaPipe classifies the gesture, and the result is pushed back to the browser over WebSocket.

<video src="demo/demo.mp4" controls width="100%"></video>

---

## Architecture

```
Browser
  │  JPEG frame  (WebSocket, ~12 fps)
  ▼
FastAPI + Uvicorn  (Python)
  ├── MediaPipe HandLandmarker  →  21 landmarks per frame
  ├── Gesture classifier        →  STOP / GO / TURN LEFT / TURN RIGHT
  └── Majority-vote smoother   →  last 9 frames, min 55% confidence
  │  JSON  { command, confidence, landmarks, infer_ms, mem_mb }
  ▼
Browser
  ├── Draws landmark skeleton on canvas
  ├── Updates gesture circle + confidence bar
  └── Shows latency / inference time / memory / machine info
```

No ML runs in the browser. All inference is Python-side.

---

## Gestures

| Gesture | Command |
|---|---|
| Open palm — all 4 fingers up | ✋ STOP |
| Fist — all fingers curled | ✊ GO |
| Index finger pointing left horizontally | 👈 TURN LEFT |
| Index finger pointing right horizontally | 👉 TURN RIGHT |

**Left / Right note:** Point the index finger as horizontally as possible. The classifier uses the direction vector from MCP (knuckle) to Tip — if the horizontal component exceeds the vertical component, the gesture is detected. Diagonal pointing will not trigger.

---

## Project Structure

```
detectHandGesture/
├── main.py                   # FastAPI server, MediaPipe inference, WebSocket
├── templates/
│   └── index.html            # UI — camera, gesture display, stats, guide
├── static/
│   └── hand_landmarker.task  # MediaPipe model (~5 MB)
├── demo/
│   └── demo.mp4              # Screen recording
└── pyproject.toml
```

---

## Setup

```bash
pip install fastapi "uvicorn[standard]" mediapipe opencv-python numpy psutil
python main.py
```

Open **`http://localhost:8000`**, click **Start Camera**, allow camera access.

> Use `localhost` — browsers block `getUserMedia` on plain HTTP from IP addresses.
