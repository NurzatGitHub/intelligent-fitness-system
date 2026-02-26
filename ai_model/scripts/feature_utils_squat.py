import numpy as np
from typing import List, Tuple, Optional

def angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
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
    def p(i: int):
        v = getattr(lm33[i], "visibility", 1.0)
        return (float(lm33[i].x), float(lm33[i].y), float(v))

    mouth_l = p(9); mouth_r = p(10)
    mouth = ((mouth_l[0]+mouth_r[0])/2, (mouth_l[1]+mouth_r[1])/2, min(mouth_l[2], mouth_r[2]))

    sh_l = p(11); sh_r = p(12)
    chest = ((sh_l[0]+sh_r[0])/2, (sh_l[1]+sh_r[1])/2, min(sh_l[2], sh_r[2]))

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
    min_vis: float = 0.35
) -> Optional[np.ndarray]:

    if len(pts18) != 18:
        return None

    needed = [4,5, 10,11, 12,13, 14,15, 16,17]
    if any(pts18[i][2] < min_vis for i in needed):
        return None

    P = [np.array([pts18[i][0], pts18[i][1]], dtype=np.float32) for i in range(18)]

    L_sh, R_sh = P[4], P[5]
    L_hip, R_hip = P[10], P[11]
    L_knee, R_knee = P[12], P[13]
    L_ank, R_ank = P[14], P[15]
    L_foot, R_foot = P[16], P[17]

    hip_mid = mid(L_hip, R_hip)
    knee_mid = mid(L_knee, R_knee)
    sh_mid = mid(L_sh, R_sh)
    foot_mid = mid(L_foot, R_foot)

    left_knee = angle(L_hip, L_knee, L_ank)
    right_knee = angle(R_hip, R_knee, R_ank)

    min_knee = min(left_knee, right_knee)
    knee_diff = abs(left_knee - right_knee)

    body_line = angle(sh_mid, hip_mid, knee_mid)

    shoulder_w = dist(L_sh, R_sh)
    feet_w = dist(L_foot, R_foot)
    stance_ratio = feet_w / (shoulder_w + 1e-6)

    hip_depth = float(hip_mid[1] - knee_mid[1])

    return np.array(
        [min_knee, knee_diff, body_line, stance_ratio, left_knee, right_knee, hip_depth],
        dtype=np.float32
    )