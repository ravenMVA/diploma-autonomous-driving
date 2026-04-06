"""
dataset_v2.py — Загрузка данных Udacity, стратифицированная выборка 3k сэмплов,
кэширование в .npy для мгновенной загрузки при обучении.
"""

import os
import numpy as np
import pandas as pd
import cv2
from pathlib import Path
from torch.utils.data import Dataset, DataLoader
import torch


# ──────────────────────────────────────────────
# Константы
# ──────────────────────────────────────────────
IMG_H, IMG_W = 32, 100          # маленький размер: в 4× меньше пикселей чем в v1
N_SAMPLES    = 3000             # итоговый размер выборки
N_BINS       = 30               # число бинов для стратификации
SAMPLES_PER_BIN = N_SAMPLES // N_BINS
THRESHOLD    = 0.15             # граница "в полосе" для бинарной классификации


def preprocess_image(img: np.ndarray) -> np.ndarray:
    """BGR → grayscale → кроп → resize → нормировка в [-1, 1]."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Убираем небо (верхние 40%) и капот (нижние 10%)
    h = gray.shape[0]
    gray = gray[int(h * 0.4): int(h * 0.9), :]
    gray = cv2.resize(gray, (IMG_W, IMG_H), interpolation=cv2.INTER_AREA)
    return (gray.astype(np.float32) / 127.5) - 1.0  # [-1, 1]


def load_and_cache(csv_path: str, images_dir: str, cache_path: str) -> tuple:
    """
    Загружает данные, делает стратифицированную выборку, сохраняет кэш.

    Returns:
        images: np.ndarray (N, 1, IMG_H, IMG_W) float32
        angles: np.ndarray (N,) float32
    """
    cache_path = Path(cache_path)
    if cache_path.exists():
        print(f"Загружаю кэш из {cache_path}...")
        data = np.load(cache_path, allow_pickle=True).item()
        return data["images"], data["angles"]

    print("Кэш не найден, создаю...")
    df = pd.read_csv(csv_path)

    # Поддержка разных форматов CSV датасета Udacity
    if "center" in df.columns:
        center_col, angle_col = "center", "steering"
    else:
        center_col, angle_col = df.columns[0], df.columns[3]

    df = df[[center_col, angle_col]].dropna()
    df.columns = ["img_path", "angle"]
    df["angle"] = df["angle"].astype(float)

    # Стратифицированная выборка по бинам угла руля
    bins = np.linspace(-1.0, 1.0, N_BINS + 1)
    df["bin"] = np.digitize(df["angle"], bins) - 1
    df["bin"] = df["bin"].clip(0, N_BINS - 1)

    sampled = (
        df.groupby("bin", group_keys=False)
          .apply(lambda g: g.sample(min(len(g), SAMPLES_PER_BIN), random_state=42))
    )
    sampled = sampled.sample(frac=1, random_state=42).reset_index(drop=True)
    print(f"Выборка: {len(sampled)} сэмплов из {len(df)}")

    images_dir = Path(images_dir)
    images_list, angles_list = [], []

    for _, row in sampled.iterrows():
        img_file = Path(row["img_path"].strip())
        if not img_file.is_absolute():
            img_file = images_dir / img_file.name
        img = cv2.imread(str(img_file))
        if img is None:
            continue
        proc = preprocess_image(img)
        images_list.append(proc[np.newaxis, :, :])   # (1, H, W)
        angles_list.append(float(row["angle"]))

    images = np.array(images_list, dtype=np.float32)
    angles = np.array(angles_list, dtype=np.float32)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache_path, {"images": images, "angles": angles})
    print(f"Кэш сохранён: {cache_path}  ({images.nbytes / 1e6:.1f} MB)")
    return images, angles


class LaneDataset(Dataset):
    """Dataset для обучения: изображение → угол руля."""

    def __init__(self, images: np.ndarray, angles: np.ndarray):
        self.images = torch.from_numpy(images)
        self.angles = torch.from_numpy(angles).unsqueeze(1)  # (N, 1)

    def __len__(self):
        return len(self.angles)

    def __getitem__(self, idx):
        return self.images[idx], self.angles[idx]


def get_loaders(images: np.ndarray, angles: np.ndarray,
                batch_size: int = 128,
                val_frac: float = 0.15,
                test_frac: float = 0.15) -> tuple:
    """Возвращает (train_loader, val_loader, test_loader)."""
    n = len(images)
    idx = np.random.permutation(n)
    n_test = int(n * test_frac)
    n_val  = int(n * val_frac)

    test_idx  = idx[:n_test]
    val_idx   = idx[n_test: n_test + n_val]
    train_idx = idx[n_test + n_val:]

    def make_loader(i, shuffle):
        ds = LaneDataset(images[i], angles[i])
        return DataLoader(ds, batch_size=batch_size, shuffle=shuffle,
                          num_workers=2, pin_memory=True)

    return (make_loader(train_idx, True),
            make_loader(val_idx, False),
            make_loader(test_idx, False))


def angle_to_label(angle: float) -> int:
    """Бинарная метка: 1 = в полосе, 0 = вне полосы."""
    return int(abs(angle) < THRESHOLD)
