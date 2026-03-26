"""
utils.py — Вспомогательные функции проекта
===========================================
Содержит:
  - Определение устройства (GPU/CPU)
  - Загрузка и сохранение модели
  - Установка воспроизводимости
  - Отображение примеров из датасета
  - Функция скачивания датасета Udacity с Kaggle
"""

import os
import random
import numpy as np
import matplotlib.pyplot as plt
import cv2
import torch


# ──────────────────────────────────────────────
# Воспроизводимость
# ──────────────────────────────────────────────

def set_seed(seed: int = 42):
    """
    Устанавливает seed для воспроизводимости результатов.
    Влияет на Python random, NumPy и PyTorch (CPU + GPU).

    Параметры
    ----------
    seed : int — значение seed (по умолчанию 42)
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)

    # Детерминированные операции в cuDNN (замедляет обучение, но гарантирует воспроизводимость)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark     = False

    print(f"✓ Seed установлен: {seed}")


# ──────────────────────────────────────────────
# Устройство
# ──────────────────────────────────────────────

def get_device() -> str:
    """
    Определяет и возвращает доступное устройство.

    Возвращает
    ----------
    str — 'cuda' если GPU доступен, иначе 'cpu'
    """
    if torch.cuda.is_available():
        device = "cuda"
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem  = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"✓ Используется GPU: {gpu_name} ({gpu_mem:.1f} GB)")
    else:
        device = "cpu"
        print("⚠ GPU недоступен, используется CPU (обучение будет медленнее)")

    return device


# ──────────────────────────────────────────────
# Сохранение и загрузка модели
# ──────────────────────────────────────────────

def save_model(model, path: str, metadata: dict = None):
    """
    Сохраняет веса модели и дополнительные метаданные.

    Параметры
    ----------
    model    : PilotNet — модель для сохранения
    path     : str      — путь к файлу (.pth)
    metadata : dict     — доп. данные (метрики, эпоха, параметры)
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    checkpoint = {
        "model_state_dict": model.state_dict(),
        "metadata": metadata or {},
    }

    torch.save(checkpoint, path)
    print(f"✓ Модель сохранена: {path}")


def load_model(model, path: str, device: str = "cpu"):
    """
    Загружает веса модели из файла.
    Поддерживает как полный checkpoint, так и только state_dict.

    Параметры
    ----------
    model  : PilotNet — модель (архитектура должна совпадать)
    path   : str      — путь к файлу .pth
    device : str      — устройство для загрузки

    Возвращает
    ----------
    tuple(model, dict) — модель с загруженными весами и метаданные
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Файл модели не найден: {path}")

    checkpoint = torch.load(path, map_location=device, weights_only=False)

    # Поддержка двух форматов сохранения
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        metadata = checkpoint.get("metadata", {})
    else:
        # Если сохранён только state_dict (из EarlyStopping)
        model.load_state_dict(checkpoint)
        metadata = {}

    model = model.to(device)
    model.eval()

    print(f"✓ Модель загружена: {path}")
    if metadata:
        print(f"  Метаданные: {metadata}")

    return model, metadata


# ──────────────────────────────────────────────
# Визуализация данных
# ──────────────────────────────────────────────

def show_dataset_samples(loader, n_samples: int = 8,
                          save_path: str = None):
    """
    Отображает случайные примеры из DataLoader.

    Параметры
    ----------
    loader    : DataLoader — обучающая или тестовая выборка
    n_samples : int — количество примеров для показа
    save_path : str — если указан, сохраняет изображение
    """
    images, angles = next(iter(loader))

    n_cols = min(n_samples, 4)
    n_rows = (n_samples + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 3.5, n_rows * 2.5))
    fig.suptitle(f"Примеры из датасета ({n_samples} изображений)",
                 fontsize=13, fontweight="bold")

    axes = axes.flatten() if n_samples > 1 else [axes]

    for i in range(n_samples):
        if i >= len(images):
            axes[i].axis("off")
            continue

        # Денормализация: [-1, 1] → [0, 1]
        img = images[i].numpy().transpose(1, 2, 0)
        img = (img + 1.0) / 2.0
        img = np.clip(img, 0, 1)

        axes[i].imshow(img)
        axes[i].set_title(f"Угол: {angles[i].item():.3f}", fontsize=9)
        axes[i].axis("off")

    # Скрываем лишние оси
    for j in range(n_samples, len(axes)):
        axes[j].axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Примеры сохранены: {save_path}")

    plt.show()


def plot_steering_distribution(samples: list, save_path: str = None):
    """
    Строит гистограмму распределения углов руля в датасете.
    Помогает понять баланс данных.

    Параметры
    ----------
    samples   : list of (path, angle) — список сэмплов
    save_path : str — путь для сохранения
    """
    angles = [s[1] for s in samples]

    fig, ax = plt.subplots(figsize=(10, 4))

    ax.hist(angles, bins=50, color="steelblue", edgecolor="white", alpha=0.85)
    ax.axvline(x=0, color="red", linestyle="--", linewidth=2, label="Прямая езда (0)")

    ax.set_xlabel("Угол руля", fontsize=12)
    ax.set_ylabel("Количество сэмплов", fontsize=12)
    ax.set_title("Распределение углов руля в датасете", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"График сохранён: {save_path}")

    plt.show()

    # Статистика
    angles_arr = np.array(angles)
    print(f"\nСтатистика углов:")
    print(f"  Среднее:   {angles_arr.mean():.4f}")
    print(f"  Ст. откл.: {angles_arr.std():.4f}")
    print(f"  Мин:       {angles_arr.min():.4f}")
    print(f"  Макс:      {angles_arr.max():.4f}")
    print(f"  Прямая езда (|угол| < 0.05): "
          f"{(np.abs(angles_arr) < 0.05).mean()*100:.1f}%")


# ──────────────────────────────────────────────
# Подготовка к запуску в Colab
# ──────────────────────────────────────────────

def setup_colab_paths(drive_path: str = "/content/drive/MyDrive/diploma"):
    """
    Настраивает пути для работы в Google Colab.
    Добавляет папку src/ в sys.path для импорта модулей.

    Параметры
    ----------
    drive_path : str — путь к папке проекта на Google Drive

    Возвращает
    ----------
    dict с ключами: project_dir, src_dir, data_dir, models_dir, outputs_dir
    """
    import sys

    src_dir = os.path.join(drive_path, "src")

    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
        print(f"✓ Добавлен в sys.path: {src_dir}")

    paths = {
        "project_dir": drive_path,
        "src_dir":     src_dir,
        "data_dir":    os.path.join(drive_path, "data"),
        "models_dir":  os.path.join(drive_path, "models"),
        "outputs_dir": os.path.join(drive_path, "outputs"),
    }

    # Создаём папки если не существуют
    for name, path in paths.items():
        if name != "project_dir":
            os.makedirs(path, exist_ok=True)

    print(f"\nПапки проекта:")
    for name, path in paths.items():
        print(f"  {name:12s}: {path}")

    return paths


def print_system_info():
    """
    Выводит информацию о системе: PyTorch, CUDA, GPU.
    Полезно запускать в начале каждого ноутбука.
    """
    print("=" * 50)
    print("  ИНФОРМАЦИЯ О СИСТЕМЕ")
    print("=" * 50)
    print(f"  PyTorch версия:  {torch.__version__}")
    print(f"  CUDA доступна:   {torch.cuda.is_available()}")

    if torch.cuda.is_available():
        print(f"  CUDA версия:     {torch.version.cuda}")
        print(f"  GPU:             {torch.cuda.get_device_name(0)}")
        mem = torch.cuda.get_device_properties(0).total_memory / 1e9
        print(f"  Память GPU:      {mem:.1f} GB")

    import platform
    print(f"  Python:          {platform.python_version()}")
    print("=" * 50)
