"""
train.py — Цикл обучения модели PilotNet
=========================================
Функционал:
  - Обучение с оптимизатором Adam (lr=1e-4)
  - Функция потерь: MSE
  - EarlyStopping по val_loss (patience=10)
  - Сохранение лучшей модели в best_model.pth
  - График loss в реальном времени
  - Логирование прогресса с tqdm
"""

import os
import time
import numpy as np
import matplotlib.pyplot as plt
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from tqdm import tqdm

# Воспроизводимость
torch.manual_seed(42)
np.random.seed(42)


# ──────────────────────────────────────────────
# EarlyStopping
# ──────────────────────────────────────────────

class EarlyStopping:
    """
    Останавливает обучение, если val_loss не улучшается patience эпох подряд.
    Сохраняет веса лучшей модели.

    Параметры
    ----------
    patience  : int   — сколько эпох ждать улучшения (по умолчанию 10)
    min_delta : float — минимальное улучшение, которое считается прогрессом
    save_path : str   — путь для сохранения лучших весов
    """

    def __init__(self, patience: int = 10, min_delta: float = 1e-4,
                 save_path: str = "best_model.pth"):
        self.patience   = patience
        self.min_delta  = min_delta
        self.save_path  = save_path
        self.best_loss  = np.inf
        self.counter    = 0
        self.best_epoch = 0

    def __call__(self, val_loss: float, model: nn.Module) -> bool:
        """
        Вызывается после каждой эпохи.

        Возвращает True если нужно остановить обучение.
        """
        if val_loss < self.best_loss - self.min_delta:
            # Есть улучшение — сохраняем модель и сбрасываем счётчик
            self.best_loss  = val_loss
            self.counter    = 0
            self.best_epoch = self._current_epoch
            torch.save(model.state_dict(), self.save_path)
            return False
        else:
            # Нет улучшения — увеличиваем счётчик
            self.counter += 1
            if self.counter >= self.patience:
                return True  # Стоп!
            return False

    def set_epoch(self, epoch: int):
        self._current_epoch = epoch


# ──────────────────────────────────────────────
# Одна эпоха обучения
# ──────────────────────────────────────────────

def train_epoch(model, loader, optimizer, criterion, device):
    """
    Прогоняет одну эпоху обучения (forward + backward + шаг оптимизатора).

    Возвращает среднее значение loss за эпоху.
    """
    model.train()
    running_loss = 0.0

    progress = tqdm(loader, desc="  Train", leave=False, ncols=80)

    for images, angles in progress:
        # Переносим данные на GPU/CPU
        images = images.to(device, non_blocking=True)
        angles = angles.to(device, non_blocking=True)

        # Обнуляем градиенты
        optimizer.zero_grad()

        # Прямой проход
        predictions = model(images)

        # Вычисляем MSE loss
        loss = criterion(predictions, angles)

        # Обратный проход
        loss.backward()

        # Клиппинг градиентов — защита от взрыва градиентов
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        # Шаг оптимизатора
        optimizer.step()

        running_loss += loss.item()
        progress.set_postfix(loss=f"{loss.item():.4f}")

    return running_loss / len(loader)


# ──────────────────────────────────────────────
# Одна эпоха валидации
# ──────────────────────────────────────────────

def val_epoch(model, loader, criterion, device):
    """
    Прогоняет одну эпоху валидации (только forward, без обновления весов).

    Возвращает среднее значение loss за эпоху.
    """
    model.eval()
    running_loss = 0.0

    with torch.no_grad():
        progress = tqdm(loader, desc="  Val  ", leave=False, ncols=80)
        for images, angles in progress:
            images = images.to(device, non_blocking=True)
            angles = angles.to(device, non_blocking=True)

            predictions  = model(images)
            loss         = criterion(predictions, angles)
            running_loss += loss.item()
            progress.set_postfix(loss=f"{loss.item():.4f}")

    return running_loss / len(loader)


# ──────────────────────────────────────────────
# Визуализация loss в реальном времени
# ──────────────────────────────────────────────

def plot_loss(train_losses: list, val_losses: list,
              save_path: str = "loss_curve.png"):
    """
    Строит и сохраняет график train/val loss по эпохам.

    Параметры
    ----------
    train_losses : list — значения train loss по эпохам
    val_losses   : list — значения val loss по эпохам
    save_path    : str  — путь для сохранения изображения
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    epochs = range(1, len(train_losses) + 1)

    ax.plot(epochs, train_losses, "b-o", markersize=4, label="Train Loss")
    ax.plot(epochs, val_losses,   "r-o", markersize=4, label="Val Loss")

    # Отмечаем минимум val loss
    best_epoch = np.argmin(val_losses) + 1
    best_loss  = min(val_losses)
    ax.axvline(x=best_epoch, color="green", linestyle="--", alpha=0.7,
               label=f"Лучшая эпоха: {best_epoch} (loss={best_loss:.4f})")

    ax.set_xlabel("Эпоха", fontsize=12)
    ax.set_ylabel("MSE Loss", fontsize=12)
    ax.set_title("Кривые обучения PilotNet", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.show()
    print(f"График сохранён: {save_path}")


# ──────────────────────────────────────────────
# Главная функция обучения
# ──────────────────────────────────────────────

def train(
    model,
    train_loader,
    val_loader,
    num_epochs:  int   = 50,
    lr:          float = 1e-4,
    patience:    int   = 10,
    save_dir:    str   = ".",
    device:      str   = "cpu",
):
    """
    Полный цикл обучения модели.

    Параметры
    ----------
    model        : PilotNet — модель для обучения
    train_loader : DataLoader — обучающая выборка
    val_loader   : DataLoader — валидационная выборка
    num_epochs   : int   — максимальное число эпох
    lr           : float — начальный learning rate (по умолчанию 1e-4)
    patience     : int   — терпение EarlyStopping
    save_dir     : str   — директория для сохранения модели и графиков
    device       : str   — 'cuda' или 'cpu'

    Возвращает
    ----------
    dict с историей обучения: train_losses, val_losses, best_epoch
    """
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "best_model.pth")

    # Функция потерь: MSE (среднеквадратичная ошибка)
    criterion = nn.MSELoss()

    # Оптимизатор Adam с weight decay для регуляризации
    optimizer = Adam(model.parameters(), lr=lr, weight_decay=1e-4)

    # Планировщик: уменьшает lr в 2 раза если val_loss не улучшается 5 эпох
    scheduler = ReduceLROnPlateau(optimizer, mode="min", factor=0.5,
                                   patience=5)

    # EarlyStopping
    early_stopping = EarlyStopping(patience=patience, save_path=save_path)

    train_losses = []
    val_losses   = []

    print(f"\n{'='*55}")
    print(f"  Начало обучения PilotNet")
    print(f"  Устройство:  {device}")
    print(f"  Эпох макс.:  {num_epochs}")
    print(f"  LR:          {lr}")
    print(f"  Batch size:  {train_loader.batch_size}")
    print(f"  EarlyStopping patience: {patience}")
    print(f"  Модель сохраняется: {save_path}")
    print(f"{'='*55}\n")

    start_time = time.time()

    for epoch in range(1, num_epochs + 1):
        early_stopping.set_epoch(epoch)

        print(f"Эпоха {epoch}/{num_epochs}")

        # Обучение
        train_loss = train_epoch(model, train_loader, optimizer, criterion, device)

        # Валидация
        val_loss = val_epoch(model, val_loader, criterion, device)

        # Шаг планировщика
        scheduler.step(val_loss)

        train_losses.append(train_loss)
        val_losses.append(val_loss)

        # Текущий learning rate
        current_lr = optimizer.param_groups[0]["lr"]

        print(f"  Train Loss: {train_loss:.4f} | "
              f"Val Loss: {val_loss:.4f} | "
              f"LR: {current_lr:.6f}")

        # Проверка EarlyStopping
        if early_stopping(val_loss, model):
            print(f"\n⏹ EarlyStopping сработал на эпохе {epoch}.")
            print(f"  Лучшая эпоха: {early_stopping.best_epoch}, "
                  f"Val Loss: {early_stopping.best_loss:.4f}")
            break

    total_time = time.time() - start_time
    print(f"\n✓ Обучение завершено за {total_time/60:.1f} минут")
    print(f"  Лучшая модель сохранена: {save_path}")

    # График loss
    plot_path = os.path.join(save_dir, "loss_curve.png")
    plot_loss(train_losses, val_losses, save_path=plot_path)

    history = {
        "train_losses": train_losses,
        "val_losses":   val_losses,
        "best_epoch":   early_stopping.best_epoch,
        "best_val_loss": early_stopping.best_loss,
    }

    return history


# ──────────────────────────────────────────────
# Запуск из командной строки
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from model   import get_model
    from dataset import get_dataloaders

    if len(sys.argv) < 2:
        print("Использование: python train.py <путь_к_driving_log.csv> [data_dir]")
        sys.exit(0)

    csv_path = sys.argv[1]
    data_dir = sys.argv[2] if len(sys.argv) > 2 else ""

    device = "cuda" if torch.cuda.is_available() else "cpu"

    train_loader, val_loader, _ = get_dataloaders(
        csv_path=csv_path, data_dir=data_dir, batch_size=32, num_workers=0
    )

    model = get_model(dropout_rate=0.5, device=device)

    train(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        num_epochs=50,
        lr=1e-4,
        patience=10,
        save_dir=".",
        device=device,
    )
