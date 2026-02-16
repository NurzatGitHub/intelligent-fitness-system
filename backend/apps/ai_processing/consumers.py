import json
from collections import deque
import numpy as np
from channels.generic.websocket import AsyncWebsocketConsumer

from .ml import get_model

# плечи/локти/кисти/таз/лодыжки (важные точки для v-check)
KEY_IDS = {4, 5, 6, 7, 8, 9, 10, 11, 14, 15}


def mid(p1, p2):
    return ((p1["x"] + p2["x"]) / 2.0, (p1["y"] + p2["y"]) / 2.0)


def dist(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    return float((dx * dx + dy * dy) ** 0.5)


def angle(a, b, c):
    # угол ABC
    ax, ay = a[0] - b[0], a[1] - b[1]
    cx, cy = c[0] - b[0], c[1] - b[1]
    dot = ax * cx + ay * cy
    na = (ax * ax + ay * ay) ** 0.5
    nc = (cx * cx + cy * cy) ** 0.5
    if na == 0 or nc == 0:
        return 0.0
    cosv = max(-1.0, min(1.0, dot / (na * nc)))
    return float(np.degrees(np.arccos(cosv)))


def ready_check(points):
    # points: list[dict{x,y,v}] len=18
    p = points
    l_sh = (p[4]["x"], p[4]["y"])
    r_sh = (p[5]["x"], p[5]["y"])
    l_wr = (p[8]["x"], p[8]["y"])
    r_wr = (p[9]["x"], p[9]["y"])

    hip_mid = mid(p[10], p[11])
    ankle_mid = mid(p[14], p[15])

    shoulder_mid = ((l_sh[0] + r_sh[0]) / 2.0, (l_sh[1] + r_sh[1]) / 2.0)
    wrist_mid = ((l_wr[0] + r_wr[0]) / 2.0, (l_wr[1] + r_wr[1]) / 2.0)

    # грудь: середина плеч (если будет точка 3 - можешь заменить)
    chest_mid = shoulder_mid

    cond1 = wrist_mid[1] > shoulder_mid[1] + 0.02  # кисти ниже плеч
    cond2 = ankle_mid[1] > hip_mid[1] + 0.04       # лодыжки ниже таза
    body_line = angle(chest_mid, hip_mid, ankle_mid)
    cond3 = body_line > 155                         # корпус почти прямой

    score = int(cond1) + int(cond2) + int(cond3)
    return score >= 2, body_line


def compute_features(points):
    p = points

    L = angle((p[4]["x"], p[4]["y"]), (p[6]["x"], p[6]["y"]), (p[8]["x"], p[8]["y"]))
    R = angle((p[5]["x"], p[5]["y"]), (p[7]["x"], p[7]["y"]), (p[9]["x"], p[9]["y"]))

    min_elbow = min(L, R)
    diff = abs(L - R)

    hip_mid = mid(p[10], p[11])
    ankle_mid = mid(p[14], p[15])
    chest_mid = mid(p[4], p[5])
    body_line = angle(chest_mid, hip_mid, ankle_mid)

    shoulder_width = dist((p[4]["x"], p[4]["y"]), (p[5]["x"], p[5]["y"])) + 1e-6
    elbow_width = dist((p[6]["x"], p[6]["y"]), (p[7]["x"], p[7]["y"]))
    elbow_ratio = elbow_width / shoulder_width

    feats = [min_elbow, diff, body_line, elbow_ratio, L, R]
    metrics = {"L": L, "R": R, "body_line": body_line, "elbow_ratio": elbow_ratio}
    return feats, metrics


def build_segments(metrics):
    body_line = metrics["body_line"]
    L = metrics["L"]
    R = metrics["R"]

    good_body = body_line >= 160
    good_left = L >= 70
    good_right = R >= 70

    segs = []

    # руки
    segs += [
        {"a": 4, "b": 6, "color": "#00FF00" if good_left else "#FF0000"},
        {"a": 6, "b": 8, "color": "#00FF00" if good_left else "#FF0000"},
        {"a": 5, "b": 7, "color": "#00FF00" if good_right else "#FF0000"},
        {"a": 7, "b": 9, "color": "#00FF00" if good_right else "#FF0000"},
    ]

    # корпус
    body_color = "#00FF00" if good_body else "#FF0000"
    segs += [
        {"a": 4, "b": 10, "color": body_color},
        {"a": 5, "b": 11, "color": body_color},
        {"a": 10, "b": 11, "color": body_color},
        {"a": 10, "b": 14, "color": body_color},
        {"a": 11, "b": 15, "color": body_color},
    ]
    return segs


class AnalyzeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.model = get_model()
        self.ready_streak = 0
        self.smooth_buf = deque(maxlen=5)

        # self.label_streak = 0
        # self.last_label = None

        self.rep_count = 0
        self.phase = "UP"          # UP / DOWN
        self.down_streak = 0
        self.up_streak = 0
        await self.accept()
        await self.send_json({"type": "connected", "server": "NEW_LANDMARKS_PIPELINE"})

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            await self.send_json({"type": "error", "message": "text_expected"})
            return

        try:
            msg = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_json({"type": "error", "message": "invalid_json"})
            return

        # service
        if msg.get("type") == "ping":
            await self.send_json({"type": "pong"})
            return

        exercise = msg.get("exercise")
        points = msg.get("points")

        if exercise != "push_up" or not isinstance(points, list) or len(points) != 18:
            await self.send_json({"type": "error", "message": "bad_payload"})
            return

        # visibility check
        for i in KEY_IDS:
            if float(points[i].get("v", 0.0)) < 0.5:
                await self.send_json({
                    "type": "result",
                    "exercise": "push_up",
                    "status": "SETUP",
                    "hint": "Примите позицию push-up",
                    "segments": []
                })
                return

        # smoothing
        self.smooth_buf.append(points)
        smoothed = points
        if len(self.smooth_buf) >= 3:
            smoothed = []
            for idx in range(18):
                xs = [f[idx]["x"] for f in self.smooth_buf]
                ys = [f[idx]["y"] for f in self.smooth_buf]
                vs = [f[idx].get("v", 1.0) for f in self.smooth_buf]
                smoothed.append({
                    "x": float(np.mean(xs)),
                    "y": float(np.mean(ys)),
                    "v": float(np.mean(vs)),
                })

        is_ready, _ = ready_check(smoothed)
        self.ready_streak = self.ready_streak + 1 if is_ready else 0

        if self.ready_streak < 2:
            await self.send_json({
                "type": "result",
                "exercise": "push_up",
                "status": "SETUP",
                "hint": "Примите позицию push-up",
                "segments": []
            })
            return

        feats, metrics = compute_features(smoothed)

        min_elbow = feats[0]  # feats = [min_elbow, diff, body_line, elbow_ratio, L, R]

        DOWN_T = 95    # когда локоть согнут (вниз)
        UP_T   = 155   # когда локоть почти прямой (вверх)

        # накапливаем “стабильность” 2 кадра подряд
        if min_elbow < DOWN_T:
            self.down_streak += 1
            self.up_streak = 0
        elif min_elbow > UP_T:
            self.up_streak += 1
            self.down_streak = 0

        # переходы фаз
        if self.phase == "UP" and self.down_streak >= 2:
            self.phase = "DOWN"
            self.down_streak = 0

        if self.phase == "DOWN" and self.up_streak >= 2:
            self.phase = "UP"
            self.up_streak = 0
            self.rep_count += 1
        X = np.array(feats, dtype=np.float32).reshape(1, -1)

        overall = None
        confidence = None

        if hasattr(self.model, "predict_proba"):
            probs = self.model.predict_proba(X)[0]
            classes = list(self.model.classes_)
            best_i = int(np.argmax(probs))
            overall = str(classes[best_i])
            confidence = float(probs[best_i])
        else:
            pred = self.model.predict(X)[0]
            overall = str(pred)

        segs = build_segments(metrics)

        # optional: "не красним" если модель не уверена
        if confidence is not None and overall == "incorrect" and confidence < 0.65:
            overall = "correct"
            segs = [{"a": s["a"], "b": s["b"], "color": "#00FF00"} for s in segs]

        await self.send_json({
            "exercise":"push_up",
            "status":"ACTIVE",
            "overall": overall,
            "confidence": confidence,
            "phase": self.phase,
            "rep_count": self.rep_count,
            "segments": segs
        })

    async def send_json(self, payload: dict):
        await self.send(text_data=json.dumps(payload, ensure_ascii=False))
