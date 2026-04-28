"""
model_v2.py — Лёгкая CNN (~37k параметров) для оценки отклонения от полосы.

Вход:  (B, 1, 32, 100) — grayscale изображение
Выход: (B, 1)          — ошибка отклонения e ∈ [-1, 1]

Обновлён: 2026-04-28 МСК
"""

import torch
import torch.nn as nn


class LaneCNN(nn.Module):
    """
    Минималистичная CNN для оценки отклонения от центра полосы.

    Архитектура:
        Conv 3×3 s=2, 8 фильтров + ReLU   → (8, 16, 50)
        MaxPool 2×2                         → (8, 8, 25)
        Conv 3×3 s=1, 16 фильтров + ReLU  → (16, 6, 23)
        MaxPool 2×2                         → (16, 3, 11)
        Flatten                             → 528
        Dense 64 + ReLU
        Dense 1  + Tanh                     → e ∈ [-1, 1]

    ~37k параметров (против 252k у PilotNet v1)
    """

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=3, stride=2, padding=1),  # → 8×16×50
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                                        # → 8×8×25
            nn.Conv2d(8, 16, kernel_size=3, stride=1, padding=1), # → 16×8×25
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                                        # → 16×4×12
        )
        # Вычислим точный размер динамически
        self._flat_size = self._get_flat_size()

        self.regressor = nn.Sequential(
            nn.Linear(self._flat_size, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Tanh(),
        )

    def _get_flat_size(self) -> int:
        with torch.no_grad():
            dummy = torch.zeros(1, 1, 32, 100)
            out = self.features(dummy)
            return int(out.numel())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.regressor(x)


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def build_model(device: str = "cpu") -> LaneCNN:
    model = LaneCNN().to(device)
    n = count_parameters(model)
    print(f"LaneCNN: {n:,} обучаемых параметров")
    return model


class LaneCNNClassifier(nn.Module):
    """
    Бинарный классификатор: Sigmoid вместо Tanh.
    Выход: вероятность "в полосе" p в [0, 1].
    Используется только для сравнительного эксперимента BCE vs MSE.
    Обновлён: 2026-04-28 МСК
    """

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 8, kernel_size=3, stride=2, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(8, 16, kernel_size=3, stride=1, padding=1),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
        )
        self._flat_size = self._get_flat_size()
        self.classifier = nn.Sequential(
            nn.Linear(self._flat_size, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 1),
            nn.Sigmoid(),
        )

    def _get_flat_size(self) -> int:
        with torch.no_grad():
            dummy = torch.zeros(1, 1, 32, 100)
            return int(self.features(dummy).numel())

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)
