# check_features.py
import json
import numpy as np
import os

keypoints_dir = r"C:\AI Fitnes\data\pushup_dataset\keypoints"

# Проверим реальные значения признаков
def print_feature_stats(files, category):
    print(f"\n📊 {category.upper()} - реальные значения признаков:")
    
    angles = []
    shoulder_diffs = []
    elbow_diffs = []
    back_straightness = []
    depth_ratios = []
    
    for f in files[:5]:  # Проверяем первые 5 файлов
        try:
            with open(os.path.join(keypoints_dir, f), 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            if data.get('keypoints'):
                frames = data['keypoints']
                if len(frames) > 0:
                    mid_idx = len(frames) // 2
                    keypoints = frames[mid_idx]['keypoints']
                    
                    # Вычисляем признаки ВРУЧНУЮ
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
                    min_angle = min(left_angle, right_angle)
                    
                    angles.append(min_angle / 180.0)
                    shoulder_diffs.append(abs(keypoints[11]['y'] - keypoints[12]['y']))
                    
                    left_dist = abs(keypoints[13]['x'] - keypoints[12]['x'])
                    right_dist = abs(keypoints[14]['x'] - keypoints[11]['x'])
                    elbow_diffs.append(abs(left_dist - right_dist))
                    
                    shoulder_mid_x = (keypoints[11]['x'] + keypoints[12]['x']) / 2
                    if len(keypoints) > 24:
                        left_hip = keypoints[23]
                        right_hip = keypoints[24]
                        hip_mid_x = (left_hip['x'] + right_hip['x']) / 2
                        back_straightness.append(abs(shoulder_mid_x - hip_mid_x))
                    else:
                        back_straightness.append(0.0)
                    
                    depth_ratios.append(min_angle / 90.0 if min_angle > 0 else 1.0)
                    
        except:
            pass
    
    if angles:
        print(f"  Углы (0-1): {np.mean(angles):.3f} ± {np.std(angles):.3f}")
        print(f"  Симметрия плеч: {np.mean(shoulder_diffs):.3f} ± {np.std(shoulder_diffs):.3f}")
        print(f"  Симметрия локтей: {np.mean(elbow_diffs):.3f} ± {np.std(elbow_diffs):.3f}")
        print(f"  Спина: {np.mean(back_straightness):.3f} ± {np.std(back_straightness):.3f}")
        print(f"  Глубина: {np.mean(depth_ratios):.3f} ± {np.std(depth_ratios):.3f}")

# Проверим
files = os.listdir(keypoints_dir)
correct_files = [f for f in files if f.lower().startswith('correct_')]
incorrect_files = [f for f in files if f.lower().startswith('incorrect_')]

print("="*60)
print("ПРОВЕРКА РЕАЛЬНЫХ ПРИЗНАКОВ")
print("="*60)

print_feature_stats(correct_files[:5], 'correct')
print_feature_stats(incorrect_files[:5], 'incorrect')