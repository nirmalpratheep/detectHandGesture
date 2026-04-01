# detectHandGesture

A real-time hand gesture recognition system that reads your webcam, classifies hand poses, and streams the result to a browser dashboard — with no cloud APIs or external services required after setup.

---

## How It Works

```
Webcam (browser)
     │
     ▼
MediaPipe Hand Landmarker (JS, runs in browser)
     │  detects 21 landmarks on your hand
     ▼
Gesture Classifier (JS)
     │  compares fingertip positions to classify pose
     ▼
Flask-SocketIO (Python server)
     │  receives gesture, broadcasts to all connected tabs
     ▼
Browser Dashboard
     │  updates icon + color in real time
```

Everything runs locally. The browser captures the webcam, detects the gesture, and sends it to the Python server over a WebSocket. The server then broadcasts it to the dashboard.

---

## Gestures

Gestures are detected by checking which fingers are extended (fingertip Y-coordinate above the middle-joint Y-coordinate), and for pointing gestures, whether the index fingertip is to the left or right of its base joint.

| Gesture | How to do it | Command | Color |
|---|---|---|---|
| Open palm | Extend all 4 fingers | ✋ STOP | Red |
| Fist | Curl all fingers closed | ✊ GO | Green |
| Point left | Only index finger up, aimed left | 👈 TURN LEFT | Blue |
| Point right | Only index finger up, aimed right | 👉 TURN RIGHT | Purple |

---

## Architecture

| Component | Technology | Role |
|---|---|---|
| Gesture detection | MediaPipe Tasks Vision (JS) | Runs in the browser, processes webcam frames |
| Web server | Flask + Flask-SocketIO | Serves the page, relays gesture events |
| Real-time comms | WebSocket (Socket.IO) | Pushes gesture changes instantly, no polling |
| Hand model | `hand_landmarker.task` | Pre-trained model file (~5 MB), loaded locally |
| WASM runtime | `vision_bundle.mjs` + `wasm/` | MediaPipe JS runtime, served locally by Flask |

All JS and model assets are served from the local `static/` folder — no CDN calls at runtime.

---

## Project Structure

```
detectHandGesture/
├── main.py                  # Flask server + HTML page
├── static/
│   ├── vision_bundle.mjs    # MediaPipe JS bundle
│   ├── hand_landmarker.task # Hand landmark model
│   └── wasm/                # WebAssembly runtime files
└── pyproject.toml
```

---

## Setup

**1. Install Python dependencies**

```bash
pip install flask flask-socketio
```

**2. Download static assets** (one-time, done automatically on first run via `npm pack`)

```bash
npm pack @mediapipe/tasks-vision@0.10.3
tar -xzf mediapipe-tasks-vision-0.10.3.tgz
mkdir -p static/wasm
cp package/vision_bundle.mjs static/
cp package/wasm/* static/wasm/
```

The `hand_landmarker.task` model file is downloaded automatically by the server on first run.

**3. Run the server**

```bash
python main.py
```

**4. Open the dashboard**

Open **`http://localhost:5000`** in your browser.

> Must use `localhost`, not an IP address. Browsers only allow webcam access on secure contexts (`https://` or `localhost`).

**5. Click "Start Camera"** and allow camera permission when prompted.

---

## Notes

- **WSL2 users:** The webcam is accessed by the Windows browser directly — no webcam passthrough to WSL2 is needed. Always use `http://localhost:5000`.
- **First load:** The WASM runtime and model are cached by the browser after the first load.
- **Multiple tabs:** All open tabs receive the same gesture broadcast from the server.
