"""
model.py — Архитектура нейронной сети NVIDIA PilotNet
======================================================
Оригинальная статья: "End to End Learning for Self-Driving Cars"
Авторы: Bojarski et al., NVIDIA (2016)
https://arxiv.org/abs/1604.07316

Задача: по изображению с камеры предсказать угол поворота руля.
Вход:  изображение 66x200x3 (формат YUV)
Выход: одно число — угол руля (нормализованный, от -1 до 1)
"""

import torch
import torch.nn as nn


# ──────────────────────────────────────────────
# Воспроизводимость результатов
# ──────────────────────────────────────────────
torch.manual_seed(42)


class PilotNet(nn.Module):
    """
    Реализация архитектуры NVIDIA PilotNet.

    Сеть состоит из двух частей:
      1. Свёрточная часть (feature extractor) — извлекает признаки из изображения
      2. Полносвязная часть (regressor) — предсказывает угол руля

    Параметры
    ----------
    dropout_rate : float
        Вероятность отключения нейрона (Dropout) для регуляризации.
        По умолчанию 0.5.
    """

    def __init__(self, dropout_rate: float = 0.5):
        super(PilotNet, self).__init__()

        self.dropout_rate = dropout_rate

        # ──────────────────────────────────────────────
        # ЧАСТЬ 1: Свёрточные слои (извлечение признаков)
        # Формат: Conv2d(входные каналы, фильтры, ядро, шаг)
        # BatchNorm2d стабилизирует обучение после каждой свёртки
        # ──────────────────────────────────────────────
        self.conv_layers = nn.Sequential(

            # Слой 1: 3 канала → 24 карты признаков, ядро 5×5, шаг 2
            # Выход: (24, 31, 98)
            nn.Conv2d(3, 24, kernel_size=5, stride=2),
            nn.BatchNorm2d(24),
            nn.ELU(),

            # Слой 2: 24 → 36 карт, ядро 5×5, шаг 2
            # Выход: (36, 14, 47)
            nn.Conv2d(24, 36, kernel_size=5, stride=2),
            nn.BatchNorm2d(36),
            nn.ELU(),

            # Слой 3: 36 → 48 карт, ядро 5×5, шаг 2
            # Выход: (48, 5, 22)
            nn.Conv2d(36, 48, kernel_size=5, stride=2),
            nn.BatchNorm2d(48),
            nn.ELU(),

            # Слой 4: 48 → 64 карты, ядро 3×3, шаг 1
            # Выход: (64, 3, 20)
            nn.Conv2d(48, 64, kernel_size=3, stride=1),
            nn.BatchNorm2d(64),
            nn.ELU(),

            # Слой 5: 64 → 64 карты, ядро 3×3, шаг 1
            # Выход: (64, 1, 18)
            nn.Conv2d(64, 64, kernel_size=3, stride=1),
            nn.BatchNorm2d(64),
            nn.ELU(),
        )

        # ──────────────────────────────────────────────
        # ЧАСТЬ 2: Полносвязные слои (регрессор угла руля)
        # Dropout предотвращает переобучение
        # ──────────────────────────────────────────────
        self.fc_layers = nn.Sequential(

            # Выравниваем тензор: (64, 1, 18) → 1152
            nn.Flatten(),

            nn.Dropout(p=dropout_rate),

            # Полносвязный слой 1: 1152 → 100
            nn.Linear(1152, 100),
            nn.ELU(),

            nn.Dropout(p=dropout_rate / 2),

            # Полносвязный слой 2: 100 → 50
            nn.Linear(100, 50),
            nn.ELU(),

            # Полносвязный слой 3: 50 → 10
            nn.Linear(50, 10),
            nn.ELU(),

            # Выходной слой: 10 → 1 (угол руля)
            # Tanh ограничивает выход в диапазоне [-1, 1]
            nn.Linear(10, 1),
            nn.Tanh(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Прямой проход через сеть.

        Параметры
        ----------
        x : torch.Tensor
            Батч изображений формы (batch_size, 3, 66, 200)

        Возвращает
        ----------
        torch.Tensor
            Предсказанные углы руля формы (batch_size, 1)
        """
        # Проходим через свёрточные слои
        x = self.conv_layers(x)

        # Проходим через полносвязные слои
        x = self.fc_layers(x)

        return x

    def summary(self, device: str = "cpu") -> None:
        """
        Выводит архитектуру модели и количество параметров.

        Параметры
        ----------
        device : str
            Устройство для теста ('cpu' или 'cuda')
        """
        print("=" * 60)
        print("       АРХИТЕКТУРА NVIDIA PilotNet")
        print("=" * 60)
        print(self)
        print("=" * 60)

        # Считаем количество обучаемых параметров
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(
            p.numel() for p in self.parameters() if p.requires_grad
        )

        print(f"Всего параметров:       {total_params:,}")
        print(f"Обучаемых параметров:   {trainable_params:,}")
        print(f"Dropout rate:           {self.dropout_rate}")
        print("=" * 60)

        # Тестовый прогон — проверяем что размерности верны
        print("\nТест прямого прохода...")
        try:
            dummy_input = torch.zeros(1, 3, 66, 200).to(device)
            model_on_device = self.to(device)
            output = model_on_device(dummy_input)
            print(f"Вход:  {tuple(dummy_input.shape)}  →  (batch, каналы, высота, ширина)")
            print(f"Выход: {tuple(output.shape)}        →  (batch, угол_руля)")
            print("✓ Архитектура корректна\n")
        except Exception as e:
            print(f"✗ Ошибка при тестовом прогоне: {e}\n")


def get_model(dropout_rate: float = 0.5, device: str = "cpu") -> PilotNet:
    """
    Создаёт и возвращает модель PilotNet, перенесённую на нужное устройство.

    Параметры
    ----------
    dropout_rate : float
        Вероятность Dropout (по умолчанию 0.5)
    device : str
        'cuda' для GPU, 'cpu' для процессора

    Возвращает
    ----------
    PilotNet
        Готовая к обучению модель
    """
    model = PilotNet(dropout_rate=dropout_rate)
    model = model.to(device)
    return model


# ──────────────────────────────────────────────
# Быстрый тест при запуске файла напрямую
# ──────────────────────────────────────────────
if __name__ == "__main__":
    # Определяем устройство: GPU если доступен, иначе CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Используется устройство: {device}\n")

    # Создаём модель и выводим её описание
    model = get_model(dropout_rate=0.5, device=device)
    model.summary(device=device)
