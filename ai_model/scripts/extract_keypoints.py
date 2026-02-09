# extract_keypoints_improved.py
import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import numpy as np
import json
import os
from tqdm import tqdm
import urllib.request
import time

def download_pose_model():
    """
    Скачивает модель pose_landmarker.task
    """
    model_url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/1/pose_landmarker_heavy.task"
    model_path = r"C:\AI Fitnes\models\pose_landmarker.task"
    
    if not os.path.exists(model_path):
        print("📥 Скачиваю модель pose_landmarker...")
        try:
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            urllib.request.urlretrieve(model_url, model_path)
            print("✅ Модель скачана!")
        except Exception as e:
            print(f"❌ Ошибка скачивания: {e}")
            print("⚠️  Будет использована встроенная модель")
            model_path = None
    
    return model_path

def check_pose_quality(landmarks, min_important_points=6, min_visibility=0.5):
    """
    Проверяет качество обнаруженной позы для отжиманий
    Возвращает True если поза достаточно качественная
    """
    if not landmarks or len(landmarks) < 17:
        return False
    
    # Ключевые точки для отжиманий (должны быть хорошо видны)
    important_indices = [11, 12, 13, 14, 15, 16, 23, 24]  # Плечи, локти, запястья, бедра
    
    visible_count = 0
    for idx in important_indices:
        if idx < len(landmarks) and landmarks[idx].visibility > min_visibility:
            visible_count += 1
    
    # Нужно видеть минимум N важных точек
    return visible_count >= min_important_points

def calculate_frame_score(landmarks):
    """
    Оценивает качество кадра по видимости ключевых точек
    Возвращает оценку от 0 до 1
    """
    if not landmarks:
        return 0.0
    
    # Веса для разных частей тела
    weights = {
        'shoulders': 0.3,    # Плечи
        'elbows': 0.3,       # Локти
        'wrists': 0.2,       # Запястья
        'hips': 0.2          # Бедра
    }
    
    # Индексы точек
    shoulder_indices = [11, 12]
    elbow_indices = [13, 14]
    wrist_indices = [15, 16]
    hip_indices = [23, 24]
    
    def get_avg_visibility(indices):
        total = 0
        count = 0
        for idx in indices:
            if idx < len(landmarks):
                total += landmarks[idx].visibility
                count += 1
        return total / max(count, 1)
    
    # Вычисляем видимость для каждой группы
    shoulder_vis = get_avg_visibility(shoulder_indices)
    elbow_vis = get_avg_visibility(elbow_indices)
    wrist_vis = get_avg_visibility(wrist_indices)
    hip_vis = get_avg_visibility(hip_indices)
    
    # Итоговая оценка
    score = (shoulder_vis * weights['shoulders'] +
             elbow_vis * weights['elbows'] +
             wrist_vis * weights['wrists'] +
             hip_vis * weights['hips'])
    
    return score

def extract_keypoints_with_quality(video_path, pose_landmarker, category, 
                                   min_quality_score=0.6, 
                                   max_frames_to_save=30):
    """
    Извлекает ключевые точки с контролем качества
    Для коротких видео (2-3 секунды) берет только лучшие кадры
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"    ❌ Не могу открыть видео")
        return None
    
    # Получаем параметры видео
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if fps == 0:
        fps = 30
    
    print(f"    📊 Кадров: {total_frames}, FPS: {fps:.1f}")
    
    # Для коротких видео: анализируем каждый кадр
    # Для длинных: анализируем каждый 2-3 кадр
    frame_skip = 1 if total_frames < 90 else 2  # < 3 секунд: каждый кадр
    
    all_keypoints = []
    frame_scores = []  # Для отбора лучших кадров
    frame_count = 0
    processed_count = 0
    
    print(f"    ⚙️  Пропуск кадров: каждый {frame_skip}-й")
    
    with tqdm(total=total_frames, desc="      ⏳ Обработка", unit="кадр") as pbar:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Пропускаем кадры если нужно
            if frame_count % frame_skip != 0:
                frame_count += 1
                pbar.update(1)
                continue
            
            # Конвертируем BGR в RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Создаем MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            
            # Детектируем позу
            detection_result = pose_landmarker.detect(mp_image)
            
            if detection_result.pose_landmarks:
                landmarks = detection_result.pose_landmarks[0]
                
                # Проверяем качество позы
                if check_pose_quality(landmarks):
                    # Оцениваем качество кадра
                    quality_score = calculate_frame_score(landmarks)
                    
                    # Сохраняем только кадры с хорошим качеством
                    if quality_score >= min_quality_score:
                        frame_keypoints = []
                        for idx, landmark in enumerate(landmarks):
                            point = {
                                "x": float(landmark.x),
                                "y": float(landmark.y),
                                "z": float(landmark.z),
                                "visibility": float(landmark.visibility),
                                "name": idx
                            }
                            frame_keypoints.append(point)
                        
                        all_keypoints.append({
                            "frame_number": frame_count,
                            "quality_score": quality_score,
                            "keypoints": frame_keypoints
                        })
                        
                        frame_scores.append((len(all_keypoints)-1, quality_score))
                        processed_count += 1
            
            frame_count += 1
            pbar.update(1)
            
            if frame_count % 10 == 0:
                pbar.set_description(f"      ⏳ Обработка: {frame_count}/{total_frames}")
    
    cap.release()
    
    if len(all_keypoints) == 0:
        print(f"    ❌ Не найдено качественных кадров")
        return None
    
    print(f"    ✅ Найдено кадров: {len(all_keypoints)} (из {total_frames})")
    
    # Для коротких видео берем все кадры
    # Для видео с большим количеством кадров отбираем лучшие
    if len(all_keypoints) > max_frames_to_save:
        print(f"    🎯 Отбираю {max_frames_to_save} лучших кадров из {len(all_keypoints)}")
        
        # Сортируем по качеству
        frame_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Берем лучшие кадры
        best_indices = [idx for idx, _ in frame_scores[:max_frames_to_save]]
        best_indices.sort()  # Сохраняем временной порядок
        
        all_keypoints = [all_keypoints[i] for i in best_indices]
    
    return all_keypoints

def analyze_video_statistics(keypoints_data, category):
    """
    Анализирует статистику извлеченных ключевых точек
    """
    if not keypoints_data:
        return None
    
    stats = {
        'total_frames': len(keypoints_data),
        'avg_quality_score': 0.0,
        'avg_visibility': {
            'shoulders': 0.0,
            'elbows': 0.0,
            'wrists': 0.0,
            'hips': 0.0
        }
    }
    
    quality_scores = []
    visibility_counts = {'shoulders': 0, 'elbows': 0, 'wrists': 0, 'hips': 0}
    visibility_totals = {'shoulders': 0, 'elbows': 0, 'wrists': 0, 'hips': 0}
    
    for frame_data in keypoints_data:
        # Качество кадра
        quality_scores.append(frame_data.get('quality_score', 0.0))
        
        # Видимость ключевых точек
        keypoints = frame_data['keypoints']
        
        # Плечи (11, 12)
        if len(keypoints) > 12:
            stats['avg_visibility']['shoulders'] += (keypoints[11].get('visibility', 0) + 
                                                    keypoints[12].get('visibility', 0)) / 2
            visibility_counts['shoulders'] += 1
        
        # Локти (13, 14)
        if len(keypoints) > 14:
            stats['avg_visibility']['elbows'] += (keypoints[13].get('visibility', 0) + 
                                                 keypoints[14].get('visibility', 0)) / 2
            visibility_counts['elbows'] += 1
        
        # Запястья (15, 16)
        if len(keypoints) > 16:
            stats['avg_visibility']['wrists'] += (keypoints[15].get('visibility', 0) + 
                                                 keypoints[16].get('visibility', 0)) / 2
            visibility_counts['wrists'] += 1
        
        # Бедра (23, 24)
        if len(keypoints) > 24:
            stats['avg_visibility']['hips'] += (keypoints[23].get('visibility', 0) + 
                                               keypoints[24].get('visibility', 0)) / 2
            visibility_counts['hips'] += 1
    
    # Средние значения
    if quality_scores:
        stats['avg_quality_score'] = sum(quality_scores) / len(quality_scores)
    
    for part in stats['avg_visibility']:
        if visibility_counts[part] > 0:
            stats['avg_visibility'][part] /= visibility_counts[part]
    
    return stats

def process_folder_with_quality(folder_path, category, output_dir):
    """
    Обрабатывает все видео в папке с контролем качества
    """
    # Ищем видеофайлы
    video_extensions = ('.mp4', '.avi', '.mov', '.MP4', '.MOV', '.mkv', '.flv')
    video_files = []
    
    for f in os.listdir(folder_path):
        if any(f.lower().endswith(ext) for ext in video_extensions):
            video_files.append(f)
    
    if not video_files:
        print(f"  ✗ Нет видеофайлов в папке")
        return 0, 0, []
    
    print(f"  📹 Найдено видео: {len(video_files)}")
    
    # Инициализация нового API MediaPipe
    print("  🔧 Инициализация нового MediaPipe API...")
    
    try:
        model_path = download_pose_model()
        
        # Создаем опции
        base_options = python.BaseOptions(model_asset_path=model_path)
        
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
            num_poses=1,
            min_pose_detection_confidence=0.7,  # Повышаем уверенность
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7,
            output_segmentation_masks=False
        )
        
        # Создаем landmarker
        pose_landmarker = vision.PoseLandmarker.create_from_options(options)
        print("  ✅ Новый API MediaPipe инициализирован")
        
    except Exception as e:
        print(f"  ❌ Ошибка инициализации нового API: {e}")
        print("  ⚠️  Переключитесь на старый метод")
        return 0, 0, []
    
    processed_count = 0
    failed_count = 0
    all_stats = []
    
    for i, video_file in enumerate(video_files, 1):
        video_path = os.path.join(folder_path, video_file)
        
        print(f"\n  [{i}/{len(video_files)}] 🚀 Видео: {video_file}")
        
        try:
            # Извлекаем ключевые точки с контролем качества
            keypoints = extract_keypoints_with_quality(video_path, pose_landmarker, category)
            
            if keypoints and len(keypoints) > 0:
                # Анализируем статистику
                stats = analyze_video_statistics(keypoints, category)
                
                # Формируем имя файла
                base_name = os.path.splitext(video_file)[0]
                
                # Убираем префикс категории, если уже есть
                if base_name.startswith('correct_'):
                    base_name = base_name[8:]
                elif base_name.startswith('incorrect_'):
                    base_name = base_name[10:]
                
                output_filename = f"{category}_{base_name}.json"
                output_path = os.path.join(output_dir, output_filename)
                
                # Сохраняем результат с метаданными
                save_data = {
                    "video_file": video_file,
                    "video_path": video_path,
                    "category": category,
                    "total_frames": len(keypoints),
                    "extraction_date": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "quality_stats": stats,
                    "keypoints": keypoints
                }
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, indent=2, ensure_ascii=False)
                
                print(f"    💾 Сохранено: {output_filename}")
                print(f"    📊 Качество: {stats['avg_quality_score']:.3f}")
                print(f"    👁️  Видимость: Плечи={stats['avg_visibility']['shoulders']:.3f}, "
                      f"Локти={stats['avg_visibility']['elbows']:.3f}")
                
                processed_count += 1
                all_stats.append(stats)
            else:
                print(f"    ❌ Пропускаю (не найдено качественных кадров)")
                failed_count += 1
                
        except Exception as e:
            print(f"    ❌ Ошибка: {str(e)}")
            failed_count += 1
    
    # Закрываем landmarker
    pose_landmarker.close()
    
    return processed_count, failed_count, all_stats

def print_summary_stats(all_stats, category):
    """Выводит сводную статистику по категории"""
    if not all_stats:
        return
    
    total_frames = sum(stats['total_frames'] for stats in all_stats)
    avg_quality = sum(stats['avg_quality_score'] for stats in all_stats) / len(all_stats)
    
    # Средняя видимость по всем видео
    avg_visibility = {'shoulders': 0.0, 'elbows': 0.0, 'wrists': 0.0, 'hips': 0.0}
    for part in avg_visibility:
        avg_visibility[part] = sum(stats['avg_visibility'][part] for stats in all_stats) / len(all_stats)
    
    print(f"\n  📈 СВОДНАЯ СТАТИСТИКА '{category.upper()}':")
    print(f"     Всего кадров: {total_frames}")
    print(f"     Среднее качество: {avg_quality:.3f}")
    print(f"     Средняя видимость:")
    print(f"       • Плечи: {avg_visibility['shoulders']:.3f}")
    print(f"       • Локти: {avg_visibility['elbows']:.3f}")
    print(f"       • Запястья: {avg_visibility['wrists']:.3f}")
    print(f"       • Бедра: {avg_visibility['hips']:.3f}")

def main():
    print("=" * 70)
    print("🎯 EXTRACT KEYPOINTS - УЛУЧШЕННАЯ ВЕРСИЯ С КОНТРОЛЕМ КАЧЕСТВА")
    print("=" * 70)
    print("⚠️  Особенности:")
    print("   • Контроль качества кадров")
    print("   • Отбор только лучших кадров")
    print("   • Статистика видимости ключевых точек")
    print("   • Оптимизация для коротких видео (2-3 секунды)")
    print("=" * 70)
    
    # Настройки путей
    base_dir = r"C:\AI Fitnes\data\pushup_dataset"
    videos_base_dir = os.path.join(base_dir, "videos")
    output_dir = os.path.join(base_dir, "keypoints")
    
    # Проверяем папки
    if not os.path.exists(videos_base_dir):
        print(f"❌ Папка не найдена: {videos_base_dir}")
        return
    
    # Создаем выходную папку
    os.makedirs(output_dir, exist_ok=True)
    
    total_processed = 0
    total_failed = 0
    all_categories_stats = {}
    
    # Обрабатываем ОБЕ папки автоматически
    folders_to_process = [
        ("correct", os.path.join(videos_base_dir, "correct")),
        ("incorrect", os.path.join(videos_base_dir, "incorrect"))
    ]
    
    for category_name, folder_path in folders_to_process:
        print(f"\n{'='*60}")
        print(f"📁 ПАПКА: {category_name.upper()}")
        print(f"📂 Путь: {folder_path}")
        print(f"{'='*60}")
        
        if not os.path.exists(folder_path):
            print(f"⚠️  Папка не найдена, пропускаю...")
            continue
        
        processed, failed, stats = process_folder_with_quality(
            folder_path, category_name, output_dir
        )
        
        total_processed += processed
        total_failed += failed
        all_categories_stats[category_name] = stats
        
        print(f"\n  📊 Итог по папке '{category_name}':")
        print(f"    Успешно: {processed}")
        print(f"    Ошибок: {failed}")
        
        # Выводим статистику для этой категории
        if stats:
            print_summary_stats(stats, category_name)
    
    # Итоговая статистика
    print("\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЙ ИТОГ")
    print("=" * 70)
    
    # Считаем файлы по категориям
    if os.path.exists(output_dir):
        json_files = [f for f in os.listdir(output_dir) if f.endswith('.json')]
        correct_files = [f for f in json_files if f.startswith('correct_')]
        incorrect_files = [f for f in json_files if f.startswith('incorrect_')]
        
        print(f"\n📁 Папка с результатами: {output_dir}")
        print(f"📄 Всего JSON файлов: {len(json_files)}")
        print(f"   ✅ correct: {len(correct_files)}")
        print(f"   ❌ incorrect: {len(incorrect_files)}")
        
        # Анализируем общую статистику
        if all_categories_stats:
            print(f"\n📈 ОБЩАЯ СТАТИСТИКА КАЧЕСТВА:")
            
            for category, stats_list in all_categories_stats.items():
                if stats_list:
                    total_frames = sum(s['total_frames'] for s in stats_list)
                    avg_quality = sum(s['avg_quality_score'] for s in stats_list) / len(stats_list)
                    print(f"   {category.upper()}: {len(stats_list)} видео, "
                          f"{total_frames} кадров, качество: {avg_quality:.3f}")
        
        if len(correct_files) > 0 and len(incorrect_files) > 0:
            print(f"\n🎉 ОТЛИЧНО! Качественные данные собраны!")
            print(f"   Теперь можно обучать улучшенную модель:")
            print(f"   python train_model_improved.py")
        elif len(json_files) > 0:
            print(f"\n⚠️  Есть данные только одного типа")
            print(f"   Добавьте видео другого типа в папку videos/")
        else:
            print(f"\n❌ Нет обработанных данных")
    else:
        print(f"❌ Папка с результатами не создана")
    
    print(f"\n✅ Обработка завершена!")
    print(f"📊 Итого: {total_processed} успешно, {total_failed} ошибок")

if __name__ == "__main__":
    main()