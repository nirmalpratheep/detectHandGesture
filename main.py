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
      flex-direction: column;
      align-items: center;
      gap: 2rem;
      padding: 2rem;
      min-height: 100vh;
      background: #0f0f1a;
      font-family: 'Segoe UI', sans-serif;
      color: #fff;
    }
    #top { display: flex; gap: 2rem; align-items: flex-start; justify-content: center; }
    #left { display: flex; flex-direction: column; align-items: center; gap: 1rem; }
    #video-wrap { position: relative; }
    video { border-radius: 12px; display: block; transform: scaleX(-1); }
    canvas { position: absolute; top: 0; left: 0; }
    #cam-label { font-size: 0.8rem; color: #555; }
    #right { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.5rem; }
    h1 { font-size: 1.2rem; color: #888; letter-spacing: 2px; text-transform: uppercase; }
    /* Gesture guide */
    #guide { width: 100%; max-width: 1060px; }
    #guide h2 { font-size: 0.9rem; color: #555; letter-spacing: 2px; text-transform: uppercase; text-align: center; margin-bottom: 1.2rem; }
    #guide-cards { display: flex; gap: 1.2rem; justify-content: center; flex-wrap: wrap; }
    .gcard {
      background: #1a1a2e;
      border: 2px solid #2a2a40;
      border-radius: 16px;
      padding: 1.2rem 1.4rem;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.7rem;
      width: 210px;
      transition: border-color 0.2s, box-shadow 0.2s;
    }
    .gcard:hover { border-color: #555; box-shadow: 0 0 20px #ffffff11; }
    .ref-icon { font-size: 4.5rem; line-height: 1; }
    .gcard .ctitle { font-size: 1.1rem; font-weight: 700; letter-spacing: 2px; }
    .gcard .cdesc  { font-size: 0.78rem; color: #777; text-align: center; line-height: 1.5; }
    .gcard .cresult { font-size: 0.72rem; background: #0f0f1a; border-radius: 6px; padding: 3px 10px; color: #aaa; }
    .stop-card  { border-color: #e74c3c33; } .stop-card  .ctitle { color: #e74c3c; }
    .go-card    { border-color: #2ecc7133; } .go-card    .ctitle { color: #2ecc71; }
    .left-card  { border-color: #3498db33; } .left-card  .ctitle { color: #3498db; }
    .right-card { border-color: #9b59b633; } .right-card .ctitle { color: #9b59b6; }
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
    #conf-wrap { width: 180px; margin-top: 0.8rem; }
    #conf-bar-bg { background: #222; border-radius: 4px; height: 8px; overflow: hidden; }
    #conf-bar { height: 8px; width: 0%; background: #555; border-radius: 4px; transition: width 0.15s ease, background 0.3s ease; }
    #conf-text { font-size: 0.75rem; color: #666; text-align: right; margin-top: 3px; }
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
  <div id="top">
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
    <div id="conf-wrap">
      <div id="conf-bar-bg"><div id="conf-bar"></div></div>
      <div id="conf-text">—</div>
    </div>
    <div id="status">Loading model...</div>
  </div>
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

    const confBar  = document.getElementById('conf-bar');
    const confText = document.getElementById('conf-text');

    // Returns { gesture, confidence } where confidence is 0–1
    function classifyGesture(lm) {
      const FINGERS = [
        { tip: 8,  pip: 6  },   // index
        { tip: 12, pip: 10 },   // middle
        { tip: 16, pip: 14 },   // ring
        { tip: 20, pip: 18 },   // pinky
      ];
      // margin > 0 means finger is up, < 0 means down
      const margins = FINGERS.map(f => lm[f.pip].y - lm[f.tip].y);
      const upCount   = margins.filter(m => m > 0).length;
      const downCount = margins.filter(m => m < 0).length;

      if (upCount === 4) {
        // confidence = how far above each tip is — average normalised margin
        const conf = Math.min(1, margins.reduce((s, m) => s + Math.max(0, m), 0) / (4 * 0.08));
        return { gesture: 'STOP', confidence: conf };
      }

      if (downCount === 4) {
        const conf = Math.min(1, margins.reduce((s, m) => s + Math.max(0, -m), 0) / (4 * 0.08));
        return { gesture: 'GO', confidence: conf };
      }

      if (margins[0] > 0 && margins[1] < 0 && margins[2] < 0 && margins[3] < 0) {
        const dx = Math.abs(lm[8].x - lm[5].x);
        const dy = Math.abs(lm[8].y - lm[5].y);
        // confidence = how horizontal the pointing direction is
        const conf = Math.min(1, dx / (dx + dy + 1e-6));
        const gesture = lm[8].x < lm[5].x ? 'TURN LEFT' : 'TURN RIGHT';
        return { gesture, confidence: conf };
      }

      return { gesture: 'none', confidence: 0 };
    }

    // Temporal smoothing — keep last 9 frames, pick majority with avg confidence
    const HISTORY = 9;
    const history = [];

    function smoothed(raw) {
      history.push(raw);
      if (history.length > HISTORY) history.shift();

      const counts = {};
      const totalConf = {};
      for (const r of history) {
        counts[r.gesture]    = (counts[r.gesture]    || 0) + 1;
        totalConf[r.gesture] = (totalConf[r.gesture] || 0) + r.confidence;
      }
      let best = 'none', bestCount = 0;
      for (const [g, c] of Object.entries(counts)) {
        if (c > bestCount) { best = g; bestCount = c; }
      }
      const conf = totalConf[best] / bestCount;
      // Require majority + minimum confidence to avoid jitter
      return bestCount >= Math.ceil(HISTORY / 2) && conf >= 0.55
        ? { gesture: best, confidence: conf }
        : { gesture: 'none', confidence: 0 };
    }

    function updateDisplay(gesture, confidence) {
      const g = GESTURES[gesture] || GESTURES['none'];
      box.className     = g.cls;
      icon.textContent  = g.icon;
      label.textContent = g.text;
      const pct = Math.round(confidence * 100);
      confBar.style.width      = gesture === 'none' ? '0%' : pct + '%';
      confBar.style.background = gesture === 'none' ? '#555' : getComputedStyle(document.documentElement).getPropertyValue('--acc') || '#fff';
      confText.textContent     = gesture === 'none' ? '—' : pct + '% confidence';
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
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        status.textContent = '⚠️ Open this page at http://localhost:5000 (not by IP) — browsers block camera access on non-localhost HTTP.';
        status.style.color = '#e74c3c';
        return;
      }
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

      let gesture = 'none', confidence = 0;
      if (result.landmarks && result.landmarks.length > 0) {
        const lm = result.landmarks[0];
        drawUtils.drawConnectors(lm, HandLandmarker.HAND_CONNECTIONS,
          { color: '#00C850', lineWidth: 2 });
        drawUtils.drawLandmarks(lm, { color: '#fff', radius: 4 });
        ({ gesture, confidence } = smoothed(classifyGesture(lm)));
      } else {
        history.length = 0; // reset history when hand leaves frame
      }

      updateDisplay(gesture, confidence);
      if (gesture !== lastGesture) {
        lastGesture = gesture;
        socket.emit('gesture_from_browser', { command: gesture });
      }

      requestAnimationFrame(detect);
    }
    detect();
    }
  </script>
  <div id="guide">
    <h2>Gesture Reference</h2>
    <div id="guide-cards">

      <div class="gcard stop-card">
        <div class="ref-icon">✋</div>
        <div class="ctitle">✋ STOP</div>
        <div class="cdesc">Open palm — all 4 fingers fully extended upward</div>
        <div class="cresult">Expected → STOP command</div>
      </div>

      <div class="gcard go-card">
        <div class="ref-icon">✊</div>
        <div class="ctitle">✊ GO</div>
        <div class="cdesc">Fist — all fingers curled closed</div>
        <div class="cresult">Expected → GO command</div>
      </div>

      <div class="gcard left-card">
        <div class="ref-icon">👈</div>
        <div class="ctitle">👈 LEFT</div>
        <div class="cdesc">Only index finger extended, pointing left</div>
        <div class="cresult">Expected → TURN LEFT command</div>
      </div>

      <div class="gcard right-card">
        <div class="ref-icon">👉</div>
        <div class="ctitle">👉 RIGHT</div>
        <div class="cdesc">Only index finger extended, pointing right</div>
        <div class="cresult">Expected → TURN RIGHT command</div>
      </div>

    </div>
  </div>


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
