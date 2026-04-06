"""
pid.py — ПИД-регулятор для стабилизации агента в полосе.

Роль в системе:
    Нейросеть (чёрный ящик) предсказывает ошибку отклонения e ∈ [-1, 1].
    ПИД получает e и вычисляет корректирующий сигнал управления u.
    Цель: минимизировать ∫|e(t)| dt.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List


@dataclass
class PIDController:
    """
    ПИД-регулятор с ограничением интеграла (anti-windup).

    Параметры:
        Kp  — пропорциональная составляющая (быстрая реакция)
        Ki  — интегральная составляющая (устранение статической ошибки)
        Kd  — дифференциальная составляющая (демпфирование колебаний)
        dt  — шаг времени, секунды (по умолчанию 1/30 для 30 FPS)
        clip_u       — ограничение выходного сигнала [-clip_u, clip_u]
        integral_max — ограничение накопленного интеграла (anti-windup)
    """
    Kp: float = 0.8
    Ki: float = 0.01
    Kd: float = 0.15
    dt: float = 1.0 / 30.0
    clip_u: float = 1.0
    integral_max: float = 5.0

    # Внутреннее состояние (не параметры конструктора)
    _integral:   float = field(default=0.0, init=False, repr=False)
    _prev_error: float = field(default=0.0, init=False, repr=False)
    _history:    List  = field(default_factory=list, init=False, repr=False)

    def step(self, error: float) -> float:
        """
        Один шаг регулятора.

        Args:
            error: текущая ошибка e = предсказание нейросети

        Returns:
            u: управляющий сигнал (угол руля) ∈ [-clip_u, clip_u]
        """
        # Пропорциональная составляющая
        p = self.Kp * error

        # Интегральная составляющая с anti-windup
        self._integral += error * self.dt
        self._integral = np.clip(self._integral, -self.integral_max, self.integral_max)
        i = self.Ki * self._integral

        # Дифференциальная составляющая
        d = self.Kd * (error - self._prev_error) / self.dt
        self._prev_error = error

        u = float(np.clip(p + i + d, -self.clip_u, self.clip_u))
        self._history.append({"e": error, "p": p, "i": i, "d": d, "u": u})
        return u

    def reset(self):
        """Сброс состояния (начало нового эпизода)."""
        self._integral   = 0.0
        self._prev_error = 0.0
        self._history    = []

    @property
    def history(self) -> List[dict]:
        return self._history

    def integral_error(self) -> float:
        """Интегральная ошибка за эпизод (Cross-Track Error)."""
        if not self._history:
            return float("inf")
        return float(np.mean([abs(h["e"]) for h in self._history]))


def tune_pid(errors: np.ndarray, kp_range=(0.1, 2.0), ki_range=(0.0, 0.1),
             kd_range=(0.0, 0.5), steps: int = 5) -> dict:
    """
    Grid search оптимальных коэффициентов ПИД по минимуму интегральной ошибки.

    Args:
        errors: массив предсказанных ошибок (из нейросети на валидационном треке)
        steps:  число шагов по каждой оси (итого steps³ комбинаций)

    Returns:
        dict с ключами Kp, Ki, Kd, cte (лучшая интегральная ошибка)
    """
    best = {"Kp": 0.8, "Ki": 0.01, "Kd": 0.15, "cte": float("inf")}

    kp_vals = np.linspace(*kp_range, steps)
    ki_vals = np.linspace(*ki_range, steps)
    kd_vals = np.linspace(*kd_range, steps)

    for kp in kp_vals:
        for ki in ki_vals:
            for kd in kd_vals:
                pid = PIDController(Kp=kp, Ki=ki, Kd=kd)
                for e in errors:
                    pid.step(float(e))
                cte = pid.integral_error()
                if cte < best["cte"]:
                    best = {"Kp": float(kp), "Ki": float(ki),
                            "Kd": float(kd), "cte": cte}

    print(f"Лучшие параметры: Kp={best['Kp']:.3f}, Ki={best['Ki']:.4f}, "
          f"Kd={best['Kd']:.3f}  →  CTE={best['cte']:.5f}")
    return best
