import json
from collections import deque

import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

from .ml import get_model

# 18 points indices (как PoseMapper)
# 0 le,1 re,2 mouth,3 chest,4 Lsh,5 Rsh,6 Lel,7 Rel,8 Lwr,9 Rwr,
# 10 Lhip,11 Rhip,12 Lknee,13 Rknee,14 Lank,15 Rank,16 Lfoot,17 Rfoot

VIS_TH = 0.12
MIN_GOOD = 6
READY_STREAK_NEED = 3

NEEDED_IDS = {3,4,5,6,7,8,9,10,11}

DOWN_T = 100
UP_T   = 150

# ---- NEW: strict "pushup pose" geometry thresholds (normalized coords) ----
MIN_BODY_SPAN_X = 0.28     # body should be "long" horizontally (standing is short)
MAX_BODY_SPAN_Y = 0.25     # body should not be tall vertically (standing is tall)
MAX_CHEST_HIP_DY = 0.10    # chest and hips should be almost same Y (horizontal torso)
MAX_SH_WR_X = 0.20         # wrists roughly under shoulders (in X)
WRIST_BELOW_SH_Y = 0.04    # wrists lower than shoulders
HIP_BELOW_SH_Y = 0.06      # hips lower than shoulders
BODYLINE_READY_MIN = 155   # torso line reasonably straight

# For coloring / quality
BODYLINE_GOOD = 165
ELBOW_GOOD_MIN = 70
HIP_OFFSET_GOOD = 0.06     # abs(hip_offset) small => straight line


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
    """
    STRICT check: accept ONLY when the person is really in push-up like pose.
    Main idea: body must be mostly horizontal and long in X, not tall in Y.
    """
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

    # how "horizontal" the whole body is (chest -> ankle)
    span_x = abs(chest[0] - ankle_mid[0])
    span_y = abs(chest[1] - ankle_mid[1])

    body_line = angle(chest, hip_mid, knee_mid)

    cond_wrist_below = wrist_mid[1] > shoulder_mid[1] + WRIST_BELOW_SH_Y
    cond_hip_below   = hip_mid[1]   > shoulder_mid[1] + HIP_BELOW_SH_Y

    # torso should be almost horizontal (chest and hips near same Y)
    cond_torso_flat  = abs(chest[1] - hip_mid[1]) < MAX_CHEST_HIP_DY

    # wrists roughly under shoulders (avoid random standing arms)
    cond_wr_under_sh = abs(wrist_mid[0] - shoulder_mid[0]) < MAX_SH_WR_X

    # global body orientation: long in X and not tall in Y
    cond_body_span_x = span_x > MIN_BODY_SPAN_X
    cond_body_span_y = span_y < MAX_BODY_SPAN_Y

    cond_body_ok     = body_line >= BODYLINE_READY_MIN

    score = sum([
        cond_wrist_below,
        cond_hip_below,
        cond_torso_flat,
        cond_wr_under_sh,
        cond_body_span_x,
        cond_body_span_y,
        cond_body_ok
    ])

    # need 6/7 to be sure (standing will fail span_x/span_y + torso_flat usually)
    return (score >= 6), body_line, score


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

    # hip_offset
    x1, y1 = chest
    x2, y2 = knee_mid
    xh, yh = hip_mid

    if abs(x2 - x1) < 1e-6:
        y_on_line = (y1 + y2) / 2.0
    else:
        t = (xh - x1) / (x2 - x1)
        y_on_line = y1 + t * (y2 - y1)

    hip_offset = yh - y_on_line  # negative => hips up (pike), positive => hips sag

    feats = [min_elbow, diff, body_line, elbow_ratio, left_elbow, right_elbow, hip_offset]
    metrics = {
        "L": left_elbow,
        "R": right_elbow,
        "body_line": body_line,
        "hip_offset": hip_offset
    }
    return feats, metrics


def build_segments(metrics):
    """
    Draw a 'square/box' torso instead of triangle.
    Use:
      shoulders: 4-5
      hips: 10-11
      verticals: 4-10 and 5-11
    """
    body_line = metrics["body_line"]
    hip_offset = metrics.get("hip_offset", 0.0)
    L = metrics["L"]
    R = metrics["R"]

    good_body = (body_line >= BODYLINE_GOOD) and (abs(hip_offset) <= HIP_OFFSET_GOOD)
    good_left = L >= ELBOW_GOOD_MIN
    good_right = R >= ELBOW_GOOD_MIN

    green = "#00FF00"
    red = "#FF0000"

    arm_left_color = green if good_left else red
    arm_right_color = green if good_right else red
    body_color = green if good_body else red

    segs = [
        # Arms
        {"a": 4, "b": 6, "color": arm_left_color},
        {"a": 6, "b": 8, "color": arm_left_color},
        {"a": 5, "b": 7, "color": arm_right_color},
        {"a": 7, "b": 9, "color": arm_right_color},

        # Torso box
        {"a": 4, "b": 5, "color": body_color},   # shoulders line
        {"a": 10, "b": 11, "color": body_color}, # hips line
        {"a": 4, "b": 10, "color": body_color},  # left side
        {"a": 5, "b": 11, "color": body_color},  # right side

        # Legs
        {"a": 10, "b": 12, "color": body_color},
        {"a": 11, "b": 13, "color": body_color},
        {"a": 12, "b": 14, "color": body_color},
        {"a": 13, "b": 15, "color": body_color},
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
        await self.send_json({"type": "connected", "server": "PUSHUP_V7_STRICT_READY2"})

    async def receive(self, text_data=None, bytes_data=None):
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
                    "hint": "Покажите полностью тело (ноги + руки)",
                    "segments": []
                })
                return

            # smooth points
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
                    "hint": "Примите позицию push-up (горизонтально, руки под плечами)",
                    "segments": []
                })
                return

            feats, metrics = compute_features_7(smoothed)
            X = np.array(feats, dtype=np.float32).reshape(1, -1)

            if X.shape[1] != self.model_n:
                await self.send_json({"type": "error", "message": f"feature_mismatch got={X.shape[1]} expected={self.model_n}"})
                return

            # rep counting via elbow angle thresholds
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

            # model prediction (overall correctness)
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

            # keep your "lenient incorrect" override
            if confidence is not None and overall == "incorrect" and confidence < 0.75:
                overall = "correct"
                segs = [{"a": s["a"], "b": s["b"], "color": "#00FF00"} for s in segs]

            await self.send_json({
                "type": "result",
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