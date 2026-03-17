# Дипломный проект — Behavioral Cloning

**Тема:** Система автономного управления автомобилем на основе нейронных сетей

**Суть:** End-to-end нейросеть (NVIDIA PilotNet) обучается по записям вождения человека.
На вход — изображение с камеры, на выход — угол поворота руля.

**Среда:** Google Colab (GPU T4), Python 3.10
**Датасет:** Udacity Self-Driving Car Simulator (Kaggle: `ronamgir/udacity-car-dataset-simulator-challenge`)

---

## Структура проекта

```
diploma/
├── notebooks/
│   ├── 00_install.ipynb         # Первый запуск: клонирование с GitHub, установка
│   ├── 01_setup_and_data.ipynb  # Загрузка датасета, анализ, гистограммы
│   ├── 02_preprocessing.ipynb  # Предобработка, аугментация, балансировка
│   ├── 03_model_training.ipynb  # Обучение PilotNet, кривые loss
│   ├── 04_evaluation.ipynb      # Метрики MSE/MAE/R², визуализация ошибок
│   └── 05_yolo_detection.ipynb  # YOLOv8 детекция + объединённый пайплайн
├── src/
│   ├── model.py                 # Архитектура NVIDIA PilotNet CNN
│   ├── dataset.py               # DataLoader, аугментация, балансировка
│   ├── train.py                 # Цикл обучения, EarlyStopping, Adam
│   ├── evaluate.py              # Метрики и графики
│   └── utils.py                 # GPU, seed, Colab-хелперы
├── requirements.txt
├── README.md
└── CLAUDE.md                    # Этот файл
```

Папки создаются автоматически при первом запуске в Colab:
```
diploma/
├── data/        # Датасет Udacity (dataset.zip → распаковывается в 01_setup)
├── models/      # best_model.pth сохраняется после обучения
└── outputs/     # Все графики и визуализации
```

---

## Как запускать (Google Colab)

1. Открыть `notebooks/00_install.ipynb` в Colab
2. Сменить среду: `Среда выполнения → GPU (T4)`
3. В ячейке 3 вставить свой GitHub username
4. Нажать **Ctrl+F9** — установит всё автоматически
5. Положить `dataset.zip` в `diploma/data/` на Google Drive
6. Запускать ноутбуки по порядку: `01 → 02 → 03 → 04 → 05`

---

## Архитектура модели (PilotNet)

Вход: изображение 66×200×3 (YUV, нормализованное в [-1, 1])

```
Conv 5×5 stride 2 → 24 фильтра  + BatchNorm + ELU
Conv 5×5 stride 2 → 36 фильтров + BatchNorm + ELU
Conv 5×5 stride 2 → 48 фильтров + BatchNorm + ELU
Conv 3×3           → 64 фильтра  + BatchNorm + ELU
Conv 3×3           → 64 фильтра  + BatchNorm + ELU
Flatten → 1152
Dropout(0.5) → Dense 100 → ELU
Dropout(0.25) → Dense 50 → ELU
Dense 10 → ELU → Dense 1 → Tanh
```

Выход: угол руля [-1, 1]

---

## Что уже сделано

- [x] `requirements.txt` — все зависимости
- [x] `README.md` — описание проекта
- [x] `src/model.py` — PilotNet CNN с BatchNorm, ELU, Dropout
- [x] `src/dataset.py` — загрузка Udacity CSV, 3 камеры, аугментация, балансировка
- [x] `src/train.py` — Adam, MSE loss, EarlyStopping, ReduceLROnPlateau
- [x] `src/evaluate.py` — MSE/MAE/R², 3 вида графиков
- [x] `src/utils.py` — GPU-хелперы, seed, Colab-пути
- [x] `notebooks/00_install.ipynb` — автоустановка из GitHub
- [x] `notebooks/01_setup_and_data.ipynb` — загрузка и анализ данных
- [x] `notebooks/02_preprocessing.ipynb` — предобработка и балансировка
- [x] `notebooks/03_model_training.ipynb` — обучение
- [x] `notebooks/04_evaluation.ipynb` — оценка качества
- [x] `notebooks/05_yolo_detection.ipynb` — YOLOv8 + совместный пайплайн

## Что ещё можно сделать

- [ ] Загрузить датасет на Google Drive, проверить запуск в Colab
- [ ] Запустить обучение, получить метрики
- [ ] Написать главы диплома (описание архитектуры, результаты)
- [ ] Добавить LSTM для учёта истории кадров
- [ ] Сделать демо-видео с работающим пайплайном

---

## Ключевые решения

| Решение | Зачем |
|---------|-------|
| 3 камеры (center/left/right) | Утраивает датасет, учит возвращаться к центру |
| Балансировка по углу руля | Убирает перекос: 80% данных — прямая езда |
| YUV вместо RGB | Лучше разделяет яркость от цвета, устойчивее к освещению |
| BatchNorm после Conv | Стабилизирует обучение, ускоряет сходимость |
| EarlyStopping patience=10 | Предотвращает переобучение |
| Коррекция угла ±0.25 | Для левой/правой камеры — учит держать полосу |
