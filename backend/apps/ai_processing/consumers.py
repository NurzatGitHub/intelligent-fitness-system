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

# PUSH-UP
NEEDED_IDS_PUSHUP = {3,4,5,6,7,8,9,10,11,12,13,14,15}
DOWN_T_PUSHUP = 95
UP_T_PUSHUP   = 155

# SQUAT
NEEDED_IDS_SQUAT = {3,4,5,10,11,12,13,14,15}
DOWN_T_SQUAT = 110
UP_T_SQUAT   = 165


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


# -----------------------------
# PUSH-UP logic
# -----------------------------
def ready_check_pushup(p):
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

    score = sum([cond_wrist_below, cond_hip_below, cond_ankle_below, cond_horizontal, cond_body_ok])
    return (score >= 4), body_line, score


def compute_features_7_pushup(p):
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


def build_segments_pushup(metrics):
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


# -----------------------------
# SQUAT logic (8 features)
# -----------------------------
def ready_check_squat(p):
    hip_mid   = mid(p[10], p[11])
    knee_mid  = mid(p[12], p[13])
    ankle_mid = mid(p[14], p[15])

    l_sh = (p[4]["x"], p[4]["y"])
    r_sh = (p[5]["x"], p[5]["y"])
    shoulder_mid = ((l_sh[0] + r_sh[0]) / 2.0, (l_sh[1] + r_sh[1]) / 2.0)

    # плечи выше таза, таз выше колен, колени выше щиколоток
    cond_order = (shoulder_mid[1] < hip_mid[1] < knee_mid[1] < ankle_mid[1])

    # корпус более-менее вертикально: плечи и таз близко по X
    cond_upright = abs(shoulder_mid[0] - hip_mid[0]) < 0.20

    score = sum([cond_order, cond_upright])
    return (score >= 2), score


def compute_features_8_squat(p):
    """
    8 фич под squat_model.pkl (expected=8):
      0 min_knee_angle
      1 left_knee_angle
      2 right_knee_angle
      3 knee_diff
      4 min_hip_angle
      5 knee_cave_ratio
      6 depth_ratio
      7 trunk_angle
    """
    chest = (p[3]["x"], p[3]["y"])
    L_sh  = (p[4]["x"], p[4]["y"])
    R_sh  = (p[5]["x"], p[5]["y"])

    L_hip = (p[10]["x"], p[10]["y"])
    R_hip = (p[11]["x"], p[11]["y"])
    L_knee = (p[12]["x"], p[12]["y"])
    R_knee = (p[13]["x"], p[13]["y"])
    L_ank = (p[14]["x"], p[14]["y"])
    R_ank = (p[15]["x"], p[15]["y"])

    pelvis = ((L_hip[0] + R_hip[0]) / 2.0, (L_hip[1] + R_hip[1]) / 2.0)

    # knee angles: hip-knee-ankle
    left_knee_angle  = angle(L_hip, L_knee, L_ank)
    right_knee_angle = angle(R_hip, R_knee, R_ank)
    min_knee_angle   = min(left_knee_angle, right_knee_angle)
    knee_diff        = abs(left_knee_angle - right_knee_angle)

    # hip angles: shoulder-hip-knee
    left_hip_angle  = angle(L_sh, L_hip, L_knee)
    right_hip_angle = angle(R_sh, R_hip, R_knee)
    min_hip_angle   = min(left_hip_angle, right_hip_angle)

    # knee cave ratio (knee width / hip width)
    hip_w  = dist(L_hip, R_hip) + 1e-6
    knee_w = dist(L_knee, R_knee)
    knee_cave_ratio = knee_w / hip_w

    # depth ratio: hip_mid_y / ankle_mid_y
    hip_mid_y = pelvis[1]
    ankle_mid_y = ((L_ank[1] + R_ank[1]) / 2.0) + 1e-6
    depth_ratio = hip_mid_y / ankle_mid_y

    # trunk angle: угол корпуса от вертикали
    torso_vec = (pelvis[0] - chest[0], pelvis[1] - chest[1])
    tv_norm = (torso_vec[0] ** 2 + torso_vec[1] ** 2) ** 0.5 + 1e-6
    cosang = torso_vec[1] / tv_norm  # (0,1) вертикаль
    cosang = max(-1.0, min(1.0, cosang))
    trunk_angle = float(np.degrees(np.arccos(cosang)))

    feats = [
        min_knee_angle,
        left_knee_angle,
        right_knee_angle,
        knee_diff,
        min_hip_angle,
        knee_cave_ratio,
        depth_ratio,
        trunk_angle,
    ]

    metrics = {
        "min_knee": min_knee_angle,
        "trunk": trunk_angle,
        "knee_cave": knee_cave_ratio,
        "depth": depth_ratio,
    }
    return feats, metrics


def build_segments_squat(metrics):
    good_knee = metrics["min_knee"] >= 80
    good_torso = metrics["trunk"] >= 155

    knee_color = "#00FF00" if good_knee else "#FF0000"
    torso_color = "#00FF00" if good_torso else "#FF0000"

    segs = [
        {"a": 10, "b": 12, "color": knee_color},
        {"a": 12, "b": 14, "color": knee_color},
        {"a": 11, "b": 13, "color": knee_color},
        {"a": 13, "b": 15, "color": knee_color},
        {"a": 4, "b": 10, "color": torso_color},
        {"a": 5, "b": 11, "color": torso_color},
    ]
    return segs


class AnalyzeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # load models
        self.pushup_model = get_model("push_up")
        self.pushup_n = int(getattr(self.pushup_model, "n_features_in_", 7))

        # ✅ squat_model.pkl = Pipeline(StandardScaler + RandomForestClassifier) (expected=8)
        self.squat_model = get_model("squat")
        self.squat_n = int(getattr(self.squat_model, "n_features_in_", 8))

        # state
        self.ready_streak = 0
        self.smooth_buf = deque(maxlen=5)

        self.rep_count = 0
        self.phase = "UP"
        self.down_streak = 0
        self.up_streak = 0

        await self.accept()
        await self.send_json({"type": "connected", "server": "MULTI_EX_V2"})

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

            exercise = msg.get("exercise")
            if exercise not in ("push_up", "squat"):
                await self.send_json({"type": "error", "message": "bad_exercise"})
                return

            points = msg.get("points")
            if not isinstance(points, list) or len(points) != 18:
                await self.send_json({"type": "error", "message": "bad_payload"})
                return

            points = sanitize_points(points)

            needed = NEEDED_IDS_PUSHUP if exercise == "push_up" else NEEDED_IDS_SQUAT
            good = sum(1 for i in needed if float(points[i].get("v", 0.0)) >= VIS_TH)
            if good < MIN_GOOD:
                self.ready_streak = 0
                self.down_streak = 0
                self.up_streak = 0
                self.phase = "UP"
                await self.send_json({
                    "type": "result",
                    "exercise": exercise,
                    "status": "SETUP",
                    "hint": "Станьте полностью в кадр (покажите ноги и корпус)",
                    "segments": []
                })
                return

            # smooth
            self.smooth_buf.append(points)
            smoothed = points
            if len(self.smooth_buf) >= 3:
                smoothed = []
                for idx in range(18):
                    xs = [f[idx]["x"] for f in self.smooth_buf]
                    ys = [f[idx]["y"] for f in self.smooth_buf]
                    vs = [f[idx].get("v", 0.0) for f in self.smooth_buf]
                    smoothed.append({"x": float(np.mean(xs)), "y": float(np.mean(ys)), "v": float(np.mean(vs))})

            # ready
            if exercise == "push_up":
                is_ready, body_line, score = ready_check_pushup(smoothed)
            else:
                is_ready, score = ready_check_squat(smoothed)

            self.ready_streak = self.ready_streak + 1 if is_ready else 0

            if self.ready_streak < READY_STREAK_NEED:
                self.phase = "UP"
                self.down_streak = 0
                self.up_streak = 0
                await self.send_json({
                    "type": "result",
                    "exercise": exercise,
                    "status": "SETUP",
                    "hint": "Примите исходную позицию",
                    "segments": []
                })
                return

            # features + model
            if exercise == "push_up":
                feats, metrics = compute_features_7_pushup(smoothed)
                X = np.array(feats, dtype=np.float32).reshape(1, -1)
                if X.shape[1] != self.pushup_n:
                    await self.send_json({"type": "error", "message": f"feature_mismatch got={X.shape[1]} expected={self.pushup_n}"})
                    return

                # reps by elbow
                min_elbow = feats[0]
                if min_elbow < DOWN_T_PUSHUP:
                    self.down_streak += 1
                    self.up_streak = 0
                elif min_elbow > UP_T_PUSHUP:
                    self.up_streak += 1
                    self.down_streak = 0

                if self.phase == "UP" and self.down_streak >= 2:
                    self.phase = "DOWN"
                    self.down_streak = 0

                if self.phase == "DOWN" and self.up_streak >= 2:
                    self.phase = "UP"
                    self.up_streak = 0
                    self.rep_count += 1

                if hasattr(self.pushup_model, "predict_proba"):
                    probs = self.pushup_model.predict_proba(X)[0]
                    classes = list(self.pushup_model.classes_)
                    best_i = int(np.argmax(probs))
                    overall = str(classes[best_i])
                    confidence = float(probs[best_i])
                else:
                    overall = str(self.pushup_model.predict(X)[0])
                    confidence = None

                segs = build_segments_pushup(metrics)

                if confidence is not None and overall == "incorrect" and confidence < 0.75:
                    overall = "correct"
                    segs = [{"a": s["a"], "b": s["b"], "color": "#00FF00"} for s in segs]

            else:
                feats, metrics = compute_features_8_squat(smoothed)
                X = np.array(feats, dtype=np.float32).reshape(1, -1)
                if X.shape[1] != self.squat_n:
                    await self.send_json({"type": "error", "message": f"feature_mismatch got={X.shape[1]} expected={self.squat_n}"})
                    return

                # reps by knee
                min_knee = feats[0]  # min_knee_angle
                if min_knee < DOWN_T_SQUAT:
                    self.down_streak += 1
                    self.up_streak = 0
                elif min_knee > UP_T_SQUAT:
                    self.up_streak += 1
                    self.down_streak = 0

                if self.phase == "UP" and self.down_streak >= 2:
                    self.phase = "DOWN"
                    self.down_streak = 0

                if self.phase == "DOWN" and self.up_streak >= 2:
                    self.phase = "UP"
                    self.up_streak = 0
                    self.rep_count += 1

                # ✅ RandomForest / Pipeline: predict_proba
                if hasattr(self.squat_model, "predict_proba"):
                    probs = self.squat_model.predict_proba(X)[0]
                    classes = list(self.squat_model.classes_)  # Pipeline обычно прокидывает
                    best_i = int(np.argmax(probs))
                    overall = str(classes[best_i])
                    confidence = float(probs[best_i])
                else:
                    overall = str(self.squat_model.predict(X)[0])
                    confidence = None

                segs = build_segments_squat(metrics)

            await self.send_json({
                "exercise": exercise,
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