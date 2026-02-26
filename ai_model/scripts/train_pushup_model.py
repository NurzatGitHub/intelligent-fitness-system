import os
import joblib
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

from ai_model.scripts.dataset_extractor_pushup import build_dataset

CORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\pushup_dataset\videos\correct"
INCORRECT_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\data\pushup_dataset\videos\incorrect"
MODELS_DIR = r"C:\Fitness\intelligent-fitness-system\ai_model\models"
MODEL_PATH = os.path.join(MODELS_DIR, "pushup_model.pkl")

os.makedirs(MODELS_DIR, exist_ok=True)

def train_and_save():
    X, y = build_dataset(CORRECT_DIR, INCORRECT_DIR)

    if len(X) < 10:
        raise RuntimeError("Too few samples extracted. Check video quality / pose detection.")

    classes = np.unique(y)
    print("[INFO] Classes in dataset:", classes)

    if len(classes) < 2:
        raise RuntimeError(
            f"Dataset has only one class: {classes}. "
            "Fix extraction (see SKIP logs) before training."
        )

    print(f"Samples: {len(y)} | correct={np.sum(y=='correct')} incorrect={np.sum(y=='incorrect')}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        class_weight="balanced",
        random_state=42
    )

    model.fit(X_train, y_train)

    print("\nTrain acc:", model.score(X_train, y_train))
    print("Test  acc:", model.score(X_test, y_test))
    print("\nConfusion Matrix:")
    print(confusion_matrix(y_test, model.predict(X_test)))
    print("\nReport:")
    print(classification_report(y_test, model.predict(X_test)))

    joblib.dump(model, MODEL_PATH)
    print(f"\n✅ Model saved: {MODEL_PATH}")

if __name__ == "__main__":
    train_and_save()
