# train_simple_model.py
import json
import numpy as np
import os
from sklearn.ensemble import RandomForestClassifier
import joblib

def extract_simple_but_effective_features(keypoints):
    """
    3 ПРОСТЫХ и ЭФФЕКТИВНЫХ признака:
    1. Угол локтей (градусы)
    2. Ширина локтей относительно плеч
    3. Симметрия (разница углов)
    """
    if len(keypoints) < 17:
        return None
    
    features = []
    
    # 1. Углы локтей
    def calculate_angle(a, b, c):
        a = np.array([a['x'], a['y']])
        b = np.array([b['x'], b['y']])
        c = np.array([c['x'], c['y']])
        
        ba = a - b
        bc = c - b
        
        cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.arccos(np.clip(cosine_angle, -1.0, 1.0))
        return np.degrees(angle)
    
    left_angle = calculate_angle(keypoints[11], keypoints[13], keypoints[15])
    right_angle = calculate_angle(keypoints[12], keypoints[14], keypoints[16])
    
    # Признак 1: Минимальный угол (90° идеально)
    min_angle = min(left_angle, right_angle)
    features.append(min_angle)  # В градусах!
    
    # Признак 2: Ширина локтей
    shoulder_width = abs(keypoints[11]['x'] - keypoints[12]['x'])
    elbow_width = abs(keypoints[13]['x'] - keypoints[14]['x'])
    if shoulder_width > 0:
        width_ratio = elbow_width / shoulder_width
    else:
        width_ratio = 1.0
    features.append(width_ratio)
    
    # Признак 3: Симметрия
    angle_diff = abs(left_angle - right_angle)
    features.append(angle_diff)
    
    return features

print("=" * 70)
print("🤖 ОБУЧЕНИЕ ПРОСТОЙ И ЭФФЕКТИВНОЙ МОДЕЛИ (3 признака)")
print("=" * 70)

keypoints_dir = r"C:\AI Fitnes\data\pushup_dataset\keypoints"

# 1. Загружаем
files = os.listdir(keypoints_dir)
correct_files = [f for f in files if f.lower().startswith('correct_')]
incorrect_files = [f for f in files if f.lower().startswith('incorrect_')]

print(f"📊 Файлов: correct={len(correct_files)}, incorrect={len(incorrect_files)}")

X, y = [], []

# Правильные - должны иметь угол ~90°
for f in correct_files:
    try:
        with open(os.path.join(keypoints_dir, f), 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if data.get('keypoints'):
            frames = data['keypoints']
            if len(frames) > 0:
                mid_idx = len(frames) // 2
                keypoints = frames[mid_idx]['keypoints']
                features = extract_simple_but_effective_features(keypoints)
                if features:
                    X.append(features)
                    y.append('correct')
    except:
        pass

# Неправильные - должны иметь угол <70 или >120
for f in incorrect_files:
    try:
        with open(os.path.join(keypoints_dir, f), 'r', encoding='utf-8') as file:
            data = json.load(file)
        
        if data.get('keypoints'):
            frames = data['keypoints']
            if len(frames) > 0:
                mid_idx = len(frames) // 2
                keypoints = frames[mid_idx]['keypoints']
                features = extract_simple_but_effective_features(keypoints)
                if features:
                    X.append(features)
                    y.append('incorrect')
    except:
        pass

print(f"\n✅ Загружено: {len(X)} примеров")
print(f"  • correct: {y.count('correct')}")
print(f"  • incorrect: {y.count('incorrect')}")

# Если мало данных, добавляем искусственные
if len(X) < 20:
    print("\n⚠️ Мало данных! Добавляю искусственные...")
    
    # Правильные: угол 85-95°, ширина 1.0-1.2, симметрия <15°
    for _ in range(30):
        X.append([np.random.uniform(85, 95), 
                 np.random.uniform(1.0, 1.2), 
                 np.random.uniform(0, 10)])
        y.append('correct')
    
    # Неправильные: 
    # 1. Широкие: угол 45-65°, широкая стойка
    for _ in range(15):
        X.append([np.random.uniform(45, 65), 
                 np.random.uniform(1.5, 2.0), 
                 np.random.uniform(5, 20)])
        y.append('incorrect')
    
    # 2. Мелкие: угол 130-150°
    for _ in range(15):
        X.append([np.random.uniform(130, 150), 
                 np.random.uniform(1.0, 1.3), 
                 np.random.uniform(0, 15)])
        y.append('incorrect')

X = np.array(X)
y = np.array(y)

print(f"\n📊 Итоговые данные: {len(X)} примеров")

# 2. Простое обучение (без сложной балансировки)
from sklearn.model_selection import train_test_split

# Оставляем максимум 50 примеров каждого класса для баланса
X_balanced, y_balanced = [], []

for class_name in ['correct', 'incorrect']:
    indices = np.where(y == class_name)[0]
    if len(indices) > 50:
        indices = indices[:50]
    
    X_balanced.extend(X[indices])
    y_balanced.extend(y[indices])

X = np.array(X_balanced)
y = np.array(y_balanced)

print(f"⚖️ После балансировки: correct={sum(y == 'correct')}, incorrect={sum(y == 'incorrect')}")

# 3. Обучение
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(
    n_estimators=50,  # Меньше деревьев для скорости
    max_depth=5,      # Неглубокие деревья
    random_state=42
)

model.fit(X_train, y_train)

train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test)

print(f"\n🎯 Результаты:")
print(f"  Точность на обучении: {train_acc:.3f}")
print(f"  Точность на тесте: {test_acc:.3f}")

# 4. Проверка
print(f"\n🧪 Проверка на тестовых примерах:")
test_cases = [
    ([90, 1.1, 5], "✅ Идеальный угол, нормальная ширина"),
    ([50, 1.8, 10], "❌ Слишком широко (угол мал)"),
    ([140, 1.2, 8], "❌ Слишком мелко (угол велик)"),
    ([85, 1.5, 25], "❌ Широко + асимметрия"),
]

for features, desc in test_cases:
    pred = model.predict([features])[0]
    proba = model.predict_proba([features])[0]
    confidence = max(proba)
    print(f"  {desc}: {pred} (уверенность: {confidence:.3f})")

# 5. Сохранение
models_dir = r"C:\AI Fitnes\models"
os.makedirs(models_dir, exist_ok=True)

model_path = os.path.join(models_dir, 'simple_effective_model.pkl')
joblib.dump(model, model_path)

print(f"\n💾 Модель сохранена: {model_path}")

# 6. Простые правила для real-time
print(f"\n📝 ПРОСТЫЕ ПРАВИЛА ДЛЯ REAL-TIME:")
print(f"   1. Если угол < 70° → 'Локти слишком широко!'")
print(f"   2. Если угол > 120° → 'Опускайтесь ниже!'")
print(f"   3. Если ширина > 1.5 → 'Локти слишком далеко!'")
print(f"   4. Если разница > 20° → 'Руки несимметричны!'")
print(f"   5. Если угол 80-100° и ширина 1.0-1.3 → '✅ Отлично!'")

print(f"\n🚀 Для тестирования запустите:")
print(f"python realtime_simple.py")