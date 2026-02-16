from pathlib import Path
import joblib

MODEL_PATH = Path(__file__).resolve().parent / "ml_models" / "pushup_model.pkl"
_model = None

def get_model():
    global _model
    if _model is None:
        _model = joblib.load(MODEL_PATH)
    return _model
