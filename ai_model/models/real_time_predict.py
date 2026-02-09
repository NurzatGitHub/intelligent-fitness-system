# unified_realtime_analysis.py
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import os
import time
import urllib.request
import joblib

def load_ml_model(model_path):
    """Загружает ML модель для анализа"""
    if os.path.exists(model_path):
        try:
            model = joblib.load(model_path)
            print(f"✅ ML модель загружена: {os.path.basename(model_path)}")
            print(f"   Признаков: {model.n_features_in_}")
            print(f"   Классы: {model.classes_}")
            return model
        except Exception as e:
            print(f"❌ Ошибка загрузки модели: {e}")
    else:
        print(f"⚠️ ML модель не найдена: {model_path}")
    
    return None

def extract_5_features_for_model(landmarks):
    """
    Извлекает 5 признаков для модели (ваши оригинальные признаки):
    1. Минимальный угол локтя (нормализованный 0-1)
    2. Симметрия плеч (разница по Y)
    3. Симметрия локтей (разница по X)
    4. Прямая спина
    5. Глубина отжимания (отношение к 90°)
    """
    if len(landmarks) < 17:
        return None
    
    try:
        features = []
        
        # 1. Углы локтей
        def calculate_angle(a, b, c):
            a = np.array([a.x, a.y])
            b = np.array([b.x, b.y])
            c = np.array([c.x, c.y])
            
            ba = a - b
            bc = c - b
            
            cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
            angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
            return np.degrees(angle)
        
        left_angle = calculate_angle(landmarks[11], landmarks[13], landmarks[15])
        right_angle = calculate_angle(landmarks[12], landmarks[14], landmarks[16])
        
        # Признак 1: Минимальный угол локтя (нормализованный 0-1)
        min_angle = min(left_angle, right_angle)
        features.append(min_angle / 180.0)
        
        # Признак 2: Симметрия плеч (разница по Y)
        shoulder_diff = abs(landmarks[11].y - landmarks[12].y)
        features.append(shoulder_diff)
        
        # Признак 3: Симметрия локтей
        # Разница в расстоянии от локтей до противоположных плеч
        left_dist = abs(landmarks[13].x - landmarks[12].x)  # левый локоть до правого плеча
        right_dist = abs(landmarks[14].x - landmarks[11].x)  # правый локоть до левого плеча
        elbow_diff = abs(left_dist - right_dist)
        features.append(elbow_diff)
        
        # Признак 4: Прямая спина
        # Разница в X координатах средних точек плеч и бедер
        shoulder_mid_x = (landmarks[11].x + landmarks[12].x) / 2
        
        if len(landmarks) > 24:
            hip_mid_x = (landmarks[23].x + landmarks[24].x) / 2
            back_straightness = abs(shoulder_mid_x - hip_mid_x)
        else:
            back_straightness = 0.0
        features.append(back_straightness)
        
        # Признак 5: Глубина отжимания (отношение к 90°)
        depth_ratio = min_angle / 90.0 if min_angle > 0 else 1.0
        features.append(depth_ratio)
        
        return np.array(features), min_angle, left_angle, right_angle
        
    except Exception as e:
        print(f"Ошибка извлечения признаков: {e}")
        return None, 0, 0, 0

def get_feedback_from_5_features(features, min_angle, left_angle, right_angle):
    """
    Генерирует обратную связь из 5 признаков (ваши оригинальные правила)
    """
    feedback = []
    
    if features is None or len(features) < 5:
        return ["⚠️ Не удалось извлечь признаки"]
    
    # Пороги из вашего model_info_5features.txt
    THRESHOLDS = {
        'elbow_angle': 45,      # угол < 45°: too wide
        'shoulder_diff': 0.05,  # > 0.05: uneven
        'elbow_diff': 0.1,      # > 0.1: asymmetric
        'back_straight': 0.15,  # > 0.15: arched back
        'depth_ratio': 1.1      # > 1.1: not deep enough
    }
    
    # 1. Проверка локтей (не должны расходиться в стороны)
    if left_angle < THRESHOLDS['elbow_angle'] or right_angle < THRESHOLDS['elbow_angle']:
        feedback.append("⚠️ Локти слишком широко!")
    
    # 2. Проверка симметрии плеч
    if features[1] > THRESHOLDS['shoulder_diff']:  # shoulder_diff
        feedback.append("⚠️ Плечи не на одном уровне!")
    
    # 3. Проверка симметрии локтей
    if features[2] > THRESHOLDS['elbow_diff']:  # elbow_diff
        feedback.append("⚠️ Локти асимметричны!")
    
    # 4. Проверка прямой спины
    if features[3] > THRESHOLDS['back_straight']:  # back_straightness
        feedback.append("⚠️ Спина не прямая!")
    
    # 5. Проверка глубины
    if features[4] > THRESHOLDS['depth_ratio']:  # depth_ratio
        feedback.append("⚠️ Опускайтесь глубже!")
    
    # Положительная обратная связь
    if not feedback:
        if min_angle <= 95:
            feedback.append("✅ Отличная техника!")
        elif min_angle <= 110:
            feedback.append("👍 Хорошо, можно опуститься чуть ниже")
    
    return feedback

def download_pose_model():
    """Скачивает модель pose_landmarker.task"""
    model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
    model_path = r"C:\AI Fitnes\models\pose_landmarker.task"
    
    if not os.path.exists(model_path):
        print("📥 Скачиваю модель pose_landmarker...")
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            urllib.request.urlretrieve(model_url, model_path)
            print(f"✅ Модель скачана")
        except Exception as e:
            print(f"❌ Ошибка скачивания: {e}")
            return None
    
    return model_path

def init_pose_detector():
    """Инициализирует детектор позы"""
    try:
        pose_model_path = download_pose_model()
        
        if pose_model_path and os.path.exists(pose_model_path):
            base_options = python.BaseOptions(model_asset_path=pose_model_path)
        else:
            base_options = python.BaseOptions(model_asset_path=None)
        
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        return vision.PoseLandmarker.create_from_options(options)
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")
        return None

def analyze_frame(pose_detector, frame, ml_model=None):
    """Анализирует один кадр с 5 признаками"""
    # Конвертируем BGR в RGB
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Создаем MediaPipe Image
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
    
    # Детектируем позу
    detection_result = pose_detector.detect(mp_image)
    
    feedback = []
    ml_prediction = None
    ml_confidence = 0.0
    
    if detection_result.pose_landmarks:
        landmarks = detection_result.pose_landmarks[0]
        
        # Извлекаем 5 признаков
        features, min_angle, left_angle, right_angle = extract_5_features_for_model(landmarks)
        
        # Генерируем обратную связь из 5 признаков
        feedback = get_feedback_from_5_features(features, min_angle, left_angle, right_angle)
        
        # Используем ML модель если есть
        if ml_model is not None and features is not None:
            try:
                # Проверяем совместимость признаков
                if len(features) == ml_model.n_features_in_:
                    ml_prediction = ml_model.predict([features])[0]
                    if hasattr(ml_model, 'predict_proba'):
                        ml_probabilities = ml_model.predict_proba([features])[0]
                        ml_confidence = max(ml_probabilities)
                    
                    # Добавляем ML feedback
                    if ml_prediction == 'incorrect' and ml_confidence > 0.6:
                        feedback.insert(0, f"🤖 ML: Ошибки ({ml_confidence:.1%})")
                    elif ml_prediction == 'correct' and ml_confidence > 0.7:
                        feedback.insert(0, f"🤖 ML: Правильно ({ml_confidence:.1%})")
                else:
                    # Если не совпадает количество признаков, используем только rule-based
                    print(f"⚠️ Модель ожидает {ml_model.n_features_in_} признаков, получено {len(features)}")
                    
            except Exception as e:
                print(f"Ошибка предсказания ML: {e}")
        
        return feedback, left_angle, right_angle, min_angle, ml_prediction, ml_confidence, features
    
    return ["⚠️ Поза не обнаружена"], 0, 0, 0, None, 0.0, None

def main():
    """Главная функция"""
    print("=" * 70)
    print("🤖 UNIFIED REAL-TIME PUSHUP ANALYSIS (5 FEATURES)")
    print("=" * 70)
    print("🎯 Использует 5 признаков:")
    print("   1. Угол локтей (нормализованный 0-1)")
    print("   2. Симметрия плеч (разница по Y)")
    print("   3. Симметрия локтей (разница по X)")
    print("   4. Прямая спина")
    print("   5. Глубина отжимания (отношение к 90°)")
    print("=" * 70)
    
    # Пробуем загрузить разные модели
    model_paths = [
        r"C:\AI Fitnes\models\realtime_pushup_model.pkl",  # 5 признаков
        # r"C:\AI Fitnes\models\realtime_model.pkl",          # 3 признака
        # r"C:\AI Fitnes\models\simple_effective_model.pkl",  # 3 признака
    ]
    
    ml_model = None
    for path in model_paths:
        ml_model = load_ml_model(path)
        if ml_model is not None:
            break
    
    if ml_model is None:
        print("⚠️ Будет использоваться только rule-based анализ")
    
    # Инициализация детектора позы
    print("\n🔧 Инициализация MediaPipe...")
    pose_detector = init_pose_detector()
    
    if pose_detector is None:
        print("❌ Не удалось инициализировать детектор позы")
        return
    
    # Путь к видео
    video_path = r"C:\AI Fitnes\models\push_up.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Видео не найдено: {video_path}")
        pose_detector.close()
        return
    
    print(f"📁 Анализирую видео: {os.path.basename(video_path)}")
    
    # Открываем видео
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print("❌ Не удалось открыть видео")
        pose_detector.close()
        return
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if fps == 0:
        fps = 30
    
    print(f"📊 FPS: {fps:.1f}, Всего кадров: {total_frames}")
    print("\n🚀 НАЧИНАЮ АНАЛИЗ...")
    print("-" * 50)
    
    # Статистика
    frame_count = 0
    rep_count = 0
    last_phase = "UP"
    last_print_time = time.time()
    
    # Для оценки
    ml_predictions = []
    rule_feedbacks = []
    all_features = []
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Анализируем каждый 3-й кадр
            if frame_count % 3 != 0:
                frame_count += 1
                continue
            
            # Анализ кадра с 5 признаками
            feedback, left_angle, right_angle, min_angle, ml_pred, ml_conf, features = analyze_frame(
                pose_detector, frame, ml_model
            )
            
            # Сохраняем признаки для анализа
            if features is not None:
                all_features.append(features)
            
            # Статистика ML
            if ml_pred is not None:
                ml_predictions.append(ml_pred)
            
            # Сохраняем feedback
            rule_feedbacks.extend(feedback)
            
            # Определяем фазу
            if min_angle <= 90:
                current_phase = "DOWN"
            elif min_angle >= 160:
                current_phase = "UP"
            else:
                current_phase = "TRANSITION"
            
            # Считаем повторения
            if last_phase == "UP" and current_phase == "DOWN":
                # Начали опускаться
                pass
            elif last_phase == "DOWN" and current_phase == "UP":
                # Завершили повторение
                rep_count += 1
            
            last_phase = current_phase
            
            # Выводим результат каждые 0.5 секунд
            current_time = time.time()
            if current_time - last_print_time >= 0.5:
                print(f"\n📊 Кадр {frame_count}/{total_frames}")
                print(f"   Углы: Л={left_angle:.0f}°, П={right_angle:.0f}° (мин: {min_angle:.0f}°)")
                print(f"   Фаза: {current_phase}")
                print(f"   Повторения: {rep_count}")
                
                if ml_pred is not None:
                    status = "✅" if ml_pred == 'correct' else "❌"
                    print(f"   ML: {status} {ml_pred} ({ml_conf:.1%})")
                
                if feedback:
                    for msg in feedback[:2]:  # Максимум 2 сообщения
                        print(f"   {msg}")
                
                # Показываем значения признаков (для отладки)
                if features is not None and frame_count % 50 == 0:
                    print(f"   Признаки: угол={features[0]:.3f}, плечи={features[1]:.3f}, "
                          f"локти={features[2]:.3f}, спина={features[3]:.3f}, глубина={features[4]:.3f}")
                
                last_print_time = current_time
            
            frame_count += 1
            
            # Прогресс
            if frame_count % 100 == 0:
                print(f"⏳ Прогресс: {frame_count}/{total_frames} кадров")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Анализ остановлен")
    
    finally:
        cap.release()
        pose_detector.close()
    
    # Итоговая статистика
    print("\n" + "=" * 50)
    print(f"🏁 АНАЛИЗ ЗАВЕРШЕН")
    print("=" * 50)
    
    print(f"📊 БАЗОВЫЕ РЕЗУЛЬТАТЫ:")
    print(f"   Всего кадров: {frame_count}")
    print(f"   Повторений: {rep_count}")
    
    # Анализ признаков
    if all_features:
        all_features = np.array(all_features)
        print(f"\n📈 СТАТИСТИКА ПРИЗНАКОВ:")
        print(f"   Анализировано кадров: {len(all_features)}")
        print(f"   Средние значения признаков:")
        print(f"     • Угол (0-1): {np.mean(all_features[:, 0]):.3f}")
        print(f"     • Симметрия плеч: {np.mean(all_features[:, 1]):.3f}")
        print(f"     • Симметрия локтей: {np.mean(all_features[:, 2]):.3f}")
        print(f"     • Прямая спина: {np.mean(all_features[:, 3]):.3f}")
        print(f"     • Глубина: {np.mean(all_features[:, 4]):.3f}")
    
    # Статистика ML
    if ml_predictions:
        correct_count = ml_predictions.count('correct')
        incorrect_count = ml_predictions.count('incorrect')
        
        print(f"\n📊 СТАТИСТИКА ML МОДЕЛИ:")
        print(f"   Предсказаний: {len(ml_predictions)}")
        print(f"   Correct: {correct_count}")
        print(f"   Incorrect: {incorrect_count}")
        
        if len(ml_predictions) > 0:
            accuracy = correct_count / len(ml_predictions)
            print(f"   Точность: {accuracy:.1%}")
    
    # Анализ feedback
    if rule_feedbacks:
        from collections import Counter
        feedback_counts = Counter(rule_feedbacks)
        
        print(f"\n📝 ЧАСТОТА ОБРАТНОЙ СВЯЗИ:")
        for feedback, count in feedback_counts.most_common(5):
            if "ML:" not in feedback:  # Пропускаем ML feedback
                print(f"   • {feedback}: {count}")
    
    # Оценка видео
    print(f"\n🎯 ОЦЕНКА ВИДЕО:")
    if rep_count > 0:
        print(f"   ✅ Видео содержит {rep_count} отжиманий")
        
        # Проверяем средний угол
        if all_features.size > 0:
            avg_angle = np.mean(all_features[:, 0]) * 180  # Конвертируем обратно в градусы
            if 80 <= avg_angle <= 100:
                print(f"   ✅ Средний угол хороший: {avg_angle:.0f}°")
            elif avg_angle < 80:
                print(f"   ⚠️ Средний угол мал: {avg_angle:.0f}° (возможно широко)")
            else:
                print(f"   ⚠️ Средний угол велик: {avg_angle:.0f}° (возможно мелко)")
    else:
        print(f"   ⚠️ Не обнаружено полных отжиманий")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    print(f"   1. Использовать модель на 5 признаков для точности")
    print(f"   2. Правила работают всегда, даже без ML модели")
    print(f"   3. Для лучших результатов нужна модель на 5 признаков")
    
    print("\n👋 Готово!")

if __name__ == "__main__":
    main()