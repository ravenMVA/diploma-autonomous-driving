"""
dataset.py — Загрузка и подготовка датасета Udacity
====================================================
Датасет: Udacity Self-Driving Car Simulator Dataset
Источник: Kaggle — ronamgir/udacity-car-dataset-simulator-challenge

Структура CSV (driving_log.csv):
  center, left, right, steering, throttle, reverse, speed
  /path/to/center.jpg, /path/to/left.jpg, ..., 0.0, 0.0, 0, 0.0

Что делает этот модуль:
  1. Читает CSV и пути к изображениям
  2. Применяет аугментацию (flip, яркость, сдвиг)
  3. Нормализует изображения в [-1, 1]
  4. Разбивает на train / val / test = 70 / 15 / 15
  5. Возвращает готовые DataLoader для обучения
"""

import os
import numpy as np
import pandas as pd
import cv2
from PIL import Image

import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split

# Воспроизводимость
torch.manual_seed(42)
np.random.seed(42)


# ──────────────────────────────────────────────
# Константы
# ──────────────────────────────────────────────

# Целевой размер изображения для PilotNet
IMG_HEIGHT = 66
IMG_WIDTH  = 200

# Часть верхней полосы изображения, которую обрезаем (небо, капот)
CROP_TOP    = 60   # пикселей сверху
CROP_BOTTOM = 25   # пикселей снизу

# Поправочный угол для левой/правой камеры
# Помогает модели научиться возвращаться к центру полосы
CAMERA_CORRECTION = 0.25


# ──────────────────────────────────────────────
# Вспомогательные функции обработки изображений
# ──────────────────────────────────────────────

def load_image(path: str) -> np.ndarray:
    """
    Загружает изображение по пути.
    Поддерживает как абсолютные пути, так и только имена файлов.

    Параметры
    ----------
    path : str
        Путь к изображению из CSV

    Возвращает
    ----------
    np.ndarray
        Изображение в формате BGR (OpenCV)
    """
    # Убираем лишние пробелы (в CSV Udacity они есть)
    path = path.strip()

    if not os.path.exists(path):
        # Если полный путь не найден — берём только имя файла
        path = os.path.basename(path)

    img = cv2.imread(path)

    if img is None:
        raise FileNotFoundError(f"Не удалось загрузить изображение: {path}")

    return img


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """
    Предобработка изображения для подачи в PilotNet:
      1. Обрезка неинформативных областей (небо сверху, капот снизу)
      2. Изменение размера до 66×200 (стандарт PilotNet)
      3. Конвертация BGR → YUV (как в оригинальной статье NVIDIA)
      4. Нормализация пикселей в диапазон [-1, 1]

    Параметры
    ----------
    img : np.ndarray
        Исходное изображение (BGR, любой размер)

    Возвращает
    ----------
    np.ndarray
        Обработанное изображение формы (66, 200, 3), float32, значения в [-1, 1]
    """
    h = img.shape[0]

    # 1. Обрезаем верх (небо) и низ (капот автомобиля)
    img = img[CROP_TOP : h - CROP_BOTTOM, :, :]

    # 2. Масштабируем до стандартного размера PilotNet
    img = cv2.resize(img, (IMG_WIDTH, IMG_HEIGHT))

    # 3. Конвертируем BGR → YUV
    # YUV лучше разделяет яркость от цвета — модель лучше видит разметку
    img = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)

    # 4. Нормализация: [0, 255] → [-1, 1]
    img = img.astype(np.float32) / 127.5 - 1.0

    return img


# ──────────────────────────────────────────────
# Функции аугментации (применяются только к train)
# ──────────────────────────────────────────────

def augment_flip(img: np.ndarray, angle: float):
    """
    Случайное горизонтальное отражение изображения.
    При отражении угол руля меняет знак.

    Удваивает размер датасета и убирает смещение влево/вправо.
    """
    if np.random.rand() > 0.5:
        img   = cv2.flip(img, 1)   # 1 = горизонтальное отражение
        angle = -angle
    return img, angle


def augment_brightness(img: np.ndarray) -> np.ndarray:
    """
    Случайное изменение яркости изображения.
    Помогает модели работать при разном освещении (день/тень/туннель).
    """
    # Конвертируем в HSV для независимого управления яркостью
    img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)

    # Случайный коэффициент яркости от 0.4 до 1.2
    brightness_factor = 0.4 + np.random.uniform()
    img[:, :, 2] *= brightness_factor

    # Ограничиваем значения в диапазоне [0, 255]
    img[:, :, 2] = np.clip(img[:, :, 2], 0, 255)

    img = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return img


def augment_shift(img: np.ndarray, angle: float, shift_range: int = 50):
    """
    Случайный горизонтальный сдвиг изображения.
    Имитирует смещение автомобиля от центра полосы.
    Угол руля корректируется пропорционально сдвигу.

    Параметры
    ----------
    shift_range : int
        Максимальный сдвиг в пикселях (по умолчанию ±50)
    """
    shift = np.random.randint(-shift_range, shift_range)
    h, w  = img.shape[:2]

    # Матрица сдвига
    M   = np.float32([[1, 0, shift], [0, 1, 0]])
    img = cv2.warpAffine(img, M, (w, h))

    # Корректируем угол: за каждые 10 px сдвига — 0.004 рад
    angle += shift * 0.004

    return img, angle


def apply_augmentation(img: np.ndarray, angle: float):
    """
    Применяет все виды аугментации к одному изображению.
    Вызывается только для обучающей выборки.

    Параметры
    ----------
    img   : np.ndarray  — исходное изображение (BGR)
    angle : float       — угол руля

    Возвращает
    ----------
    tuple(np.ndarray, float) — аугментированные изображение и угол
    """
    img, angle = augment_shift(img, angle)
    img        = augment_brightness(img)
    img, angle = augment_flip(img, angle)
    return img, angle


# ──────────────────────────────────────────────
# PyTorch Dataset
# ──────────────────────────────────────────────

class UdacityDataset(Dataset):
    """
    PyTorch Dataset для датасета Udacity.

    Поддерживает:
    - Три камеры (center / left / right) с поправкой угла
    - Аугментацию для обучающей выборки
    - Фильтрацию "скучных" кадров (почти прямая езда)

    Параметры
    ----------
    samples : list of (img_path, steering_angle)
        Список пар (путь к изображению, угол руля)
    augment : bool
        Применять ли аугментацию (True для train, False для val/test)
    """

    def __init__(self, samples: list, augment: bool = False):
        self.samples = samples
        self.augment = augment

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        img_path, angle = self.samples[idx]

        try:
            img = load_image(img_path)
        except FileNotFoundError as e:
            # Если изображение не найдено — возвращаем чёрный кадр
            print(f"Предупреждение: {e}")
            img   = np.zeros((160, 320, 3), dtype=np.uint8)
            angle = 0.0

        # Аугментация (только для обучающей выборки)
        if self.augment:
            img, angle = apply_augmentation(img, angle)

        # Предобработка: обрезка, ресайз, YUV, нормализация
        img = preprocess_image(img)

        # Конвертируем в тензор PyTorch: (H, W, C) → (C, H, W)
        img_tensor   = torch.tensor(img, dtype=torch.float32).permute(2, 0, 1)
        angle_tensor = torch.tensor([angle], dtype=torch.float32)

        return img_tensor, angle_tensor


# ──────────────────────────────────────────────
# Загрузка и разбивка данных
# ──────────────────────────────────────────────

def load_samples_from_csv(csv_path: str, data_dir: str = "") -> list:
    """
    Читает CSV и формирует список (путь_к_изображению, угол_руля).

    Использует все три камеры:
    - Центральная: угол без изменений
    - Левая:       угол + CAMERA_CORRECTION (нужно повернуть вправо)
    - Правая:      угол - CAMERA_CORRECTION (нужно повернуть влево)

    Параметры
    ----------
    csv_path : str
        Путь к файлу driving_log.csv
    data_dir : str
        Директория с изображениями (если пути в CSV относительные)

    Возвращает
    ----------
    list of (str, float)
        Список пар (путь, угол)
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV файл не найден: {csv_path}")

    df = pd.read_csv(csv_path, header=None,
                     names=["center", "left", "right",
                             "steering", "throttle", "reverse", "speed"])

    print(f"Загружено строк из CSV: {len(df)}")

    samples = []

    for _, row in df.iterrows():
        steering = float(row["steering"])

        # Формируем пути к изображениям
        def resolve_path(raw_path):
            raw_path = str(raw_path).strip()
            if data_dir and not os.path.isabs(raw_path):
                # Берём только имя файла и ищем в data_dir/IMG/
                filename = os.path.basename(raw_path)
                return os.path.join(data_dir, "IMG", filename)
            return raw_path

        center_path = resolve_path(row["center"])
        left_path   = resolve_path(row["left"])
        right_path  = resolve_path(row["right"])

        # Добавляем все три камеры
        samples.append((center_path, steering))
        samples.append((left_path,   steering + CAMERA_CORRECTION))
        samples.append((right_path,  steering - CAMERA_CORRECTION))

    print(f"Итого сэмплов (×3 камеры): {len(samples)}")
    return samples


def balance_samples(samples: list, bins: int = 25, max_per_bin: int = 400) -> list:
    """
    Балансировка датасета по углу руля.

    Проблема: ~80% данных — прямая езда (угол ≈ 0).
    Без балансировки модель научится всегда предсказывать 0.

    Решение: ограничиваем количество сэмплов с малым углом.

    Параметры
    ----------
    bins        : int — количество интервалов гистограммы углов
    max_per_bin : int — максимум сэмплов в одном интервале

    Возвращает
    ----------
    list — сбалансированный список сэмплов
    """
    angles = np.array([s[1] for s in samples])

    # Разбиваем углы на интервалы
    hist, bin_edges = np.histogram(angles, bins=bins)

    balanced = []
    for i in range(bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        # Берём сэмплы в этом интервале
        bin_samples = [s for s in samples if lo <= s[1] < hi]
        # Ограничиваем количество
        if len(bin_samples) > max_per_bin:
            bin_samples = list(np.array(bin_samples, dtype=object)[
                np.random.choice(len(bin_samples), max_per_bin, replace=False)
            ])
        balanced.extend(bin_samples)

    print(f"После балансировки: {len(balanced)} сэмплов (было {len(samples)})")
    return balanced


def get_dataloaders(
    csv_path:   str,
    data_dir:   str  = "",
    batch_size: int  = 32,
    balance:    bool = True,
    num_workers: int = 2,
) -> tuple:
    """
    Главная функция модуля.
    Создаёт и возвращает DataLoader для train / val / test.

    Параметры
    ----------
    csv_path    : str  — путь к driving_log.csv
    data_dir    : str  — директория с папкой IMG/
    batch_size  : int  — размер батча (по умолчанию 32)
    balance     : bool — балансировать ли датасет (рекомендуется True)
    num_workers : int  — потоки загрузки данных (0 для Colab)

    Возвращает
    ----------
    tuple: (train_loader, val_loader, test_loader)
    """
    # 1. Загружаем все сэмплы из CSV
    all_samples = load_samples_from_csv(csv_path, data_dir)

    # 2. Балансировка (убираем перекос в сторону прямой езды)
    if balance:
        all_samples = balance_samples(all_samples)

    # 3. Разбивка: 70% train / 15% val / 15% test
    train_samples, temp_samples = train_test_split(
        all_samples, test_size=0.30, random_state=42, shuffle=True
    )
    val_samples, test_samples = train_test_split(
        temp_samples, test_size=0.50, random_state=42
    )

    print(f"\nРазбивка датасета:")
    print(f"  Train: {len(train_samples)} сэмплов")
    print(f"  Val:   {len(val_samples)}  сэмплов")
    print(f"  Test:  {len(test_samples)} сэмплов")

    # 4. Создаём Dataset объекты
    # augment=True только для train!
    train_dataset = UdacityDataset(train_samples, augment=True)
    val_dataset   = UdacityDataset(val_samples,   augment=False)
    test_dataset  = UdacityDataset(test_samples,  augment=False)

    # 5. Оборачиваем в DataLoader
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,              # перемешиваем каждую эпоху
        num_workers=num_workers,
        pin_memory=True,           # ускоряет передачу на GPU
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )
    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    return train_loader, val_loader, test_loader


# ──────────────────────────────────────────────
# Быстрый тест при запуске файла напрямую
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Использование: python dataset.py <путь_к_driving_log.csv> [папка_с_IMG]")
        print("Пример:        python dataset.py /content/data/driving_log.csv /content/data")
        sys.exit(0)

    csv_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else ""

    train_loader, val_loader, test_loader = get_dataloaders(
        csv_path=csv_path,
        data_dir=data_dir,
        batch_size=32,
    )

    # Проверяем один батч
    images, angles = next(iter(train_loader))
    print(f"\nФорма батча изображений: {images.shape}")   # (32, 3, 66, 200)
    print(f"Форма батча углов:       {angles.shape}")    # (32, 1)
    print(f"Мин/Макс пикселей:       {images.min():.2f} / {images.max():.2f}")
    print(f"Мин/Макс углов:          {angles.min():.3f} / {angles.max():.3f}")
    print("\n✓ DataLoader работает корректно")
