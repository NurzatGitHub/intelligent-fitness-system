import os
import csv
import cv2
import numpy as np
from typing import List, Dict, Optional

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from ai_model.scripts.feature_utils_squat import to_points_18, angle, mid


CORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\squat_dataset\videos\correct"
INCORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\squat_dataset\videos\incorrect"
TASK_MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\tasks\pose_landmarker_full.task"

OUT_CSV = r"C:\Fitness\intelligent-fitness-system\ai_model\scripts\squat_frame_stats.csv"


FRAME_STEP = 1            
MIN_VIS = 0.35           
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
    left_knee, right_knee, min_knee,
    body_line (shoulder-mid -> hip-mid -> knee-mid),
    hip_depth (hip_mid_y - knee_mid_y),
    stance_ratio (feet_width / shoulder_width)
    """
    if len(pts18) != 18:
        return None

    if not vis_ok(pts18, [10, 12, 14, 11, 13, 15]):
        return None

    P = [np.array([pts18[i][0], pts18[i][1]], dtype=np.float32) for i in range(18)]

    L_sh, R_sh = P[4], P[5]
    L_hip, R_hip = P[10], P[11]
    L_knee, R_knee = P[12], P[13]
    L_ank, R_ank = P[14], P[15]
    L_foot, R_foot = P[16], P[17]

    left_knee = float(angle(L_hip, L_knee, L_ank))
    right_knee = float(angle(R_hip, R_knee, R_ank))
    min_knee = float(min(left_knee, right_knee))
    knee_diff = float(abs(left_knee - right_knee))


    sh_mid = mid(L_sh, R_sh)
    hip_mid = mid(L_hip, R_hip)
    knee_mid = mid(L_knee, R_knee)


    body_line = float(angle(sh_mid, hip_mid, knee_mid))


    hip_depth = float(hip_mid[1] - knee_mid[1])

    shoulder_w = float(np.linalg.norm(L_sh - R_sh))
    feet_w = float(np.linalg.norm(L_foot - R_foot))
    stance_ratio = float(feet_w / (shoulder_w + 1e-6))

    return {
        "left_knee": left_knee,
        "right_knee": right_knee,
        "min_knee": min_knee,
        "knee_diff": knee_diff,
        "body_line": body_line,
        "hip_depth": hip_depth,
        "stance_ratio": stance_ratio,
    }

def phase_from_min_knee(min_knee: float, down_th: float, up_th: float) -> str:
    if min_knee <= down_th:
        return "DOWN"
    if min_knee >= up_th:
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

    print(f"[INFO] videos total: {len(videos)} "
          f"(correct={len(list_videos(CORRECT_DIR))}, incorrect={len(list_videos(INCORRECT_DIR))})")
    if len(videos) == 0:
        raise RuntimeError("No videos found.")

    per_label = {
        "correct": {"min_knee": [], "body_line": [], "hip_depth": [], "stance_ratio": [], "knee_diff": []},
        "incorrect": {"min_knee": [], "body_line": [], "hip_depth": [], "stance_ratio": [], "knee_diff": []},
    }

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        wcsv = csv.writer(f)
        wcsv.writerow([
            "label", "video", "frame", "phase_guess",
            "min_knee", "left_knee", "right_knee", "knee_diff",
            "body_line", "hip_depth", "stance_ratio"
        ])

        DOWN_TH_TMP = 110.0
        UP_TH_TMP = 165.0

        for video_path, label in videos:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                print(f"[SKIP] cannot open: {os.path.basename(video_path)}")
                continue

            frame_idx = 0
            kept = 0
            pose_ok = 0
            valid = 0

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

                pts18 = to_points_18(res.pose_landmarks[0])
                metrics = compute_metrics_from_pts18(pts18)
                if metrics is None:
                    continue
                valid += 1

                ph = phase_from_min_knee(metrics["min_knee"], DOWN_TH_TMP, UP_TH_TMP)

                wcsv.writerow([
                    label,
                    os.path.basename(video_path),
                    frame_idx,
                    ph,
                    f"{metrics['min_knee']:.2f}",
                    f"{metrics['left_knee']:.2f}",
                    f"{metrics['right_knee']:.2f}",
                    f"{metrics['knee_diff']:.2f}",
                    f"{metrics['body_line']:.2f}",
                    f"{metrics['hip_depth']:.5f}",
                    f"{metrics['stance_ratio']:.4f}",
                ])

                per_label[label]["min_knee"].append(metrics["min_knee"])
                per_label[label]["body_line"].append(metrics["body_line"])
                per_label[label]["hip_depth"].append(metrics["hip_depth"])
                per_label[label]["stance_ratio"].append(metrics["stance_ratio"])
                per_label[label]["knee_diff"].append(metrics["knee_diff"])

                if valid % PRINT_EVERY_N_FRAMES == 0:
                    print(f"[{label}] {os.path.basename(video_path)} frame={frame_idx} "
                          f"min_knee={metrics['min_knee']:.1f} body_line={metrics['body_line']:.1f} "
                          f"hip_depth={metrics['hip_depth']:.3f} stance={metrics['stance_ratio']:.2f}")

            cap.release()
            print(f"[DONE] {label}/{os.path.basename(video_path)} total_frames={frame_idx} sampled={kept} pose={pose_ok} valid={valid}")

    landmarker.close()

    print("\n================ SUMMARY ================")
    for label in ["correct", "incorrect"]:
        print(f"\n--- {label.upper()} ---")
        for key in ["min_knee", "knee_diff", "body_line", "hip_depth", "stance_ratio"]:
            arr = np.array(per_label[label][key], dtype=np.float32)
            if arr.size == 0:
                print(f"{key}: NO DATA")
                continue
            s = summarize(arr)
            print(f"{key}: min={s['min']:.2f} max={s['max']:.2f} mean={s['mean']:.2f} "
                  f"median={s['median']:.2f} p10={s['p10']:.2f} p90={s['p90']:.2f}")

    corr = np.array(per_label["correct"]["min_knee"], dtype=np.float32)
    if corr.size > 0:

        down_th = float(np.percentile(corr, 30))
        up_th = float(np.percentile(corr, 80))

        down_th = min(down_th + 5.0, 130.0)   
        up_th = max(up_th - 5.0, 150.0)

        print("\n=========== AUTO THRESHOLDS (SUGGESTED) ===========")
        print(f"DOWN_TH ≈ {down_th:.1f}  (min_knee <= DOWN_TH => DOWN)")
        print(f"UP_TH   ≈ {up_th:.1f}  (min_knee >= UP_TH   => UP)")
        print("Suggested from correct data distribution.\n")

    print(f"✅ Saved per-frame CSV: {OUT_CSV}")

if __name__ == "__main__":
    main()