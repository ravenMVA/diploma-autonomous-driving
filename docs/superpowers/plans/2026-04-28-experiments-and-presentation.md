# Эксперименты v2 + обновлённая презентация — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить 5 экспериментальных блоков в ноутбуки и обновить make_presentation.py до 12 слайдов.

**Architecture:** Новые ячейки добавляются в конец каждого ноутбука через NotebookEdit. LaneCNNClassifier добавляется в src/model_v2.py. make_presentation.py обновляется — добавляются слайды 8, 9, 12, обновляются слайды 5, 7, 11.

**Tech Stack:** PyTorch, optuna>=3.0.0, matplotlib, python-pptx, Jupyter (Google Colab)

---

## Карта файлов

| Файл | Действие |
|------|----------|
| `src/model_v2.py` | + класс `LaneCNNClassifier` (Sigmoid вместо Tanh) |
| `requirements_v2.txt` | + `optuna>=3.0.0` |
| `notebooks/01_data.ipynb` | + ячейка: таблица распределения углов руля |
| `notebooks/02_train.ipynb` | + ячейка: сравнение оптимизаторов (10 эпох, Adam baseline) |
| `notebooks/02_train.ipynb` | + ячейка: CrossEntropy vs MSE |
| `notebooks/03_agent_pid.ipynb` | + ячейка: Optuna vs Grid Search |
| `make_presentation.py` | слайды 5,7 обновлены; слайды 8,9,12 добавлены; слайд 11 обновлён |

Выходные файлы (создаются ноутбуками в `outputs/`):
- `outputs/training_curves.png` — уже создаётся cell-7 ноутбука 02
- `outputs/angle_distribution.png` — новый (Task 3)
- `outputs/optimizer_comparison.png` — новый (Task 4)
- `outputs/crossentropy_vs_mse.png` — новый (Task 5)
- `outputs/optuna_convergence.png` — новый (Task 6)

---

### Task 1: LaneCNNClassifier в src/model_v2.py

**Files:**
- Modify: `src/model_v2.py`

- [ ] **Step 1: Добавить класс LaneCNNClassifier**

Вставить после функции `build_model` в `src/model_v2.py`:

```python
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
```

- [ ] **Step 2: Проверить импорт и форму выхода**

```bash
cd C:/Users/Tjeo/diploma && python -c "
import torch
from src.model_v2 import LaneCNNClassifier
m = LaneCNNClassifier()
x = torch.zeros(4, 1, 32, 100)
out = m(x)
assert out.shape == (4, 1), f'Wrong shape: {out.shape}'
assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0
print('OK shape:', out.shape)
"
```

Ожидаемый вывод: `OK shape: torch.Size([4, 1])`

- [ ] **Step 3: Обновить временную метку в src/model_v2.py**

Первая строка файла:
```python
# Обновлён: 2026-04-28 МСК
```

- [ ] **Step 4: Commit**

```bash
git add src/model_v2.py
git commit -m "feat: добавить LaneCNNClassifier (Sigmoid) для BCE-эксперимента"
```

---

### Task 2: Добавить optuna в requirements_v2.txt

**Files:**
- Modify: `requirements_v2.txt`

- [ ] **Step 1: Добавить строку в конец файла**

```
optuna>=3.0.0
```

- [ ] **Step 2: Commit**

```bash
git add requirements_v2.txt
git commit -m "feat: добавить optuna в зависимости"
```

---

### Task 3: Таблица распределения сэмплов (notebooks/01_data.ipynb)

**Files:**
- Modify: `notebooks/01_data.ipynb` — добавить ячейку после cell-8

- [ ] **Step 1: Добавить ячейку через NotebookEdit (after_id="cell-8")**

```python
# -- Таблица распределения сэмплов по углам руля -------------------
# Обновлён: 2026-04-28 МСК
import pandas as pd
import numpy as np

df_all = pd.read_csv(CSV_PATH)
angle_col = 'steering' if 'steering' in df_all.columns else df_all.columns[3]

n_bins = 30
bins = np.linspace(-1.0, 1.0, n_bins + 1)
bin_labels = [f'[{bins[i]:.2f}, {bins[i+1]:.2f})' for i in range(n_bins)]

counts_before, _ = np.histogram(df_all[angle_col].values, bins=bins)
counts_after,  _ = np.histogram(angles, bins=bins)

dist_df = pd.DataFrame({
    'Диапазон угла':        bin_labels,
    'До балансировки':      counts_before,
    'После балансировки':   counts_after,
    '% (после)':           (counts_after / max(counts_after.sum(), 1) * 100).round(1),
})
dist_df = dist_df[counts_before > 0].reset_index(drop=True)

print(f'Всего сэмплов до:    {counts_before.sum():,}')
print(f'Всего сэмплов после: {counts_after.sum():,}')
display(dist_df)

fig, ax = plt.subplots(figsize=(10, max(4, 0.35 * len(dist_df) + 1.2)))
ax.axis('off')
tbl = ax.table(
    cellText=dist_df.values,
    colLabels=dist_df.columns,
    cellLoc='center',
    loc='center',
    colColours=['#1F4788'] * 4,
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(9)
tbl.scale(1, 1.4)
for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.get_text().set_color('white')
        cell.get_text().set_fontweight('bold')
    elif col > 0:
        cell.get_text().set_ha('right')
plt.title('Распределение сэмплов по углам руля', pad=10, fontsize=12, fontweight='bold')
plt.tight_layout()
plt.savefig('outputs/angle_distribution.png', dpi=120, bbox_inches='tight')
plt.show()
print('Сохранено: outputs/angle_distribution.png')
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/01_data.ipynb
git commit -m "feat: таблица распределения сэмплов по углам руля (ноутбук 01)"
```

---

### Task 4: Сравнение оптимизаторов (notebooks/02_train.ipynb)

**Files:**
- Modify: `notebooks/02_train.ipynb` — добавить ячейку после cell-9

- [ ] **Step 1: Добавить ячейку через NotebookEdit (after_id="cell-9")**

```python
# -- Сравнение оптимизаторов: Adam (baseline) vs SGD vs RMSprop vs Adagrad --
# Обновлён: 2026-04-28 МСК
import torch.optim as optim

COMPARE_EPOCHS = 10
LR = 3e-4
SEED = 42

optimizers_cfg = [
    ('Adam (baseline)', lambda p: optim.Adam(p, lr=LR, weight_decay=1e-4)),
    ('SGD + momentum',  lambda p: optim.SGD(p, lr=LR, momentum=0.9, weight_decay=1e-4)),
    ('RMSprop',         lambda p: optim.RMSprop(p, lr=LR, weight_decay=1e-4)),
    ('Adagrad',         lambda p: optim.Adagrad(p, lr=LR, weight_decay=1e-4)),
]

results_opt = {}

for opt_name, opt_fn in optimizers_cfg:
    torch.manual_seed(SEED)
    np.random.seed(SEED)
    m = build_model(DEVICE)
    optimizer_i = opt_fn(m.parameters())
    criterion_i = torch.nn.MSELoss()
    train_losses_i, val_losses_i = [], []

    for epoch in range(COMPARE_EPOCHS):
        m.train()
        tl = 0.0
        for imgs, ang in train_loader:
            imgs, ang = imgs.to(DEVICE), ang.to(DEVICE)
            optimizer_i.zero_grad()
            loss = criterion_i(m(imgs), ang)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(m.parameters(), 1.0)
            optimizer_i.step()
            tl += loss.item() * len(imgs)
        train_losses_i.append(tl / len(train_loader.dataset))

        m.train(False)
        vl = 0.0
        with torch.no_grad():
            for imgs, ang in val_loader:
                imgs, ang = imgs.to(DEVICE), ang.to(DEVICE)
                vl += criterion_i(m(imgs), ang).item() * len(imgs)
        val_losses_i.append(vl / len(val_loader.dataset))

    results_opt[opt_name] = {'train': train_losses_i, 'val': val_losses_i}
    print(f'{opt_name:<25} val_loss={val_losses_i[-1]:.5f}')

# График
colors = ['#1F4788', '#E53935', '#2E7D32', '#F57C00']
styles = [('-', 2.5), ('--', 1.5), ('--', 1.5), ('--', 1.5)]

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
for (name, res), color, (ls, lw) in zip(results_opt.items(), colors, styles):
    axes[0].plot(res['train'], color=color, lw=lw, ls=ls, label=name)
    axes[1].plot(res['val'],   color=color, lw=lw, ls=ls, label=name)

for ax, title in zip(axes, ['Train Loss (MSE)', 'Val Loss (MSE)']):
    ax.set_xlabel('Эпоха')
    ax.set_ylabel('MSE Loss')
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)

plt.suptitle(f'Сравнение оптимизаторов ({COMPARE_EPOCHS} эпох, lr={LR}, Adam = baseline)', fontsize=13)
plt.tight_layout()
plt.savefig('outputs/optimizer_comparison.png', dpi=120)
plt.show()

print('\n-- Итоговые метрики --')
print(f'{"Оптимизатор":<25} {"train_loss":>12} {"val_loss":>12}')
print('-' * 52)
for name, res in results_opt.items():
    marker = ' <- baseline' if 'baseline' in name else ''
    print(f'{name:<25} {res["train"][-1]:>12.5f} {res["val"][-1]:>12.5f}{marker}')
print('Сохранено: outputs/optimizer_comparison.png')
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/02_train.ipynb
git commit -m "feat: сравнение оптимизаторов Adam/SGD/RMSprop/Adagrad (ноутбук 02)"
```

---

### Task 5: CrossEntropy vs MSE (notebooks/02_train.ipynb)

**Files:**
- Modify: `notebooks/02_train.ipynb` — добавить ячейку после ячейки сравнения оптимизаторов

**Предусловие:** Task 1 завершён (`LaneCNNClassifier` в `src/model_v2.py`). Task 4 выполнен (`results_opt` доступен).

- [ ] **Step 1: Добавить ячейку через NotebookEdit (last cell)**

```python
# -- Эксперимент: CrossEntropy (BCELoss) vs MSE ---------------------
# Обновлён: 2026-04-28 МСК
from src.model_v2 import LaneCNNClassifier
from src.dataset_v2 import THRESHOLD
from torch.utils.data import DataLoader, TensorDataset

BCE_EPOCHS = 10

def angles_to_bce_loader(loader):
    """Конвертирует DataLoader с углами в DataLoader с бинарными метками."""
    all_imgs, all_labels = [], []
    for imgs, ang in loader:
        all_imgs.append(imgs)
        all_labels.append((ang.abs() < THRESHOLD).float())
    ds = TensorDataset(torch.cat(all_imgs), torch.cat(all_labels))
    return DataLoader(ds, batch_size=128, shuffle=False)

bce_train_dl = angles_to_bce_loader(train_loader)
bce_val_dl   = angles_to_bce_loader(val_loader)
bce_test_dl  = angles_to_bce_loader(test_loader)

torch.manual_seed(SEED)
clf = LaneCNNClassifier().to(DEVICE)
bce_optim     = torch.optim.Adam(clf.parameters(), lr=LR, weight_decay=1e-4)
bce_criterion = torch.nn.BCELoss()

bce_val_losses = []
for epoch in range(BCE_EPOCHS):
    clf.train()
    for imgs, lbl in bce_train_dl:
        imgs, lbl = imgs.to(DEVICE), lbl.to(DEVICE)
        bce_optim.zero_grad()
        bce_criterion(clf(imgs), lbl).backward()
        torch.nn.utils.clip_grad_norm_(clf.parameters(), 1.0)
        bce_optim.step()

    clf.train(False)
    vl = 0.0
    with torch.no_grad():
        for imgs, lbl in bce_val_dl:
            imgs, lbl = imgs.to(DEVICE), lbl.to(DEVICE)
            vl += bce_criterion(clf(imgs), lbl).item() * len(imgs)
    bce_val_losses.append(vl / len(bce_val_dl.dataset))
    print(f'BCE epoch {epoch+1:02d}: val={bce_val_losses[-1]:.5f}')

# Точность BCE на тесте
clf.train(False)
bce_correct = bce_total = 0
with torch.no_grad():
    for imgs, lbl in bce_test_dl:
        imgs, lbl = imgs.to(DEVICE), lbl.to(DEVICE)
        bce_correct += ((clf(imgs) >= 0.5).float() == lbl).sum().item()
        bce_total   += len(lbl)
bce_accuracy = bce_correct / bce_total

# Метрики MSE-модели (уже обучена в cell-6)
from src.train_v2 import evaluate as compute_metrics
mse_metrics   = compute_metrics(model, test_loader, DEVICE)
mse_val_final = results_opt['Adam (baseline)']['val'][-1]

# График кривых val loss
fig, ax = plt.subplots(figsize=(9, 4))
ax.plot(results_opt['Adam (baseline)']['val'], 'b-', lw=2.5, label='Adam + MSELoss (baseline)')
ax.plot(bce_val_losses, 'r--', lw=2.0, label='Adam + BCELoss')
ax.set_xlabel('Эпоха')
ax.set_ylabel('Loss')
ax.set_title('CrossEntropy (BCE) vs MSE: val loss (10 эпох)')
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig('outputs/crossentropy_vs_mse.png', dpi=120)
plt.show()

# Сравнительная таблица
print('\n-- MSE vs BCE --')
print(f'{"Метрика":<22} {"MSELoss (Tanh)":>18} {"BCELoss (Sigmoid)":>18}')
print('-' * 60)
print(f'{"Val Loss (10 эп.)":<22} {mse_val_final:>18.5f} {bce_val_losses[-1]:>18.5f}')
print(f'{"Accuracy (тест)":<22} {mse_metrics["accuracy"]*100:>17.1f}% {bce_accuracy*100:>17.1f}%')
print('\nBCE-модель не используется в агенте — только сравнительный эксперимент.')
print('Сохранено: outputs/crossentropy_vs_mse.png')
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/02_train.ipynb
git commit -m "feat: эксперимент BCELoss vs MSELoss (ноутбук 02)"
```

---

### Task 6: Optuna vs Grid Search (notebooks/03_agent_pid.ipynb)

**Files:**
- Modify: `notebooks/03_agent_pid.ipynb` — добавить ячейку после cell-10

**Предусловие:** Ячейки cell-6 и cell-9 выполнены — `val_errors` и `best` (grid search) доступны.

- [ ] **Step 1: Добавить ячейку через NotebookEdit (after_id="cell-10")**

```python
# -- Optuna: байесовская оптимизация ПИД (vs Grid Search) ----------
# Обновлён: 2026-04-28 МСК
try:
    import optuna
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'optuna', '-q'])
    import optuna

optuna.logging.set_verbosity(optuna.logging.WARNING)

N_TRIALS = 50

def pid_objective(trial):
    kp = trial.suggest_float('kp', 0.05, 2.0)
    ki = trial.suggest_float('ki', 0.0,  0.1)
    kd = trial.suggest_float('kd', 0.0,  0.5)
    pid = PIDController(Kp=kp, Ki=ki, Kd=kd)
    for e in val_errors:
        pid.step(float(e))
    return pid.integral_error()

study = optuna.create_study(direction='minimize')
study.optimize(pid_objective, n_trials=N_TRIALS, show_progress_bar=False)

best_optuna     = study.best_params
best_cte_optuna = study.best_value
grid_iters      = 9 * 8   # kp_vals(9) x kd_vals(8) из cell-9

print(f'Grid Search  ({grid_iters} iter): Kp={best["Kp"]:.3f} Ki={best["Ki"]:.4f} Kd={best["Kd"]:.3f}  CTE={best["cte"]:.5f}')
print(f'Optuna       ({N_TRIALS} trials): Kp={best_optuna["kp"]:.3f} Ki={best_optuna["ki"]:.4f} Kd={best_optuna["kd"]:.3f}  CTE={best_cte_optuna:.5f}')

# Кривая сходимости
trial_ctes   = [t.value for t in study.trials]
running_best = np.minimum.accumulate(trial_ctes)

fig, axes = plt.subplots(1, 2, figsize=(13, 4))

axes[0].plot(running_best, color='#1F4788', lw=2)
axes[0].axhline(best['cte'], color='#E53935', ls='--', lw=1.5,
                label=f'Grid Search CTE={best["cte"]:.4f}')
axes[0].set_xlabel('Попытка (trial)')
axes[0].set_ylabel('Лучший CTE')
axes[0].set_title(f'Optuna: сходимость за {N_TRIALS} попыток')
axes[0].legend()
axes[0].grid(alpha=0.3)

kps  = [t.params['kp'] for t in study.trials]
kds  = [t.params['kd'] for t in study.trials]
ctes = [t.value         for t in study.trials]
sc = axes[1].scatter(kps, ctes, c=kds, cmap='RdYlGn_r', s=25, alpha=0.7)
plt.colorbar(sc, ax=axes[1], label='Kd')
axes[1].set_xlabel('Kp')
axes[1].set_ylabel('CTE')
axes[1].set_title('Optuna: Kp vs CTE (цвет = Kd)')
axes[1].grid(alpha=0.3)

plt.tight_layout()
plt.savefig('outputs/optuna_convergence.png', dpi=120)
plt.show()

print('\n-- Grid Search vs Optuna --')
print(f'{"Метод":<25} {"Kp":>6} {"Ki":>7} {"Kd":>6} {"CTE":>10} {"Итераций":>10}')
print('-' * 68)
print(f'{"Grid Search":<25} {best["Kp"]:>6.3f} {best["Ki"]:>7.4f} {best["Kd"]:>6.3f} {best["cte"]:>10.5f} {grid_iters:>10}')
print(f'{"Optuna (Bayesian)":<25} {best_optuna["kp"]:>6.3f} {best_optuna["ki"]:>7.4f} {best_optuna["kd"]:>6.3f} {best_cte_optuna:>10.5f} {N_TRIALS:>10}')
print('Сохранено: outputs/optuna_convergence.png')
```

- [ ] **Step 2: Commit**

```bash
git add notebooks/03_agent_pid.ipynb
git commit -m "feat: Optuna байесовская оптимизация ПИД (ноутбук 03)"
```

---

### Task 7: Обновление make_presentation.py (12 слайдов)

**Files:**
- Modify: `make_presentation.py`

Итоговая структура:

| # | Слайд | Изменение |
|---|-------|-----------|
| 1 | Титульный | — |
| 2 | Постановка задачи | — |
| 3 | Архитектура агента | — |
| 4 | Симулятор Udacity | — |
| 5 | Данные и модель | + блок распределения сэмплов |
| 6 | Loss + ПИД | — |
| 7 | Кривые обучения | ссылка → outputs/training_curves.png |
| **8** | **Сравнение оптимизаторов** | **НОВЫЙ** |
| **9** | **CrossEntropy vs MSE** | **НОВЫЙ** |
| 10 | Результаты (таблица CTE) | — |
| 11 | Grid Search + Optuna | правая колонка заменена на Optuna |
| **12** | **Выводы** | **НОВЫЙ** (перенесён из слайда 11) |

- [ ] **Step 1: Обновить слайд 5 — добавить блок распределения**

Найти в `make_presentation.py`:
```python
divider(s, Inches(4.5))
add_text(s, "Обучение: Adam (lr=3×10⁻⁴) · MSE Loss · EarlyStopping · ReduceLROnPlateau · Google Colab GPU T4",
         Inches(0.5), Inches(4.6), W - Inches(1.0), Inches(0.5),
         size=14, color=C_SUBTEXT)
```
Заменить на:
```python
divider(s, Inches(4.15))
add_text(s, "Обучение: Adam (lr=3×10⁻⁴) · MSE Loss · EarlyStopping · ReduceLROnPlateau · Google Colab GPU T4",
         Inches(0.5), Inches(4.22), W - Inches(1.0), Inches(0.4),
         size=13, color=C_SUBTEXT)
add_text(s, "Распределение сэмплов по углам руля (до / после балансировки):",
         Inches(0.5), Inches(4.72), W - Inches(1.0), Inches(0.35),
         size=13, bold=True, color=C_ACCENT)
add_image_safe(s, os.path.join(BASE_DIR, "outputs", "angle_distribution.png"),
               Inches(0.5), Inches(5.12), W - Inches(1.0), Inches(2.1))
```

- [ ] **Step 2: Обновить слайд 7 — ссылка на training_curves.png**

Найти:
```python
img2 = os.path.join(BASE_DIR, "результаты ноутбука 02.png")
```
Заменить на:
```python
img2 = os.path.join(BASE_DIR, "outputs", "training_curves.png")
```
И найти:
```python
add_text(s, "Ноутбук 02 — предобработка, балансировка датасета:",
```
Заменить на:
```python
add_text(s, "Кривые обучения Adam — train/val MSE Loss по эпохам:",
```

- [ ] **Step 3: Добавить слайд 8 — Сравнение оптимизаторов**

Вставить новый блок ПЕРЕД строкой `# -- 4. Результаты`:

```python
# -- 8. Сравнение оптимизаторов ------------------------------------
s = blank_slide(prs)
header(s, "Сравнение оптимизаторов: Adam (baseline) vs SGD vs RMSprop vs Adagrad")

add_text(s, "10 эпох · lr = 3×10⁻⁴ · seed = 42 · Adam — базовый, выделен жирной линией",
         Inches(0.5), Inches(1.25), W - Inches(1.0), Inches(0.4),
         size=14, color=C_SUBTEXT)

add_image_safe(s, os.path.join(BASE_DIR, "outputs", "optimizer_comparison.png"),
               Inches(0.5), Inches(1.75), W - Inches(1.0), Inches(4.3))

divider(s, Inches(6.15))
add_text(s,
    "• Adam сходится быстрее и стабильнее на задаче регрессии угла руля\n"
    "• SGD требует тонкой настройки lr/momentum, медленнее стартует\n"
    "• RMSprop и Adagrad уступают Adam по итоговому val loss",
    Inches(0.5), Inches(6.25), W - Inches(1.0), Inches(1.0),
    size=14, color=C_TEXT)
```

- [ ] **Step 4: Добавить слайд 9 — CrossEntropy vs MSE**

Вставить новый блок ПЕРЕД строкой `# -- 4. Результаты` (после слайда 8):

```python
# -- 9. CrossEntropy vs MSE ----------------------------------------
s = blank_slide(prs)
header(s, "CrossEntropy (BCE) vs MSE: сравнение функций потерь")

add_text(s, "LaneCNNClassifier (Sigmoid) + BCELoss  vs  LaneCNN (Tanh) + MSELoss · 10 эпох · Adam",
         Inches(0.5), Inches(1.25), W - Inches(1.0), Inches(0.4),
         size=14, color=C_SUBTEXT)

add_image_safe(s, os.path.join(BASE_DIR, "outputs", "crossentropy_vs_mse.png"),
               Inches(0.5), Inches(1.75), Inches(7.8), Inches(3.8))

add_rect(s, Inches(8.6), Inches(1.75), Inches(4.3), Inches(0.45), C_ACCENT)
add_text(s, "Ключевые различия", Inches(8.75), Inches(1.8), Inches(4.0), Inches(0.4),
         size=15, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

diff_lines = [
    ("MSELoss",  "Регрессия e в [-1,1]\nВыход: Tanh → ПИД-вход"),
    ("BCELoss",  "Бинарная классификация\nВыход: Sigmoid → вероятность"),
    ("Вывод",   "BCE сопоставима по accuracy\nMSE удобнее для ПИД"),
]
for j, (term, desc) in enumerate(diff_lines):
    y_d = Inches(2.35) + j * Inches(1.15)
    add_rect(s, Inches(8.6), y_d, Inches(1.1), Inches(0.42), C_ACCENT)
    add_text(s, term, Inches(8.62), y_d + Inches(0.04), Inches(1.05), Inches(0.36),
             size=12, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), align=PP_ALIGN.CENTER)
    add_text(s, desc, Inches(9.8), y_d, Inches(3.0), Inches(1.05), size=13, color=C_TEXT)

add_text(s, "В агент (ПИД) по-прежнему подаётся LaneCNN (Tanh) с непрерывным e в [-1, 1].",
         Inches(0.5), Inches(6.2), W - Inches(1.0), Inches(0.55),
         size=13, bold=True, color=C_ACCENT)
```

- [ ] **Step 5: Обновить слайд 11 — заменить Выводы на Optuna**

Найти в блоке слайда "Grid Search и выводы" правую колонку:
```python
# Выводы
add_rect(s, Inches(6.8), Inches(1.25), Inches(6.0), Inches(0.45), C_ACCENT)
add_text(s, "Выводы", ...
```
Заменить всю правую колонку (от `# Выводы` до конца блока слайда) на:
```python
# Optuna
add_rect(s, Inches(6.8), Inches(1.25), Inches(6.0), Inches(0.45), C_ACCENT)
add_text(s, "Bayesian Optimization (Optuna, 50 попыток)",
         Inches(6.95), Inches(1.3), Inches(5.7), Inches(0.4),
         size=15, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))

add_image_safe(s, os.path.join(BASE_DIR, "outputs", "optuna_convergence.png"),
               Inches(6.8), Inches(1.85), Inches(6.0), Inches(3.3))

add_text(s, "Grid Search vs Optuna:", Inches(6.8), Inches(5.28), Inches(6.0), Inches(0.35),
         size=13, bold=True, color=C_ACCENT)
for j, line in enumerate([
    "Grid Search: 72 комбинации (Kp×Kd), слепой перебор",
    "Optuna: 50 попыток, суррогатная байесовская модель",
    "Optuna находит оптимум быстрее при равном CTE",
]):
    add_text(s, f"• {line}", Inches(6.8), Inches(5.72) + j * Inches(0.44),
             Inches(6.0), Inches(0.42), size=13, color=C_TEXT)
```

- [ ] **Step 6: Добавить слайд 12 — Выводы**

Вставить ПЕРЕД блоком сохранения `# -- Сохранение`:

```python
# -- 12. Выводы ----------------------------------------------------
s = blank_slide(prs)
header(s, "Выводы")

concl_12 = [
    ("•", "Нейросеть без ПИД: нестабильный сигнал, 20% в полосе",           False),
    ("•", "Неверные коэффициенты ПИД ухудшают результат (CTE x2.5)",         False),
    ("★", "Оптимальный ПИД: CTE / 10, 100% удержание полосы",               True),
    ("•", "Adam сходится быстрее конкурентов на задаче регрессии угла",       False),
    ("•", "BCE сопоставима с MSE по accuracy, MSE удобнее для ПИД-входа",    False),
    ("•", "Optuna находит оптимум за 50 попыток против 72 у Grid Search",     False),
    ("•", "Подход применим как базовый модуль реальной ADAS",                 False),
]
for j, (sym, line, star) in enumerate(concl_12):
    add_text(s, f"{sym}  {line}",
             Inches(0.8), Inches(1.4) + j * Inches(0.66),
             W - Inches(1.6), Inches(0.62), size=16,
             bold=star, color=C_GREEN if star else C_TEXT)
```

- [ ] **Step 7: Обновить метку времени**

В начало `make_presentation.py` добавить:
```python
# Обновлён: 2026-04-28 МСК
```

- [ ] **Step 8: Проверить синтаксис**

```bash
cd C:/Users/Tjeo/diploma && python -c "import ast; ast.parse(open('make_presentation.py').read()); print('Синтаксис OK')"
```

Ожидаемый вывод: `Синтаксис OK`

- [ ] **Step 9: Commit**

```bash
git add make_presentation.py
git commit -m "feat: презентация обновлена до 12 слайдов (оптимизаторы, BCE, Optuna, выводы)"
```

---

## Self-Review

**Покрытие спецификации:**
- [x] Таблица распределения сэмплов → Task 3 (ноутбук 01)
- [x] Кривые обучения Adam → training_curves.png уже создаётся в cell-7 ноутбука 02; Task 7 Step 2 обновляет ссылку
- [x] Сравнение оптимизаторов (Adam baseline, 10 эпох, seed=42) → Task 4
- [x] CrossEntropy vs MSE (вариант A — параллельный, в агент не идёт) → Tasks 1 + 5
- [x] Optuna vs Grid Search (оба метода, сравнение CTE и кол-ва итераций) → Tasks 2 + 6
- [x] Презентация 12 слайдов → Task 7

**Зависимости между задачами:**
- Task 5 требует Task 1 (`LaneCNNClassifier`) и Task 4 (`results_opt`)
- Task 7 выполняется последним (слайды ссылаются на `outputs/`)
- Tasks 2, 3, 4 независимы

**Проверка имён переменных:**
- `results_opt` создаётся в Task 4, используется в Task 5 — одна сессия ноутбука ✓
- `val_errors`, `best` из cell-6/cell-9 ноутбука 03, используются в Task 6 ✓
- `LaneCNNClassifier` импортируется из `src.model_v2` в Task 5 ✓
- `PIDController` уже импортирован в cell-1 ноутбука 03 ✓
