import base64
import json
import math
import platform
import time
import cv2
import numpy as np
import mediapipe as mp
import psutil
import uvicorn
from collections import deque, Counter
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# ── MediaPipe ──────────────────────────────────────────────────────────────────
landmarker = mp.tasks.vision.HandLandmarker.create_from_options(
    mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path="static/hand_landmarker.task"),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_hands=1,
    )
)

# ── Gesture classification ─────────────────────────────────────────────────────
def classify(lm) -> tuple[str, float]:
    """Return (gesture, confidence) from a list of 21 hand landmarks."""
    margins = [lm[pip].y - lm[tip].y for tip, pip in [(8,6),(12,10),(16,14),(20,18)]]
    up   = sum(1 for m in margins if m > 0)
    down = sum(1 for m in margins if m < 0)

    if up == 4:
        return "STOP", min(1.0, sum(max(0, m) for m in margins) / (4 * 0.08))

    if down == 4:
        return "GO",   min(1.0, sum(max(0, -m) for m in margins) / (4 * 0.08))

    # Left / Right: direction vector from MCP(5) → Tip(8)
    dx, dy   = lm[8].x - lm[5].x, lm[8].y - lm[5].y
    finger_len = math.hypot(dx, dy)
    if finger_len > 0.08 and abs(dx) > abs(dy) * 0.8:
        return ("TURN LEFT" if dx > 0 else "TURN RIGHT"), min(1.0, abs(dx) / finger_len)

    return "none", 0.0


# ── Majority-vote smoother ─────────────────────────────────────────────────────
HISTORY   = 9
MIN_VOTES = math.ceil(HISTORY / 2)
MIN_CONF  = 0.55

def smooth(history: deque) -> tuple[str, float]:
    if not history:
        return "none", 0.0
    counts   = Counter(g for g, _ in history)
    best, n  = counts.most_common(1)[0]
    if n < MIN_VOTES:
        return "none", 0.0
    avg_conf = sum(c for g, c in history if g == best) / n
    return (best, avg_conf) if avg_conf >= MIN_CONF else ("none", 0.0)


# ── System info ────────────────────────────────────────────────────────────────
_proc = psutil.Process()

def machine_info() -> dict:
    return {
        "os":     f"{platform.system()} {platform.release()}",
        "cpu":    platform.processor() or platform.machine(),
        "cores":  psutil.cpu_count(logical=False),
        "ram_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        "python": platform.python_version(),
    }


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse("templates/index.html")

@app.get("/info", response_class=JSONResponse)
async def info():
    return machine_info()

@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    history: deque = deque(maxlen=HISTORY)

    try:
        while True:
            frame = cv2.imdecode(
                np.frombuffer(base64.b64decode(json.loads(await websocket.receive_text())["frame"]), np.uint8),
                cv2.IMREAD_COLOR,
            )
            if frame is None:
                continue

            t0     = time.perf_counter()
            result = landmarker.detect(mp.Image(image_format=mp.ImageFormat.SRGB,
                                                data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)))
            infer_ms = round((time.perf_counter() - t0) * 1000, 1)
            mem_mb   = round(_proc.memory_info().rss / 1024**2, 1)

            landmarks = []
            if result.hand_landmarks:
                lm = result.hand_landmarks[0]
                history.append(classify(lm))
                landmarks = [{"x": p.x, "y": p.y} for p in lm]
            else:
                history.clear()

            gesture, confidence = smooth(history)
            await websocket.send_text(json.dumps({
                "command":    gesture,
                "confidence": round(confidence, 3),
                "landmarks":  landmarks,
                "infer_ms":   infer_ms,
                "mem_mb":     mem_mb,
            }))

    except WebSocketDisconnect:
        pass


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Open http://localhost:8000 in your browser.")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
