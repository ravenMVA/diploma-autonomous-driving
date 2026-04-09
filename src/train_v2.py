"""
train_v2.py — Обучение LaneCNN.

Быстро: 20 эпох на 3k сэмплах ≈ 10-15 минут на T4.
Данные загружаются из .npy кэша — никаких дисковых операций при обучении.
Обновлён: 2026-04-10 00:05 МСК
"""

import time
import numpy as np
import torch
import torch.nn as nn
from torch.optim import Adam
from torch.optim.lr_scheduler import ReduceLROnPlateau
from pathlib import Path


def train(model, train_loader, val_loader,
          epochs: int = 20,
          lr: float = 3e-4,
          patience: int = 5,
          model_path: str = "models/model_v2.pth",
          device: str = "cpu") -> dict:
    """
    Цикл обучения с EarlyStopping и ReduceLROnPlateau.

    Returns:
        history: dict с ключами train_loss, val_loss
    """
    model = model.to(device)
    optimizer = Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = ReduceLROnPlateau(optimizer, factor=0.5, patience=3)
    criterion = nn.MSELoss()

    history = {"train_loss": [], "val_loss": []}
    best_val = float("inf")
    no_improve = 0
    t0 = time.time()

    for epoch in range(1, epochs + 1):
        # ── Train ──────────────────────────────
        model.train()
        train_loss = 0.0
        for imgs, angles in train_loader:
            imgs   = imgs.to(device, non_blocking=True)
            angles = angles.to(device, non_blocking=True)
            optimizer.zero_grad()
            pred = model(imgs)
            loss = criterion(pred, angles)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(imgs)
        train_loss /= len(train_loader.dataset)

        # ── Validation ─────────────────────────
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for imgs, angles in val_loader:
                imgs   = imgs.to(device, non_blocking=True)
                angles = angles.to(device, non_blocking=True)
                pred   = model(imgs)
                val_loss += criterion(pred, angles).item() * len(imgs)
        val_loss /= len(val_loader.dataset)

        scheduler.step(val_loss)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)

        elapsed = time.time() - t0
        print(f"Epoch {epoch:02d}/{epochs}  "
              f"train={train_loss:.5f}  val={val_loss:.5f}  "
              f"[{elapsed:.0f}s]")

        # ── EarlyStopping ───────────────────────
        if val_loss < best_val - 1e-5:
            best_val = val_loss
            no_improve = 0
            _save(model, model_path)
        else:
            no_improve += 1
            if no_improve >= patience:
                print(f"EarlyStopping на эпохе {epoch}. "
                      f"Лучший val_loss={best_val:.5f}")
                break

    print(f"\nОбучение завершено за {time.time() - t0:.0f} секунд")
    return history


def evaluate(model, loader, device: str = "cpu") -> dict:
    """Метрики MSE, MAE и точность бинарной классификации на выборке."""
    from src.dataset_v2 import THRESHOLD

    model.eval()
    criterion_mse = nn.MSELoss(reduction="sum")
    criterion_mae = nn.L1Loss(reduction="sum")
    total_mse = total_mae = 0.0
    correct = total = 0

    with torch.no_grad():
        for imgs, angles in loader:
            imgs   = imgs.to(device)
            angles = angles.to(device)
            pred   = model(imgs)

            total_mse += criterion_mse(pred, angles).item()
            total_mae += criterion_mae(pred, angles).item()

            # Точность бинарной классификации
            pred_label  = (pred.abs()   < THRESHOLD).long()
            true_label  = (angles.abs() < THRESHOLD).long()
            correct += (pred_label == true_label).sum().item()
            total   += len(angles)

    n = total
    return {
        "mse":      total_mse / n,
        "mae":      total_mae / n,
        "rmse":     (total_mse / n) ** 0.5,
        "accuracy": correct / n,
    }


def _save(model, path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), path)
