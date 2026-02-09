import json
import numpy as np
import joblib
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from collections import deque
import asyncio

# ===== Настройка =====
MODEL_PATH = r"C:\AI Fitnes\models\simple_effective_model.pkl"
model = joblib.load(MODEL_PATH)
logger = logging.getLogger("pushup_analyzer")

app = FastAPI(title="PushUp Analyzer API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== State management =====
class PushupAnalyzer:
    def __init__(self, buffer_size=5):
        self.angle_buffer = deque(maxlen=buffer_size)
        self.width_buffer = deque(maxlen=buffer_size)
        self.prev_wrist_y = None
        self.phase = "unknown"
        self.rep_count = 0
        self.last_phase = None
        
    def normalize_keypoints(self, keypoints):
        """Нормализация ключевых точек"""
        kps = np.array([[kp['x'], kp['y']] for kp in keypoints[:17]])
        shoulder_dist = np.linalg.norm(kps[11] - kps[12])
        if shoulder_dist < 0.01:
            return None
        return kps / shoulder_dist
    
    def extract_features(self, keypoints):
        """Извлечение признаков с нормализацией"""
        kps_norm = self.normalize_keypoints(keypoints)
        if kps_norm is None:
            return None
        
        def angle(a_idx, b_idx, c_idx):
            a, b, c = kps_norm[a_idx], kps_norm[b_idx], kps_norm[c_idx]
            ba, bc = a - b, c - b
            cos = np.dot(ba, bc) / (np.linalg.norm(ba)*np.linalg.norm(bc) + 1e-6)
            return np.degrees(np.arccos(np.clip(cos, -1, 1)))
        
        left = angle(11, 13, 15)
        right = angle(12, 14, 16)
        
        # Сглаживание
        self.angle_buffer.append(min(left, right))
        self.width_buffer.append(
            abs(kps_norm[13][0] - kps_norm[14][0]) / 
            max(abs(kps_norm[11][0] - kps_norm[12][0]), 0.01)
        )
        
        smooth_angle = np.mean(self.angle_buffer) if self.angle_buffer else min(left, right)
        smooth_width = np.mean(self.width_buffer) if self.width_buffer else 1.0
        
        return [smooth_angle, smooth_width, abs(left - right)]
    
    def detect_phase_and_count(self, keypoints):
        """Определение фазы и подсчет повторений"""
        wrist_y = (keypoints[15]['y'] + keypoints[16]['y']) / 2
        
        if self.prev_wrist_y is None:
            self.prev_wrist_y = wrist_y
            return "starting"
        
        delta = wrist_y - self.prev_wrist_y
        self.prev_wrist_y = wrist_y
        
        if delta > 0.015:
            new_phase = "down"
        elif delta < -0.015:
            new_phase = "up"
        else:
            new_phase = self.phase
        
        # Подсчет повторений (смена down -> up)
        if self.phase == "down" and new_phase == "up":
            self.rep_count += 1
        
        self.phase = new_phase
        return self.phase
    
    def get_feedback(self, features, phase):
        """Генерация обратной связи"""
        angle, width, diff = features
        
        feedback = []
        
        if phase == "down" and angle < 70:
            feedback.append("Слишком широко в нижней точке!")
        elif phase == "down" and angle > 120:
            feedback.append("Опускайтесь глубже!")
        elif width > 1.5:
            feedback.append("Локти слишком далеко от тела")
        elif diff > 20:
            feedback.append("Держите симметрию")
        elif 80 <= angle <= 100 and 0.9 <= width <= 1.3:
            feedback.append("✅ Идеально!")
        
        return " | ".join(feedback) if feedback else "Продолжайте в том же духе"

# ===== WebSocket endpoint =====
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    logger.info("🟢 Client connected")
    
    analyzer = PushupAnalyzer(buffer_size=5)
    
    try:
        while True:
            data = await ws.receive_text()
            payload = json.loads(data)
            
            keypoints = payload.get("keypoints")
            if not keypoints or len(keypoints) < 17:
                await ws.send_json({"error": "invalid_keypoints"})
                continue
            
            # Извлечение признаков
            features = analyzer.extract_features(keypoints)
            if features is None:
                await ws.send_json({"error": "feature_extraction_failed"})
                continue
            
            # Анализ
            phase = analyzer.detect_phase_and_count(keypoints)
            pred = model.predict([features])[0]
            proba = model.predict_proba([features])[0]
            confidence = float(np.max(proba))
            feedback = analyzer.get_feedback(features, phase)
            
            # Ответ
            response = {
                "prediction": pred,
                "confidence": round(confidence, 3),
                "phase": phase,
                "rep_count": analyzer.rep_count,
                "features": {
                    "angle": round(features[0], 1),
                    "width_ratio": round(features[1], 2),
                    "symmetry": round(features[2], 1)
                },
                "feedback": feedback,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            await ws.send_json(response)
            
    except WebSocketDisconnect:
        logger.info("🔴 Client disconnected")
    except Exception as e:
        logger.error(f"Error in WebSocket: {e}")
        await ws.close(code=1011)

# ===== REST Endpoints =====
@app.get("/")
async def root():
    return {"message": "PushUp Analyzer API", "status": "running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)