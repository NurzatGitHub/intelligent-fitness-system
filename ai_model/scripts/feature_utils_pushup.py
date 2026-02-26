import numpy as np
from typing import List, Tuple, Optional


def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Angle ABC in degrees."""
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-6
    cosang = float(np.dot(ba, bc) / denom)
    return float(np.degrees(np.arccos(np.clip(cosang, -1.0, 1.0))))

def dist(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.linalg.norm(a - b))

def mid(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a + b) / 2.0


def to_points_18(lm33) -> List[Tuple[float, float, float]]:
    """
    Output (len=18) indices:
    0 left_ear
    1 right_ear
    2 mouth (avg left/right mouth)
    3 chest (avg left/right shoulder)
    4 left_shoulder
    5 right_shoulder
    6 left_elbow
    7 right_elbow
    8 left_wrist
    9 right_wrist
    10 left_hip
    11 right_hip
    12 left_knee
    13 right_knee
    14 left_ankle
    15 right_ankle
    16 left_foot
    17 right_foot
    """
    def p(i: int):
        v = getattr(lm33[i], "visibility", 1.0)
        return (float(lm33[i].x), float(lm33[i].y), float(v))


    mouth_l = p(9)
    mouth_r = p(10)
    mouth = (
        (mouth_l[0] + mouth_r[0]) / 2.0,
        (mouth_l[1] + mouth_r[1]) / 2.0,
        min(mouth_l[2], mouth_r[2]),
    )


    sh_l = p(11)
    sh_r = p(12)
    chest = (
        (sh_l[0] + sh_r[0]) / 2.0,
        (sh_l[1] + sh_r[1]) / 2.0,
        min(sh_l[2], sh_r[2]),
    )

    return [
        p(7),  p(8),   
        mouth,         
        chest,         
        p(11), p(12),
        p(13), p(14),  
        p(15), p(16), 
        p(23), p(24), 
        p(25), p(26),  
        p(27), p(28), 
        p(31), p(32),  
    ]



def features_from_points18(
    pts18: List[Tuple[float, float, float]],
    min_vis: float = 0.20
) -> Optional[np.ndarray]:

    if len(pts18) != 18:
        return None


    needed = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
    if any(pts18[i][2] < min_vis for i in needed):
        return None

    P = [np.array([pts18[i][0], pts18[i][1]], dtype=np.float32) for i in range(18)]

    chest = P[3]
    L_sh, R_sh = P[4], P[5]
    L_el, R_el = P[6], P[7]
    L_wr, R_wr = P[8], P[9]
    L_hip, R_hip = P[10], P[11]
    L_knee, R_knee = P[12], P[13]


    left_elbow = angle(L_sh, L_el, L_wr)
    right_elbow = angle(R_sh, R_el, R_wr)

    min_elbow = min(left_elbow, right_elbow)
    diff = abs(left_elbow - right_elbow)

    shoulder_w = dist(L_sh, R_sh)
    elbow_w = dist(L_el, R_el)
    elbow_ratio = elbow_w / (shoulder_w + 1e-6)


    hip_mid = mid(L_hip, R_hip)
    knee_mid = mid(L_knee, R_knee)

    body_line = angle(chest, hip_mid, knee_mid)

    x1, y1 = float(chest[0]), float(chest[1])
    x2, y2 = float(knee_mid[0]), float(knee_mid[1])
    xh, yh = float(hip_mid[0]), float(hip_mid[1])

    if abs(x2 - x1) < 1e-6:
        y_on_line = (y1 + y2) / 2.0
    else:
        t = (xh - x1) / (x2 - x1)
        y_on_line = y1 + t * (y2 - y1)

    hip_offset = yh - y_on_line

    return np.array(
        [
            min_elbow,
            diff,
            body_line,
            elbow_ratio,
            left_elbow,
            right_elbow,
            hip_offset 
        ],
        dtype=np.float32
    )
