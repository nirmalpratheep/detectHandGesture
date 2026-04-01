from flask import Flask, Response, send_from_directory
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

current_gesture = "none"

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Hand Gesture Controller</title>
  <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      display: flex;
      gap: 2rem;
      align-items: flex-start;
      justify-content: center;
      padding: 2rem;
      min-height: 100vh;
      background: #0f0f1a;
      font-family: 'Segoe UI', sans-serif;
      color: #fff;
    }
    #left { display: flex; flex-direction: column; align-items: center; gap: 1rem; }
    #video-wrap { position: relative; }
    video { border-radius: 12px; display: block; transform: scaleX(-1); }
    canvas { position: absolute; top: 0; left: 0; }
    #cam-label { font-size: 0.8rem; color: #555; }
    #right { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.5rem; }
    h1 { font-size: 1.2rem; color: #888; letter-spacing: 2px; text-transform: uppercase; }
    #command-box {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      width: 300px;
      height: 300px;
      border-radius: 50%;
      border: 4px solid #333;
      background: #1a1a2e;
      transition: all 0.3s ease;
    }
    #icon  { font-size: 5rem; margin-bottom: 0.8rem; }
    #label { font-size: 1.8rem; font-weight: 700; letter-spacing: 4px; text-transform: uppercase; }
    #status { font-size: 0.8rem; color: #555; }
    .state-stop  { border-color: #e74c3c; box-shadow: 0 0 40px #e74c3c55; }
    .state-stop  #label { color: #e74c3c; }
    .state-go    { border-color: #2ecc71; box-shadow: 0 0 40px #2ecc7155; }
    .state-go    #label { color: #2ecc71; }
    .state-left  { border-color: #3498db; box-shadow: 0 0 40px #3498db55; }
    .state-left  #label { color: #3498db; }
    .state-right { border-color: #9b59b6; box-shadow: 0 0 40px #9b59b655; }
    .state-right #label { color: #9b59b6; }
    .state-none  { border-color: #333; box-shadow: none; }
    .state-none  #label { color: #555; }
  </style>
</head>
<body>
  <div id="left">
    <div id="video-wrap">
      <video id="video" width="480" height="360" autoplay playsinline muted></video>
      <canvas id="canvas" width="480" height="360" style="position:absolute;top:0;left:0;transform:scaleX(-1);"></canvas>
    </div>
    <button id="start-btn" onclick="startCamera()" style="padding:10px 24px;font-size:1rem;cursor:pointer;border-radius:8px;border:none;background:#2ecc71;color:#000;font-weight:700;">Start Camera</button>
    <div id="cam-label">Live camera feed</div>
  </div>

  <div id="right">
    <h1>Hand Gesture Controller</h1>
    <div id="command-box" class="state-none">
      <div id="icon">✋</div>
      <div id="label">Waiting...</div>
    </div>
    <div id="status">Loading model...</div>
  </div>

  <script type="module">
    import { HandLandmarker, FilesetResolver, DrawingUtils }
      from "/static/vision_bundle.mjs";

    const socket = io();
    const video  = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const ctx    = canvas.getContext('2d');
    const box    = document.getElementById('command-box');
    const icon   = document.getElementById('icon');
    const label  = document.getElementById('label');
    const status = document.getElementById('status');

    const GESTURES = {
      'STOP':       { icon: '✋', text: 'STOP',  cls: 'state-stop'  },
      'GO':         { icon: '✊', text: 'GO',    cls: 'state-go'    },
      'TURN LEFT':  { icon: '👈', text: 'LEFT',  cls: 'state-left'  },
      'TURN RIGHT': { icon: '👉', text: 'RIGHT', cls: 'state-right' },
      'none':       { icon: '✋', text: 'Waiting...', cls: 'state-none' },
    };

    socket.on('connect',    () => status.textContent = 'Connected — show your hand');
    socket.on('disconnect', () => status.textContent = 'Disconnected');

    function fingerUp(lm, tip, pip) { return lm[tip].y < lm[pip].y; }

    function classifyGesture(lm) {
      const indexUp  = fingerUp(lm, 8,  6);
      const middleUp = fingerUp(lm, 12, 10);
      const ringUp   = fingerUp(lm, 16, 14);
      const pinkyUp  = fingerUp(lm, 20, 18);
      const count    = [indexUp, middleUp, ringUp, pinkyUp].filter(Boolean).length;

      if (count >= 4) return 'STOP';
      if (count === 0) return 'GO';
      if (indexUp && !middleUp && !ringUp && !pinkyUp)
        return lm[8].x < lm[5].x ? 'TURN LEFT' : 'TURN RIGHT';
      return 'none';
    }

    function updateDisplay(gesture) {
      const g = GESTURES[gesture] || GESTURES['none'];
      box.className     = g.cls;
      icon.textContent  = g.icon;
      label.textContent = g.text;
    }

    let lastGesture = 'none';

    // Load MediaPipe hand landmarker
    const vision = await FilesetResolver.forVisionTasks("/static/wasm");
    const landmarker = await HandLandmarker.createFromOptions(vision, {
      baseOptions: {
        modelAssetPath: "/static/hand_landmarker.task",
        delegate: "GPU",
      },
      runningMode: "VIDEO",
      numHands: 1,
    });

    window.startCamera = async () => {
      document.getElementById('start-btn').style.display = 'none';
      status.textContent = 'Requesting camera...';
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        video.srcObject = stream;
        await new Promise(r => video.addEventListener('loadeddata', r, { once: true }));
        status.textContent = 'Connected — show your hand';
      } catch (err) {
        status.textContent = 'Camera error: ' + err.message;
        document.getElementById('start-btn').style.display = 'inline-block';
        return;
      }
      runDetection();
    };

    const drawUtils = new DrawingUtils(ctx);

    function runDetection() {

    function detect() {
      const now = performance.now();
      const result = landmarker.detectForVideo(video, now);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      let gesture = 'none';
      if (result.landmarks && result.landmarks.length > 0) {
        const lm = result.landmarks[0];
        drawUtils.drawConnectors(lm, HandLandmarker.HAND_CONNECTIONS,
          { color: '#00C850', lineWidth: 2 });
        drawUtils.drawLandmarks(lm, { color: '#fff', radius: 4 });
        gesture = classifyGesture(lm);
      }

      updateDisplay(gesture);
      if (gesture !== lastGesture) {
        lastGesture = gesture;
        socket.emit('gesture_from_browser', { command: gesture });
      }

      requestAnimationFrame(detect);
    }
    detect();
    }
  </script>
</body>
</html>
"""


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


@app.route("/favicon.ico")
def favicon():
    return Response(status=204)


@app.route("/")
def index():
    return HTML_PAGE


@socketio.on("connect")
def handle_connect():
    emit("gesture", {"command": current_gesture})


@socketio.on("gesture_from_browser")
def handle_gesture(data):
    global current_gesture
    gesture = data.get("command", "none")
    if gesture != current_gesture:
        current_gesture = gesture
        emit("gesture", {"command": gesture}, broadcast=True)


if __name__ == "__main__":
    print("Open http://localhost:5000 in your browser.")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
