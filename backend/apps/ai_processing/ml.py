from pathlib import Path
import joblib

MODEL_DIR = Path(__file__).resolve().parent / "ml_models"

MODEL_PATHS = {
    "push_up": MODEL_DIR / "pushup_model.pkl",
    "squat":   MODEL_DIR / "squat_model.pkl",
}

_cache = {}

def get_model(exercise: str = "push_up"):
    """
    push_up -> sklearn model (обычно RandomForest/…)
    squat   -> bundle dict: {"scaler": StandardScaler, "model": IsolationForest}
    """
    if exercise not in MODEL_PATHS:
        raise ValueError(f"unknown exercise: {exercise}")

    if exercise not in _cache:
        _cache[exercise] = joblib.load(MODEL_PATHS[exercise])

    return _cache[exercise]