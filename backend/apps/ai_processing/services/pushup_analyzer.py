import pickle
import cv2
import mediapipe as mp

class PushupAnalyzer:
    def __init__(self, model_path='pushup_model.pkl'):
        # Загружаем модель 
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # MediaPipe для позы
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
    
    def extract_keypoints(self, frame):
        # Конвертируем кадр
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Извлекаем ключевые точки
        results = self.pose.process(rgb_frame)
        
        if results.pose_landmarks:
            keypoints = []
            for landmark in results.pose_landmarks.landmark:
                keypoints.append([landmark.x, landmark.y, landmark.z])
            return keypoints
        return None
    
    def analyze_frame(self, frame):
        # 1. Извлекаем ключевые точки
        keypoints = self.extract_keypoints(frame)
        
        if keypoints is None:
            return {"error": "No person detected"}
        
        # 2. Преобразуем для модели (зависит от его модели)
        features = self.prepare_features(keypoints)
        
        # 3. Предсказываем
        prediction = self.model.predict([features])
        
        return {
            "exercise": "pushup",
            "count": prediction.get('count', 0),
            "errors": prediction.get('errors', []),
            "feedback": prediction.get('feedback', ""),
            "score": prediction.get('score', 0)
        }