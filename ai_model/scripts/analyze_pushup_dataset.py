import os
import csv
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from ai_model.scripts.feature_utils_pushup import to_points_18, angle, mid

CORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\pushup_dataset\videos\correct"
INCORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\pushup_dataset\videos\incorrect"
TASK_MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\tasks\pose_landmarker_full.task"

OUT_CSV = r"C:\Fitness\intelligent-fitness-system\ai_model\scripts\dataset_frame_stats.csv"

FRAME_STEP = 1        
MIN_VIS = 0.20        
PRINT_EVERY_N_FRAMES = 30  

# -----------------------------
def list_videos(folder: str) -> List[str]:
    exts = (".mp4", ".mov", ".avi", ".mkv", ".m4v")
    if not os.path.exists(folder):
        return []
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]

def create_landmarker():
    if not os.path.exists(TASK_MODEL_PATH):
        raise FileNotFoundError(f"Task model not found: {TASK_MODEL_PATH}")

    base_options = python.BaseOptions(model_asset_path=TASK_MODEL_PATH)
    options = vision.PoseLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.IMAGE,
        num_poses=1,
        min_pose_detection_confidence=0.5,
        min_pose_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    return vision.PoseLandmarker.create_from_options(options)

def vis_ok(pts18, idxs, min_vis=MIN_VIS) -> bool:
    return all(pts18[i][2] >= min_vis for i in idxs)

def compute_metrics_from_pts18(pts18) -> Optional[Dict[str, float]]:
    """
    returns dict with:
    left_elbow, right_elbow, min_elbow,
    body_line (chest-hip-knee),
    hip_offset (hips up / sag)
    """
    if len(pts18) != 18:
        return None

    if not vis_ok(pts18, [4,6,8,5,7,9]):
        return None

    P = [np.array([pts18[i][0], pts18[i][1]], dtype=np.float32) for i in range(18)]
    L_sh, R_sh = P[4], P[5]
    L_el, R_el = P[6], P[7]
    L_wr, R_wr = P[8], P[9]

    left_elbow = angle(L_sh, L_el, L_wr)
    right_elbow = angle(R_sh, R_el, R_wr)
    min_elbow = float(min(left_elbow, right_elbow))

    # Body (prefer chest-hip-knee)
    body_line = 180.0
    hip_offset = 0.0

    if vis_ok(pts18, [3,10,11,12,13]):
        chest = P[3]
        L_hip, R_hip = P[10], P[11]
        L_knee, R_knee = P[12], P[13]

        hip_mid = mid(L_hip, R_hip)
        knee_mid = mid(L_knee, R_knee)

        body_line = float(angle(chest, hip_mid, knee_mid))

        x1, y1 = float(chest[0]), float(chest[1])
        x2, y2 = float(knee_mid[0]), float(knee_mid[1])
        xh, yh = float(hip_mid[0]), float(hip_mid[1])

        if abs(x2 - x1) < 1e-6:
            y_on_line = (y1 + y2) / 2.0
        else:
            t = (xh - x1) / (x2 - x1)
            y_on_line = y1 + t * (y2 - y1)

        hip_offset = float(yh - y_on_line)

    return {
        "left_elbow": float(left_elbow),
        "right_elbow": float(right_elbow),
        "min_elbow": float(min_elbow),
        "body_line": float(body_line),
        "hip_offset": float(hip_offset),
    }

def phase_from_min_elbow(min_elbow: float, down_th: float, up_th: float) -> str:
    if min_elbow <= down_th:
        return "DOWN"
    if min_elbow >= up_th:
        return "UP"
    return "MID"

def summarize(arr: np.ndarray) -> Dict[str, float]:
    return {
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "p10": float(np.percentile(arr, 10)),
        "p90": float(np.percentile(arr, 90)),
    }

def main():
    landmarker = create_landmarker()

    videos = []
    for vp in list_videos(CORRECT_DIR):
        videos.append((vp, "correct"))
    for vp in list_videos(INCORRECT_DIR):
        videos.append((vp, "incorrect"))

    print(f"[INFO] videos total: {len(videos)} (correct={len(list_videos(CORRECT_DIR))}, incorrect={len(list_videos(INCORRECT_DIR))})")
    if len(videos) == 0:
        raise RuntimeError("No videos found.")

    per_label = {
        "correct": {"min_elbow": [], "body_line": [], "hip_offset": []},
        "incorrect": {"min_elbow": [], "body_line": [], "hip_offset": []},
    }

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        wcsv = csv.writer(f)
        wcsv.writerow(["label","video","frame","phase_guess","min_elbow","left_elbow","right_elbow","body_line","hip_offset"])

        for video_path, label in videos:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"[SKIP] cannot open: {os.path.basename(video_path)}")
                continue

            frame_idx = 0
            kept = 0
            pose_ok = 0
            valid = 0

            DOWN_TH_TMP = 110.0
            UP_TH_TMP = 155.0

            while True:
                ok, frame_bgr = cap.read()
                if not ok:
                    break
                frame_idx += 1

                if FRAME_STEP > 1 and (frame_idx % FRAME_STEP != 0):
                    continue

                kept += 1

                rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                res = landmarker.detect(mp_image)

                if not (res.pose_landmarks and len(res.pose_landmarks) > 0):
                    continue

                pose_ok += 1
                lm33 = res.pose_landmarks[0]
                pts18 = to_points_18(lm33)

                metrics = compute_metrics_from_pts18(pts18)
                if metrics is None:
                    continue

                valid += 1

                ph = phase_from_min_elbow(metrics["min_elbow"], DOWN_TH_TMP, UP_TH_TMP)

                wcsv.writerow([
                    label,
                    os.path.basename(video_path),
                    frame_idx,
                    ph,
                    f"{metrics['min_elbow']:.2f}",
                    f"{metrics['left_elbow']:.2f}",
                    f"{metrics['right_elbow']:.2f}",
                    f"{metrics['body_line']:.2f}",
                    f"{metrics['hip_offset']:.4f}",
                ])

                per_label[label]["min_elbow"].append(metrics["min_elbow"])
                per_label[label]["body_line"].append(metrics["body_line"])
                per_label[label]["hip_offset"].append(metrics["hip_offset"])

                if valid % PRINT_EVERY_N_FRAMES == 0:
                    print(f"[{label}] {os.path.basename(video_path)} frame={frame_idx} "
                          f"min_elbow={metrics['min_elbow']:.1f} body_line={metrics['body_line']:.1f} hip_off={metrics['hip_offset']:.3f}")

            cap.release()
            print(f"[DONE] {label}/{os.path.basename(video_path)} total_frames={frame_idx} sampled={kept} pose={pose_ok} valid={valid}")

    landmarker.close()


    print("\n================ SUMMARY ================")
    for label in ["correct", "incorrect"]:
        print(f"\n--- {label.upper()} ---")
        for key in ["min_elbow", "body_line", "hip_offset"]:
            arr = np.array(per_label[label][key], dtype=np.float32)
            if arr.size == 0:
                print(f"{key}: NO DATA")
                continue
            s = summarize(arr)
            print(f"{key}: min={s['min']:.2f} max={s['max']:.2f} mean={s['mean']:.2f} median={s['median']:.2f} p10={s['p10']:.2f} p90={s['p90']:.2f}")


    corr = np.array(per_label["correct"]["min_elbow"], dtype=np.float32)
    if corr.size > 0:
        down_th = float(np.percentile(corr, 30))
        up_th = float(np.percentile(corr, 80))

        # Expand margins a bit for stability
        down_th = min(down_th + 5.0, 120.0)
        up_th = max(up_th - 5.0, 145.0)

        print("\n=========== AUTO THRESHOLDS (SUGGESTED) ===========")
        print(f"DOWN_TH ≈ {down_th:.1f}  (min_elbow <= DOWN_TH => DOWN)")
        print(f"UP_TH   ≈ {up_th:.1f}  (min_elbow >= UP_TH   => UP)")
        print("These are suggested from correct data distribution.\n")

    print(f"✅ Saved per-frame CSV: {OUT_CSV}")

if __name__ == "__main__":
    main()
