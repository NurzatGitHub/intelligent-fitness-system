# evaluate_model.py
import joblib
import numpy as np
import os
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
import matplotlib.pyplot as plt
import seaborn as sns

def evaluate_model(model_path):
    """Тщательная оценка модели"""
    print("=" * 60)
    print("🤖 ТЩАТЕЛЬНАЯ ОЦЕНКА МОДЕЛИ")
    print("=" * 60)
    
    # Загружаем модель
    if not os.path.exists(model_path):
        print(f"❌ Модель не найдена: {model_path}")
        return
    
    model = joblib.load(model_path)
    
    print(f"✅ Модель загружена: {os.path.basename(model_path)}")
    print(f"📊 Алгоритм: {model.__class__.__name__}")
    print(f"📊 Ожидает признаков: {model.n_features_in_}")
    print(f"📊 Классы: {model.classes_}")
    print(f"📊 Количество деревьев: {model.n_estimators}")
    
    # Создаем тестовые данные для оценки
    print("\n" + "=" * 60)
    print("📊 ГЕНЕРАЦИЯ ТЕСТОВЫХ ДАННЫХ")
    print("=" * 60)
    
    # Создаем более разнообразные тестовые данные
    test_samples = 100
    
    # Правильные отжимания (разные варианты)
    correct_data = []
    for i in range(test_samples // 2):
        # Добавляем немного вариативности
        features = [
            np.random.uniform(0.4, 0.6),      # угол 72-108°
            np.random.uniform(0.01, 0.04),    # небольшая асимметрия
            np.random.uniform(0.03, 0.08),    # небольшая асимметрия локтей
            np.random.uniform(0.005, 0.02),   # почти прямая спина
            np.random.uniform(0.55, 0.65)     # глубина около 90°
        ]
        correct_data.append(features)
    
    # Неправильные отжимания (разные ошибки)
    incorrect_data = []
    for i in range(test_samples // 2):
        # Разные типы ошибок
        error_type = np.random.choice(['wide_elbows', 'uneven', 'shallow', 'arched_back'])
        
        if error_type == 'wide_elbows':
            features = [
                np.random.uniform(0.2, 0.4),    # широкие локти (36-72°)
                np.random.uniform(0.02, 0.05),
                np.random.uniform(0.15, 0.25),  # асимметрия
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.3, 0.5)
            ]
        elif error_type == 'uneven':
            features = [
                np.random.uniform(0.4, 0.6),
                np.random.uniform(0.08, 0.15),  # большая разница плеч
                np.random.uniform(0.2, 0.3),    # асимметрия локтей
                np.random.uniform(0.01, 0.03),
                np.random.uniform(0.5, 0.7)
            ]
        elif error_type == 'shallow':
            features = [
                np.random.uniform(0.7, 0.9),    # мелкие отжимания (126-162°)
                np.random.uniform(0.01, 0.04),
                np.random.uniform(0.03, 0.08),
                np.random.uniform(0.005, 0.02),
                np.random.uniform(0.8, 1.1)     # глубина > 90°
            ]
        else:  # arched_back
            features = [
                np.random.uniform(0.4, 0.6),
                np.random.uniform(0.02, 0.05),
                np.random.uniform(0.05, 0.1),
                np.random.uniform(0.2, 0.3),    # прогнутая спина
                np.random.uniform(0.5, 0.7)
            ]
        
        incorrect_data.append(features)
    
    X_test = np.array(correct_data + incorrect_data)
    y_test = np.array(['correct'] * (test_samples // 2) + ['incorrect'] * (test_samples // 2))
    
    print(f"📊 Создано тестовых примеров: {len(X_test)}")
    print(f"   • correct: {test_samples // 2}")
    print(f"   • incorrect: {test_samples // 2}")
    
    # Предсказания
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ПРЕДСКАЗАНИЙ")
    print("=" * 60)
    
    y_pred = model.predict(X_test)
    
    # Метрики
    accuracy = np.mean(y_pred == y_test)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='weighted')
    
    print(f"🎯 Точность (accuracy): {accuracy:.3f}")
    print(f"🎯 Precision: {precision:.3f}")
    print(f"🎯 Recall: {recall:.3f}")
    print(f"🎯 F1-Score: {f1:.3f}")
    
    # Матрица ошибок
    cm = confusion_matrix(y_test, y_pred, labels=model.classes_)
    
    print(f"\n📊 Матрица ошибок:")
    print(f"           Predicted")
    print(f"           {model.classes_[0]:<10} {model.classes_[1]:<10}")
    print(f"Actual {model.classes_[0]:<6} {cm[0, 0]:<10} {cm[0, 1]:<10}")
    print(f"       {model.classes_[1]:<6} {cm[1, 0]:<10} {cm[1, 1]:<10}")
    
    # Подробный отчет
    print("\n📊 Подробный отчет:")
    print(classification_report(y_test, y_pred, target_names=model.classes_))
    
    # Анализ важности признаков
    if hasattr(model, 'feature_importances_'):
        print("\n" + "=" * 60)
        print("📊 ВАЖНОСТЬ ПРИЗНАКОВ")
        print("=" * 60)
        
        feature_names = [
            "Угол локтя",
            "Симметрия плеч", 
            "Симметрия локтей",
            "Прямая спина",
            "Глубина"
        ]
        
        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]
        
        print("Рейтинг важности признаков:")
        for i, idx in enumerate(indices):
            print(f"{i+1}. {feature_names[idx]}: {importances[idx]:.3f}")
    
    # Тестовые примеры
    print("\n" + "=" * 60)
    print("🧪 ТЕСТОВЫЕ ПРИМЕРЫ")
    print("=" * 60)
    
    # Пример правильного отжимания
    good_example = np.array([[0.5, 0.02, 0.05, 0.01, 0.55]])  # Хорошая форма
    good_pred = model.predict(good_example)[0]
    good_proba = model.predict_proba(good_example)[0]
    
    print(f"✅ Пример правильного отжимания:")
    print(f"   Признаки: {good_example[0]}")
    print(f"   Предсказание: {good_pred}")
    print(f"   Вероятности: correct={good_proba[0]:.3f}, incorrect={good_proba[1]:.3f}")
    
    # Пример неправильного отжимания
    bad_example = np.array([[0.3, 0.15, 0.25, 0.2, 0.35]])  # Плохая форма
    bad_pred = model.predict(bad_example)[0]
    bad_proba = model.predict_proba(bad_example)[0]
    
    print(f"\n❌ Пример неправильного отжимания:")
    print(f"   Признаки: {bad_example[0]}")
    print(f"   Предсказание: {bad_pred}")
    print(f"   Вероятности: correct={bad_proba[0]:.3f}, incorrect={bad_proba[1]:.3f}")
    
    # Границы принятия решений
    print("\n" + "=" * 60)
    print("🎯 ГРАНИЦЫ ПРИНЯТИЯ РЕШЕНИЙ")
    print("=" * 60)
    
    # Проверяем чувствительность модели
    test_cases = [
        ([0.5, 0.02, 0.05, 0.01, 0.55], "Идеальное"),
        ([0.3, 0.02, 0.05, 0.01, 0.55], "Широкие локти"),
        ([0.5, 0.15, 0.05, 0.01, 0.55], "Несимметричные плечи"),
        ([0.5, 0.02, 0.25, 0.01, 0.55], "Несимметричные локти"),
        ([0.5, 0.02, 0.05, 0.2, 0.55], "Прогнутая спина"),
        ([0.7, 0.02, 0.05, 0.01, 0.85], "Мелкие отжимания"),
    ]
    
    for features, description in test_cases:
        pred = model.predict([features])[0]
        proba = model.predict_proba([features])[0]
        print(f"   {description}: {pred} (correct: {proba[0]:.3f}, incorrect: {proba[1]:.3f})")
    
    # Вывод
    print("\n" + "=" * 60)
    print("📋 ИТОГОВАЯ ОЦЕНКА")
    print("=" * 60)
    
    if accuracy >= 0.9:
        print("✅ ОТЛИЧНО! Модель хорошо обучена.")
        print("   Может использоваться в реальных условиях.")
    elif accuracy >= 0.8:
        print("👍 ХОРОШО! Модель работает приемлемо.")
        print("   Рекомендуется собрать больше данных.")
    elif accuracy >= 0.7:
        print("⚠️ УДОВЛЕТВОРИТЕЛЬНО! Есть проблемы.")
        print("   Нужно больше данных и настройка.")
    else:
        print("❌ ПЛОХО! Модель требует доработки.")
        print("   Необходимо переобучить на больших данных.")
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if test_samples < 100:
        print("   1. Собрать больше данных (минимум 200 примеров)")
    if np.abs(cm[0,0] - cm[1,1]) > 10:
        print("   2. Балансировать классы")
    if accuracy < 0.85:
        print("   3. Попробовать другие алгоритмы (SVM, Gradient Boosting)")
    print("   4. Добавить кросс-валидацию")
    print("   5. Тестировать на реальных видео")

if __name__ == "__main__":
    model_path = r"C:\AI Fitnes\models\realtime_model.pkl"
    evaluate_model(model_path)