import os
import cv2
import numpy as np
from typing import List, Optional, Tuple

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from feature_utils_squat import to_points_18, features_from_points18

TASK_MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\tasks\pose_landmarker_full.task"

MIN_VALID_FRAMES = 1
DEFAULT_SAMPLE_EVERY = 2

DOWN_THRESHOLD = 120.0

MIN_VIS = 0.35

VALID_KNEE_MIN = 20.0
VALID_KNEE_MAX = 180.0

VALID_BODYLINE_MIN = 60.0
VALID_BODYLINE_MAX = 180.0

WINDOW_HALF = 2

def list_videos(folder: str) -> List[str]:
    exts = (".mp4", ".mov", ".avi", ".mkv", ".m4v")
    if not os.path.exists(folder):
        return []
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]

def _create_landmarker():
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

def _extract_with_params(video_path: str, sample_every: int, down_threshold: float, min_vis: float) -> Tuple[Optional[np.ndarray], str]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, "cannot_open"

    feats_list = []
    min_knees = []

    frames_total = frames_sampled = frames_pose = frames_feats = frames_valid = frames_filtered = 0

    landmarker = _create_landmarker()
    frame_idx = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        frames_total += 1

        if frame_idx % sample_every != 0:
            frame_idx += 1
            continue
        frames_sampled += 1

        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = landmarker.detect(mp_image)

        if not (result.pose_landmarks and len(result.pose_landmarks) > 0):
            frame_idx += 1
            continue
        frames_pose += 1

        pts18 = to_points_18(result.pose_landmarks[0])
        feats = features_from_points18(pts18, min_vis=min_vis)
        if feats is None:
            frame_idx += 1
            continue
        frames_feats += 1

        min_knee = float(feats[0])
        body_line = float(feats[2])

        if not (VALID_KNEE_MIN <= min_knee <= VALID_KNEE_MAX):
            frames_filtered += 1
            frame_idx += 1
            continue

        if not (VALID_BODYLINE_MIN <= body_line <= VALID_BODYLINE_MAX):
            frames_filtered += 1
            frame_idx += 1
            continue

        frames_valid += 1
        feats_list.append(feats)
        min_knees.append(min_knee)

        frame_idx += 1

    cap.release()
    landmarker.close()

    stats = (f"total={frames_total}, sampled={frames_sampled}, pose={frames_pose}, "
             f"feats={frames_feats}, valid={frames_valid}, filtered={frames_filtered}, "
             f"sample_every={sample_every}, min_vis={min_vis}")

    if len(feats_list) < MIN_VALID_FRAMES:
        return None, "too_few_valid_frames(" + stats + ")"

    feats_arr = np.stack(feats_list, axis=0)
    min_knees = np.array(min_knees, dtype=np.float32)

    down_candidates = np.where(min_knees <= down_threshold)[0]
    if len(down_candidates) == 0:
        best_i = int(np.argmin(min_knees))
        best_kind = "fallback_global_min"
    else:
        best_i = int(down_candidates[np.argmin(min_knees[down_candidates])])
        best_kind = "down_min"

    lo = max(0, best_i - WINDOW_HALF)
    hi = min(len(feats_arr), best_i + WINDOW_HALF + 1)
    sample = feats_arr[lo:hi].mean(axis=0)

    best_min_knee = float(min_knees[best_i])
    return sample, f"ok({best_kind}, best_min_knee={best_min_knee:.1f}, {stats})"

def extract_video_sample(video_path: str, sample_every: int = DEFAULT_SAMPLE_EVERY, down_threshold: float = DOWN_THRESHOLD,
                         min_vis: float = MIN_VIS, verbose: bool = False) -> Optional[np.ndarray]:
    sample, reason = _extract_with_params(video_path, sample_every, down_threshold, min_vis)
    if sample is not None:
        if verbose:
            print(f"[OK] {os.path.basename(video_path)} -> {reason}")
        return sample

    if sample_every != 1:
        sample2, reason2 = _extract_with_params(video_path, 1, down_threshold, min_vis)
        if sample2 is not None:
            if verbose:
                print(f"[FALLBACK OK] {os.path.basename(video_path)} -> {reason2}")
            return sample2
        if verbose:
            print(f"[SKIP] {os.path.basename(video_path)} -> {reason2}")
    else:
        if verbose:
            print(f"[SKIP] {os.path.basename(video_path)} -> {reason}")

    return None

def build_dataset(correct_dir: str, incorrect_dir: str, verbose: bool = True):
    X, y = [], []

    correct_videos = list_videos(correct_dir)
    incorrect_videos = list_videos(incorrect_dir)

    print(f"[INFO] Found videos: correct={len(correct_videos)} incorrect={len(incorrect_videos)}")

    ok_c = 0
    for vp in correct_videos:
        sample = extract_video_sample(vp, verbose=verbose)
        if sample is not None:
            X.append(sample); y.append("correct"); ok_c += 1

    ok_i = 0
    for vp in incorrect_videos:
        sample = extract_video_sample(vp, verbose=verbose)
        if sample is not None:
            X.append(sample); y.append("incorrect"); ok_i += 1

    print(f"[INFO] Extracted samples: correct={ok_c} incorrect={ok_i}")
    return np.array(X), np.array(y)