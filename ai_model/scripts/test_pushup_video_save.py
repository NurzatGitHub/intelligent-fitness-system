import os
import cv2
import numpy as np
import joblib
from collections import Counter

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from feature_utils import to_points_18, features_from_points18

MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\pushup_model.pkl"
TASK_MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\tasks\pose_landmarker_full.task"

DOWN_TH = 120.0
UP_TH = 155.0


def create_landmarker():
    base_options = python.BaseOptions(model_asset_path=TASK_MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1
    )
    return vision.PoseLandmarker.create_from_options(options)


def detect_phase(min_elbow):
    if min_elbow <= DOWN_TH:
        return "DOWN"
    if min_elbow >= UP_TH:
        return "UP"
    return "MID"


def draw_skeleton(frame, pts18, feats):
    h, w = frame.shape[:2]

    # convert normalized → pixel
    pts_px = []
    for (x, y, v) in pts18:
        pts_px.append((int(x * w), int(y * h)))

    min_elbow = feats[0]
    body_line = feats[2]

    # colors
    arm_color = (0, 255, 0) if 80 <= min_elbow <= 110 else (0, 0, 255)
    body_color = (0, 255, 0) if body_line > 165 else (0, 0, 255)

    segments = [
        # arms
        (4,6, arm_color), (6,8, arm_color),
        (5,7, arm_color), (7,9, arm_color),

        # torso
        (4,10, body_color), (5,11, body_color),
        (10,11, body_color),

        # legs
        (10,14, body_color), (11,15, body_color),
    ]

    for a,b,color in segments:
        cv2.line(frame, pts_px[a], pts_px[b], color, 3)

    for (x,y) in pts_px:
        cv2.circle(frame, (x,y), 4, (255,255,255), -1)


def main(video_path):

    model = joblib.load(MODEL_PATH)
    landmarker = create_landmarker()

    cap = cv2.VideoCapture(video_path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30

    out_path = os.path.join(os.path.dirname(video_path), "pushup_result.mp4")
    writer = cv2.VideoWriter(out_path,
                             cv2.VideoWriter_fourcc(*"mp4v"),
                             fps,
                             (w, h))

    state = "WAIT_UP"
    down_predictions = []
    correct_frames = 0
    incorrect_frames = 0

    while True:
        ok, frame = cap.read()
        if not ok:
            break

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(mp_image)

        pred_label = "-"
        phase = "MID"

        if result.pose_landmarks:
            lm33 = result.pose_landmarks[0]
            pts18 = to_points_18(lm33)
            feats = features_from_points18(pts18)

            if feats is not None:
                min_elbow = feats[0]
                phase = detect_phase(min_elbow)
                pred_label = model.predict([feats])[0]

                if pred_label == "correct":
                    correct_frames += 1
                else:
                    incorrect_frames += 1

                draw_skeleton(frame, pts18, feats)

                if state == "WAIT_UP" and phase == "UP":
                    state = "WAIT_DOWN"

                elif state == "WAIT_DOWN" and phase == "DOWN":
                    state = "IN_DOWN"

                elif state == "IN_DOWN":
                    down_predictions.append(pred_label)
                    if phase == "UP":
                        break

        cv2.putText(frame, f"PRED: {pred_label}", (20,40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255),2)

        writer.write(frame)

    cap.release()
    writer.release()
    landmarker.close()

    if len(down_predictions) == 0:
        print("No full cycle detected.")
        return

    final_result = Counter(down_predictions).most_common(1)[0][0]

    print("\n============================")
    print("FINAL RESULT:", final_result.upper())
    print("Correct frames:", correct_frames)
    print("Incorrect frames:", incorrect_frames)
    print("Saved video:", out_path)
    print("============================")


if __name__ == "__main__":
    import sys
    main(sys.argv[1])
