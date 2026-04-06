"""
agent.py — Агент удержания полосы.

Связывает три компонента:
    1. LaneCNN   — нейросеть (чёрный ящик): image → e ∈ [-1, 1]
    2. PIDController — агент влияния: e → u (корректирующий сигнал)
    3. Reward function — классификатор: |u| < порог → в полосе (+1) / вне (−1)

Цель агента: максимизировать суммарную награду = минимизировать ∫|e(t)| dt.
"""

import numpy as np
import torch
import torch.nn as nn
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from src.model_v2 import LaneCNN
from src.pid import PIDController


THRESHOLD = 0.15  # граница "в полосе" (соответствует dataset_v2.THRESHOLD)


@dataclass
class EpisodeResult:
    """Результаты одного эпизода (последовательности кадров)."""
    rewards:     np.ndarray   # +1 / -1 по каждому кадру
    errors:      np.ndarray   # предсказанные ошибки e(t) из нейросети
    controls:    np.ndarray   # управляющие сигналы u(t) от ПИД
    cte:         float        # средняя абсолютная ошибка (Cross-Track Error)
    in_lane_pct: float        # % кадров "в полосе"
    total_reward: float       # суммарная награда

    def summary(self) -> str:
        return (f"CTE={self.cte:.4f}  |  В полосе: {self.in_lane_pct:.1f}%  "
                f"|  Награда: {self.total_reward:.0f}/{len(self.rewards)}")


class LaneKeepingAgent:
    """
    Агент удержания полосы.

    Использование:
        agent = LaneKeepingAgent.load("models/model_v2.pth")
        result = agent.run_episode(frames)   # frames: np.ndarray (N, 1, 32, 100)
        print(result.summary())
    """

    def __init__(self, model: LaneCNN, pid: PIDController, device: str = "cpu"):
        self.model  = model.to(device)
        self.pid    = pid
        self.device = device
        self.model.eval()

    # ──────────────────────────────────────────────
    # Предсказание нейросети (чёрный ящик)
    # ──────────────────────────────────────────────

    @torch.no_grad()
    def predict_error(self, frame: np.ndarray) -> float:
        """
        Нейросеть оценивает отклонение от полосы по одному кадру.

        Args:
            frame: np.ndarray (1, H, W) float32 нормированный в [-1, 1]

        Returns:
            e ∈ [-1, 1]: ошибка отклонения (0 = точно по центру)
        """
        tensor = torch.from_numpy(frame[np.newaxis]).to(self.device)  # (1, 1, H, W)
        return float(self.model(tensor).item())

    # ──────────────────────────────────────────────
    # Функция вознаграждения (классификатор полосы)
    # ──────────────────────────────────────────────

    @staticmethod
    def get_reward(control_signal: float) -> float:
        """
        Бинарная классификация положения в полосе.

        |u| < THRESHOLD → агент в полосе  → +1 (выигрыш)
        |u| ≥ THRESHOLD → агент вне полосы → -1 (проигрыш)
        """
        return 1.0 if abs(control_signal) < THRESHOLD else -1.0

    # ──────────────────────────────────────────────
    # Один эпизод
    # ──────────────────────────────────────────────

    def run_episode(self, frames: np.ndarray) -> EpisodeResult:
        """
        Прогон агента по последовательности кадров.

        Args:
            frames: np.ndarray (N, 1, H, W) — последовательность кадров

        Returns:
            EpisodeResult с метриками эпизода
        """
        self.pid.reset()
        rewards, errors, controls = [], [], []

        for frame in frames:
            e = self.predict_error(frame)   # нейросеть: чёрный ящик
            u = self.pid.step(e)            # ПИД: агент влияния
            r = self.get_reward(u)          # классификатор полосы

            errors.append(e)
            controls.append(u)
            rewards.append(r)

        rewards  = np.array(rewards)
        errors   = np.array(errors)
        controls = np.array(controls)

        cte          = float(np.mean(np.abs(errors)))
        in_lane_pct  = float(np.mean(rewards == 1.0)) * 100.0
        total_reward = float(np.sum(rewards))

        return EpisodeResult(
            rewards=rewards, errors=errors, controls=controls,
            cte=cte, in_lane_pct=in_lane_pct, total_reward=total_reward,
        )

    def run_episode_no_pid(self, frames: np.ndarray) -> EpisodeResult:
        """Тот же эпизод но БЕЗ ПИД — для сравнения."""
        rewards, errors, controls = [], [], []

        for frame in frames:
            e = self.predict_error(frame)
            r = self.get_reward(e)   # используем сырой выход нейросети

            errors.append(e)
            controls.append(e)
            rewards.append(r)

        rewards  = np.array(rewards)
        errors   = np.array(errors)
        controls = np.array(controls)

        return EpisodeResult(
            rewards=rewards, errors=errors, controls=controls,
            cte=float(np.mean(np.abs(errors))),
            in_lane_pct=float(np.mean(rewards == 1.0)) * 100.0,
            total_reward=float(np.sum(rewards)),
        )

    # ──────────────────────────────────────────────
    # Сохранение / загрузка
    # ──────────────────────────────────────────────

    def save(self, path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), path)
        print(f"Модель сохранена: {path}")

    @classmethod
    def load(cls, path: str, device: str = "cpu",
             kp: float = 0.8, ki: float = 0.01, kd: float = 0.15) -> "LaneKeepingAgent":
        model = LaneCNN()
        model.load_state_dict(torch.load(path, map_location=device))
        pid = PIDController(Kp=kp, Ki=ki, Kd=kd)
        agent = cls(model, pid, device)
        print(f"Агент загружен из {path}")
        return agent
