# dataset_extractor.py (UPDATED for your push-up dataset)
import os
import cv2
import numpy as np
from typing import List, Optional, Tuple

import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from ai_model.scripts.feature_utils_pushup import to_points_18, features_from_points18

# -----------------------------
# Task model path
# -----------------------------
TASK_MODEL_PATH = r"C:\Fitness\intelligent-fitness-system\ai_model\models\tasks\pose_landmarker_full.task"

# -----------------------------
# Tuned settings for YOUR dataset
# -----------------------------
MIN_VALID_FRAMES = 1          # your videos are short (1 rep)
DEFAULT_SAMPLE_EVERY = 2      # will fallback to 1 if needed
DOWN_THRESHOLD = 120.0        # from your stats
MIN_VIS = 0.20                # relaxed for push-up

# Filter impossible elbow angles (remove landmark glitches)
VALID_ELBOW_MIN = 30.0
VALID_ELBOW_MAX = 180.0

# Also filter extreme/garbage body_line (optional, safe)
VALID_BODYLINE_MIN = 120.0
VALID_BODYLINE_MAX = 180.0

# Window around best DOWN frame
WINDOW_HALF = 2  # +/-2 frames => 5 frames average


# -----------------------------
# Video listing
# -----------------------------
def list_videos(folder: str) -> List[str]:
    exts = (".mp4", ".mov", ".avi", ".mkv", ".m4v")
    if not os.path.exists(folder):
        return []
    return [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(exts)]


# -----------------------------
# MediaPipe landmarker
# -----------------------------
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


# -----------------------------
# Core extraction (with stats & reasons)
# -----------------------------
def _extract_with_params(
    video_path: str,
    sample_every: int,
    down_threshold: float,
    min_vis: float
) -> Tuple[Optional[np.ndarray], str]:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return None, "cannot_open"

    feats_list = []
    min_elbows = []

    frames_total = 0
    frames_sampled = 0
    frames_pose = 0
    frames_feats = 0
    frames_valid = 0
    frames_filtered = 0

    landmarker = _create_landmarker()
    frame_idx = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break

        frames_total += 1

        # sample frames
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

        lm33 = result.pose_landmarks[0]
        pts18 = to_points_18(lm33)

        # IMPORTANT: use relaxed visibility
        feats = features_from_points18(pts18, min_vis=min_vis)
        if feats is None:
            frame_idx += 1
            continue
        frames_feats += 1

        # feats: [min_elbow, diff, body_line, elbow_ratio, left_elbow, right_elbow]
        min_elbow = float(feats[0])
        body_line = float(feats[2])

        # Filter out landmark glitches (impossible angles)
        if not (VALID_ELBOW_MIN <= min_elbow <= VALID_ELBOW_MAX):
            frames_filtered += 1
            frame_idx += 1
            continue

        # Filter obvious body_line garbage (optional)
        if not (VALID_BODYLINE_MIN <= body_line <= VALID_BODYLINE_MAX):
            frames_filtered += 1
            frame_idx += 1
            continue

        frames_valid += 1
        feats_list.append(feats)
        min_elbows.append(min_elbow)

        frame_idx += 1

    cap.release()
    landmarker.close()

    stats = (
        f"total={frames_total}, sampled={frames_sampled}, pose={frames_pose}, "
        f"feats={frames_feats}, valid={frames_valid}, filtered={frames_filtered}, "
        f"sample_every={sample_every}, min_vis={min_vis}"
    )

    if len(feats_list) < MIN_VALID_FRAMES:
        return None, "too_few_valid_frames(" + stats + ")"

    feats_arr = np.stack(feats_list, axis=0)
    min_elbows = np.array(min_elbows, dtype=np.float32)

    # Prefer DOWN frames (min_elbow <= threshold)
    down_candidates = np.where(min_elbows <= down_threshold)[0]
    if len(down_candidates) == 0:
        # fallback: choose the minimum anyway
        best_i = int(np.argmin(min_elbows))
        best_kind = "fallback_global_min"
    else:
        best_i = int(down_candidates[np.argmin(min_elbows[down_candidates])])
        best_kind = "down_min"

    lo = max(0, best_i - WINDOW_HALF)
    hi = min(len(feats_arr), best_i + WINDOW_HALF + 1)

    sample = feats_arr[lo:hi].mean(axis=0)

    # attach best min_elbow to reason for visibility
    best_min_elbow = float(min_elbows[best_i])
    return sample, f"ok({best_kind}, best_min_elbow={best_min_elbow:.1f}, {stats})"


# -----------------------------
# Public API: extract one sample per video
# -----------------------------
def extract_video_sample(
    video_path: str,
    sample_every: int = DEFAULT_SAMPLE_EVERY,
    down_threshold: float = DOWN_THRESHOLD,
    min_vis: float = MIN_VIS,
    verbose: bool = False
) -> Optional[np.ndarray]:
    sample, reason = _extract_with_params(video_path, sample_every, down_threshold, min_vis)
    if sample is not None:
        if verbose:
            print(f"[OK] {os.path.basename(video_path)} -> {reason}")
        return sample

    # fallback: try every frame
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


# -----------------------------
# Build dataset (one sample per video)
# -----------------------------
def build_dataset(correct_dir: str, incorrect_dir: str, verbose: bool = True):
    X, y = [], []

    correct_videos = list_videos(correct_dir)
    incorrect_videos = list_videos(incorrect_dir)

    print(f"[INFO] Found videos: correct={len(correct_videos)} incorrect={len(incorrect_videos)}")

    ok_c = 0
    for vp in correct_videos:
        sample = extract_video_sample(vp, verbose=verbose)
        if sample is not None:
            X.append(sample)
            y.append("correct")
            ok_c += 1

    ok_i = 0
    for vp in incorrect_videos:
        sample = extract_video_sample(vp, verbose=verbose)
        if sample is not None:
            X.append(sample)
            y.append("incorrect")
            ok_i += 1

    print(f"[INFO] Extracted samples: correct={ok_c} incorrect={ok_i}")

    return np.array(X), np.array(y)
