import json
from collections import deque

import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

from .ml import get_model

# 18 points indices (как PoseMapper)
# 0 le,1 re,2 mouth,3 chest,4 Lsh,5 Rsh,6 Lel,7 Rel,8 Lwr,9 Rwr,
# 10 Lhip,11 Rhip,12 Lknee,13 Rknee,14 Lank,15 Rank,16 Lfoot,17 Rfoot

VIS_TH = 0.15
MIN_GOOD = 7
READY_STREAK_NEED = 3

NEEDED_IDS = {3,4,5,6,7,8,9,10,11,12,13,14,15}

DOWN_T = 95
UP_T   = 155


def _is_finite(x: float) -> bool:
    return bool(np.isfinite(x))


def _clamp01(x: float) -> float:
    if not _is_finite(x):
        return 0.0
    return float(min(1.0, max(0.0, x)))


def sanitize_points(points):
    out = []
    for p in points:
        x = _clamp01(float(p.get("x", 0.0)))
        y = _clamp01(float(p.get("y", 0.0)))
        v = float(p.get("v", 0.0))
        if not _is_finite(v):
            v = 0.0
        out.append({"x": x, "y": y, "v": float(v)})
    return out


def mid(p1, p2):
    return ((p1["x"] + p2["x"]) / 2.0, (p1["y"] + p2["y"]) / 2.0)


def dist(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return float((dx * dx + dy * dy) ** 0.5)


def angle(a, b, c):
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    dot = ax * cx + ay * cy
    na = (ax * ax + ay * ay) ** 0.5
    nc = (cx * cx + cy * cy) ** 0.5
    if na == 0.0 or nc == 0.0:
        return 0.0
    cosv = max(-1.0, min(1.0, dot / (na * nc)))
    return float(np.degrees(np.arccos(cosv)))


def ready_check(p):
    chest = (p[3]["x"], p[3]["y"])
    l_sh  = (p[4]["x"], p[4]["y"])
    r_sh  = (p[5]["x"], p[5]["y"])
    l_wr  = (p[8]["x"], p[8]["y"])
    r_wr  = (p[9]["x"], p[9]["y"])

    hip_mid   = mid(p[10], p[11])
    knee_mid  = mid(p[12], p[13])
    ankle_mid = mid(p[14], p[15])

    shoulder_mid = ((l_sh[0] + r_sh[0]) / 2.0, (l_sh[1] + r_sh[1]) / 2.0)
    wrist_mid    = ((l_wr[0] + r_wr[0]) / 2.0, (l_wr[1] + r_wr[1]) / 2.0)

    body_line = angle(chest, hip_mid, knee_mid)

    cond_wrist_below = wrist_mid[1] > shoulder_mid[1] + 0.04
    cond_hip_below   = hip_mid[1]   > shoulder_mid[1] + 0.06
    cond_ankle_below = ankle_mid[1] > hip_mid[1] + 0.06
    cond_horizontal  = abs(chest[1] - hip_mid[1]) < 0.22
    cond_body_ok     = body_line > 145

    score = sum([
        cond_wrist_below,
        cond_hip_below,
        cond_ankle_below,
        cond_horizontal,
        cond_body_ok
    ])
    return (score >= 4), body_line, score


def compute_features_7(p):
    L_sh = (p[4]["x"], p[4]["y"])
    R_sh = (p[5]["x"], p[5]["y"])
    L_el = (p[6]["x"], p[6]["y"])
    R_el = (p[7]["x"], p[7]["y"])
    L_wr = (p[8]["x"], p[8]["y"])
    R_wr = (p[9]["x"], p[9]["y"])

    chest    = (p[3]["x"], p[3]["y"])
    hip_mid  = mid(p[10], p[11])
    knee_mid = mid(p[12], p[13])

    left_elbow  = angle(L_sh, L_el, L_wr)
    right_elbow = angle(R_sh, R_el, R_wr)

    min_elbow = min(left_elbow, right_elbow)
    diff = abs(left_elbow - right_elbow)

    body_line = angle(chest, hip_mid, knee_mid)

    shoulder_w = dist(L_sh, R_sh) + 1e-6
    elbow_w = dist(L_el, R_el)
    elbow_ratio = elbow_w / shoulder_w

    # hip_offset ( feature_utils)
    x1, y1 = chest
    x2, y2 = knee_mid
    xh, yh = hip_mid

    if abs(x2 - x1) < 1e-6:
        y_on_line = (y1 + y2) / 2.0
    else:
        t = (xh - x1) / (x2 - x1)
        y_on_line = y1 + t * (y2 - y1)

    hip_offset = yh - y_on_line  # negative => hips up

    feats = [min_elbow, diff, body_line, elbow_ratio, left_elbow, right_elbow, hip_offset]
    metrics = {"L": left_elbow, "R": right_elbow, "body_line": body_line}
    return feats, metrics


def build_segments(metrics):
    body_line = metrics["body_line"]
    L = metrics["L"]
    R = metrics["R"]

    good_body = body_line >= 160
    good_left = L >= 70
    good_right = R >= 70

    segs = [
        {"a": 4, "b": 6, "color": "#00FF00" if good_left else "#FF0000"},
        {"a": 6, "b": 8, "color": "#00FF00" if good_left else "#FF0000"},
        {"a": 5, "b": 7, "color": "#00FF00" if good_right else "#FF0000"},
        {"a": 7, "b": 9, "color": "#00FF00" if good_right else "#FF0000"},
    ]

    body_color = "#00FF00" if good_body else "#FF0000"
    segs += [
        {"a": 3, "b": 10, "color": body_color},
        {"a": 3, "b": 11, "color": body_color},
        {"a": 10, "b": 12, "color": body_color},
        {"a": 11, "b": 13, "color": body_color},
    ]
    return segs


class AnalyzeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.model = get_model()
        self.model_n = int(getattr(self.model, "n_features_in_", 7))

        self.ready_streak = 0
        self.smooth_buf = deque(maxlen=5)

        self.rep_count = 0
        self.phase = "UP"
        self.down_streak = 0
        self.up_streak = 0

        await self.accept()
        await self.send_json({"type": "connected", "server": "PUSHUP_V7_STRICT"})

    async def receive(self, text_data=None, bytes_data=None):
        # Главное: НЕ роняем consumer (иначе Broken pipe на Android)
        try:
            if not text_data:
                await self.send_json({"type": "error", "message": "text_expected"})
                return

            try:
                msg = json.loads(text_data)
            except json.JSONDecodeError:
                await self.send_json({"type": "error", "message": "invalid_json"})
                return

            if msg.get("type") == "ping":
                await self.send_json({"type": "pong"})
                return

            if msg.get("exercise") != "push_up":
                await self.send_json({"type": "error", "message": "bad_exercise"})
                return

            points = msg.get("points")
            if not isinstance(points, list) or len(points) != 18:
                await self.send_json({"type": "error", "message": "bad_payload"})
                return

            points = sanitize_points(points)

            good = sum(1 for i in NEEDED_IDS if float(points[i].get("v", 0.0)) >= VIS_TH)
            if good < MIN_GOOD:
                self.ready_streak = 0
                self.down_streak = 0
                self.up_streak = 0
                self.phase = "UP"
                await self.send_json({
                    "type": "result",
                    "exercise": "push_up",
                    "status": "SETUP",
                    "hint": "Примите позицию push-up (покажите ноги + руки)",
                    "segments": []
                })
                return

            self.smooth_buf.append(points)
            smoothed = points
            if len(self.smooth_buf) >= 3:
                smoothed = []
                for idx in range(18):
                    xs = [f[idx]["x"] for f in self.smooth_buf]
                    ys = [f[idx]["y"] for f in self.smooth_buf]
                    vs = [f[idx].get("v", 0.0) for f in self.smooth_buf]
                    smoothed.append({"x": float(np.mean(xs)), "y": float(np.mean(ys)), "v": float(np.mean(vs))})

            is_ready, body_line, score = ready_check(smoothed)
            self.ready_streak = self.ready_streak + 1 if is_ready else 0

            if self.ready_streak < READY_STREAK_NEED:
                self.phase = "UP"
                self.down_streak = 0
                self.up_streak = 0
                await self.send_json({
                    "type": "result",
                    "exercise": "push_up",
                    "status": "SETUP",
                    "hint": "Примите позицию push-up",
                    "segments": []
                })
                return

            feats, metrics = compute_features_7(smoothed)
            X = np.array(feats, dtype=np.float32).reshape(1, -1)

            if X.shape[1] != self.model_n:
                await self.send_json({"type": "error", "message": f"feature_mismatch got={X.shape[1]} expected={self.model_n}"})
                return

            min_elbow = feats[0]
            if min_elbow < DOWN_T:
                self.down_streak += 1
                self.up_streak = 0
            elif min_elbow > UP_T:
                self.up_streak += 1
                self.down_streak = 0

            if self.phase == "UP" and self.down_streak >= 2:
                self.phase = "DOWN"
                self.down_streak = 0

            if self.phase == "DOWN" and self.up_streak >= 2:
                self.phase = "UP"
                self.up_streak = 0
                self.rep_count += 1

            if hasattr(self.model, "predict_proba"):
                probs = self.model.predict_proba(X)[0]
                classes = list(self.model.classes_)
                best_i = int(np.argmax(probs))
                overall = str(classes[best_i])
                confidence = float(probs[best_i])
            else:
                overall = str(self.model.predict(X)[0])
                confidence = None

            segs = build_segments(metrics)

            if confidence is not None and overall == "incorrect" and confidence < 0.75:
                overall = "correct"
                segs = [{"a": s["a"], "b": s["b"], "color": "#00FF00"} for s in segs]

            await self.send_json({
                "exercise": "push_up",
                "status": "ACTIVE",
                "overall": overall,
                "confidence": confidence,
                "phase": self.phase,
                "rep_count": self.rep_count,
                "segments": segs
            })

        except Exception as e:
            await self.send_json({"type": "error", "message": f"server_exception: {type(e).__name__}: {str(e)}"})

    async def send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload, ensure_ascii=False))
