"""
evaluate.py — Оценка качества модели PilotNet
==============================================
Метрики:
  - MSE  (Mean Squared Error)
  - MAE  (Mean Absolute Error)
  - R²   (коэффициент детерминации)

Визуализации:
  - График: предсказанные vs реальные углы руля
  - Гистограмма ошибок предсказания
  - Сетка 3×3 с примерами изображений и предсказаниями
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import torch
import torch.nn as nn
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from tqdm import tqdm

# Воспроизводимость
torch.manual_seed(42)
np.random.seed(42)


# ──────────────────────────────────────────────
# Сбор предсказаний на тестовой выборке
# ──────────────────────────────────────────────

def get_predictions(model, loader, device):
    """
    Прогоняет модель через весь DataLoader и собирает предсказания.

    Параметры
    ----------
    model  : PilotNet — обученная модель (лучше загрузить best_model.pth)
    loader : DataLoader — тестовая выборка
    device : str — 'cuda' или 'cpu'

    Возвращает
    ----------
    tuple(np.ndarray, np.ndarray)
        (y_true, y_pred) — реальные и предсказанные углы руля
    """
    model.eval()
    all_targets = []
    all_preds   = []

    with torch.no_grad():
        for images, angles in tqdm(loader, desc="Оценка модели", ncols=80):
            images = images.to(device, non_blocking=True)
            angles = angles.to(device, non_blocking=True)

            preds = model(images)

            all_targets.append(angles.cpu().numpy())
            all_preds.append(preds.cpu().numpy())

    y_true = np.concatenate(all_targets).flatten()
    y_pred = np.concatenate(all_preds).flatten()

    return y_true, y_pred


# ──────────────────────────────────────────────
# Метрики качества
# ──────────────────────────────────────────────

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Вычисляет основные метрики регрессии.

    Параметры
    ----------
    y_true : np.ndarray — реальные углы руля
    y_pred : np.ndarray — предсказанные углы руля

    Возвращает
    ----------
    dict с ключами: mse, rmse, mae, r2
    """
    mse  = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    mae  = mean_absolute_error(y_true, y_pred)
    r2   = r2_score(y_true, y_pred)

    metrics = {"mse": mse, "rmse": rmse, "mae": mae, "r2": r2}

    # Красивый вывод в консоль
    print("\n" + "=" * 45)
    print("         МЕТРИКИ КАЧЕСТВА МОДЕЛИ")
    print("=" * 45)
    print(f"  MSE  (ср. кв. ошибка):    {mse:.6f}")
    print(f"  RMSE (корень из MSE):      {rmse:.6f}")
    print(f"  MAE  (ср. абс. ошибка):   {mae:.6f} рад")
    print(f"  R²   (коэф. детерминации): {r2:.4f}")
    print("=" * 45)
    print(f"  Интерпретация R²:")
    if r2 >= 0.9:
        print("  ✓ Отличное качество (R² ≥ 0.9)")
    elif r2 >= 0.75:
        print("  ◑ Хорошее качество (R² ≥ 0.75)")
    elif r2 >= 0.5:
        print("  △ Удовлетворительное (R² ≥ 0.5)")
    else:
        print("  ✗ Требует улучшения (R² < 0.5)")
    print("=" * 45 + "\n")

    return metrics


# ──────────────────────────────────────────────
# График: предсказания vs реальность
# ──────────────────────────────────────────────

def plot_predictions_vs_actual(y_true: np.ndarray, y_pred: np.ndarray,
                                save_path: str = "pred_vs_actual.png"):
    """
    Строит два графика:
      1. Scatter: предсказанные vs реальные углы (идеал — точки на диагонали)
      2. Линейный: предсказания и реальность по времени (первые 300 сэмплов)

    Параметры
    ----------
    y_true    : np.ndarray — реальные углы руля
    y_pred    : np.ndarray — предсказанные углы
    save_path : str        — путь для сохранения
    """
    fig, axes = plt.subplots(1, 2, figsize=(15, 5))

    # ── График 1: Scatter ──
    ax = axes[0]
    ax.scatter(y_true, y_pred, alpha=0.3, s=5, color="steelblue")

    # Идеальная линия предсказания
    lim = max(abs(y_true).max(), abs(y_pred).max()) * 1.1
    ax.plot([-lim, lim], [-lim, lim], "r--", linewidth=2, label="Идеал")

    ax.set_xlabel("Реальный угол руля", fontsize=12)
    ax.set_ylabel("Предсказанный угол", fontsize=12)
    ax.set_title("Предсказания vs Реальность", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    # ── График 2: Временной ряд (первые 300 сэмплов) ──
    ax = axes[1]
    n = min(300, len(y_true))
    x = range(n)

    ax.plot(x, y_true[:n], "b-",  linewidth=1.2, label="Реальный угол",    alpha=0.8)
    ax.plot(x, y_pred[:n], "r--", linewidth=1.2, label="Предсказание",    alpha=0.8)

    ax.set_xlabel("Сэмпл", fontsize=12)
    ax.set_ylabel("Угол руля", fontsize=12)
    ax.set_title(f"Первые {n} предсказаний", fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()
    print(f"График сохранён: {save_path}")


# ──────────────────────────────────────────────
# Гистограмма ошибок
# ──────────────────────────────────────────────

def plot_error_distribution(y_true: np.ndarray, y_pred: np.ndarray,
                             save_path: str = "error_distribution.png"):
    """
    Строит гистограмму ошибок предсказания (y_pred - y_true).
    Хорошая модель даёт ошибки, близкие к нормальному распределению с μ ≈ 0.

    Параметры
    ----------
    y_true    : np.ndarray — реальные углы
    y_pred    : np.ndarray — предсказанные углы
    save_path : str        — путь для сохранения
    """
    errors = y_pred - y_true

    fig, ax = plt.subplots(figsize=(9, 5))

    ax.hist(errors, bins=60, color="steelblue", edgecolor="white",
            alpha=0.85, density=True)

    # Линия среднего
    ax.axvline(x=errors.mean(), color="red", linestyle="--",
               linewidth=2, label=f"Среднее: {errors.mean():.4f}")
    ax.axvline(x=0, color="green", linestyle="-",
               linewidth=1.5, alpha=0.7, label="Идеал (0)")

    ax.set_xlabel("Ошибка предсказания (рад)", fontsize=12)
    ax.set_ylabel("Плотность", fontsize=12)
    ax.set_title("Распределение ошибок предсказания угла руля",
                 fontsize=13, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()
    print(f"График сохранён: {save_path}")


# ──────────────────────────────────────────────
# Сетка 3×3 с примерами изображений
# ──────────────────────────────────────────────

def plot_sample_predictions(model, loader, device,
                             save_path: str = "sample_predictions.png"):
    """
    Показывает сетку 3×3 изображений с предсказаниями и реальными углами.
    Зелёный заголовок = хорошее предсказание, красный = большая ошибка.

    Параметры
    ----------
    model     : PilotNet — обученная модель
    loader    : DataLoader — выборка для примеров
    device    : str — 'cuda' или 'cpu'
    save_path : str — путь для сохранения
    """
    model.eval()

    # Берём один батч
    images, angles = next(iter(loader))
    images_dev = images.to(device)

    with torch.no_grad():
        preds = model(images_dev).cpu().numpy().flatten()

    angles_np = angles.numpy().flatten()
    images_np = images.numpy()

    fig, axes = plt.subplots(3, 3, figsize=(12, 9))
    fig.suptitle("Примеры предсказаний модели (3×3)",
                 fontsize=14, fontweight="bold")

    for i, ax in enumerate(axes.flatten()):
        if i >= len(images_np):
            ax.axis("off")
            continue

        # Возвращаем изображение из тензора для отображения
        # Формат: (C, H, W) → (H, W, C), денормализация [-1,1] → [0,1]
        img = images_np[i].transpose(1, 2, 0)
        img = (img + 1.0) / 2.0
        img = np.clip(img, 0, 1)

        ax.imshow(img)
        ax.axis("off")

        # Ошибка предсказания
        error  = abs(preds[i] - angles_np[i])
        color  = "green" if error < 0.05 else ("orange" if error < 0.15 else "red")

        ax.set_title(
            f"Реал: {angles_np[i]:.3f}  |  Пред: {preds[i]:.3f}\n"
            f"Ошибка: {error:.3f}",
            fontsize=9,
            color=color,
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()
    print(f"Сетка изображений сохранена: {save_path}")


# ──────────────────────────────────────────────
# Главная функция оценки
# ──────────────────────────────────────────────

def evaluate(model, test_loader, device, save_dir: str = "."):
    """
    Полная оценка модели: метрики + все визуализации.

    Параметры
    ----------
    model       : PilotNet — модель (с загруженными весами best_model.pth)
    test_loader : DataLoader — тестовая выборка
    device      : str — 'cuda' или 'cpu'
    save_dir    : str — директория для сохранения графиков

    Возвращает
    ----------
    dict — словарь с метриками (mse, rmse, mae, r2)
    """
    os.makedirs(save_dir, exist_ok=True)

    print("Сбор предсказаний на тестовой выборке...")
    y_true, y_pred = get_predictions(model, test_loader, device)

    # Метрики
    metrics = compute_metrics(y_true, y_pred)

    # Визуализации
    plot_predictions_vs_actual(
        y_true, y_pred,
        save_path=os.path.join(save_dir, "pred_vs_actual.png")
    )
    plot_error_distribution(
        y_true, y_pred,
        save_path=os.path.join(save_dir, "error_distribution.png")
    )
    plot_sample_predictions(
        model, test_loader, device,
        save_path=os.path.join(save_dir, "sample_predictions.png")
    )

    return metrics


# ──────────────────────────────────────────────
# Запуск из командной строки
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model   import get_model
    from dataset import get_dataloaders

    if len(sys.argv) < 3:
        print("Использование: python evaluate.py <модель.pth> <driving_log.csv> [data_dir]")
        sys.exit(0)

    model_path = sys.argv[1]
    csv_path   = sys.argv[2]
    data_dir   = sys.argv[3] if len(sys.argv) > 3 else ""

    device = "cuda" if torch.cuda.is_available() else "cpu"

    _, _, test_loader = get_dataloaders(
        csv_path=csv_path, data_dir=data_dir, batch_size=32, num_workers=0
    )

    model = get_model(device=device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    print(f"Модель загружена: {model_path}")

    evaluate(model, test_loader, device, save_dir=".")
