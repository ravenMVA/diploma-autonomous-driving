"""
make_presentation.py — генерирует presentation.pptx с результатами диплома.
Обновлён: 2026-04-10 00:35 МСК

Запуск в Colab:
    !pip install python-pptx -q
    !python /content/drive/MyDrive/diploma/make_presentation.py
"""

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import os

# ── Цвета ────────────────────────────────────────────────────────
C_BG        = RGBColor(0xFF, 0xFF, 0xFF)  # белый
C_ACCENT    = RGBColor(0x1F, 0x47, 0x88)  # тёмно-синий
C_TEXT      = RGBColor(0x1A, 0x1A, 0x1A)  # почти чёрный
C_SUBTEXT   = RGBColor(0x55, 0x55, 0x55)  # серый
C_GREEN     = RGBColor(0x2E, 0x7D, 0x32)  # тёмно-зелёный
C_RED       = RGBColor(0xC6, 0x28, 0x28)  # тёмно-красный
C_HEADER_BG = RGBColor(0x1F, 0x47, 0x88)  # синяя шапка

W = Inches(13.33)  # ширина слайда 16:9
H = Inches(7.5)


def new_prs() -> Presentation:
    prs = Presentation()
    prs.slide_width  = W
    prs.slide_height = H
    return prs


def blank_slide(prs):
    layout = prs.slide_layouts[6]  # полностью пустой
    return prs.slides.add_slide(layout)


def add_rect(slide, x, y, w, h, color):
    shape = slide.shapes.add_shape(1, x, y, w, h)  # MSO_SHAPE_TYPE.RECTANGLE=1
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def add_text(slide, text, x, y, w, h,
             size=18, bold=False, color=C_TEXT,
             align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(x, y, w, h)
    tf  = txb.text_frame
    tf.word_wrap = wrap
    p   = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size  = Pt(size)
    run.font.bold  = bold
    run.font.color.rgb = color
    return txb


def header(slide, title_text):
    """Синяя полоса сверху с заголовком."""
    add_rect(slide, 0, 0, W, Inches(1.1), C_HEADER_BG)
    add_text(slide, title_text,
             Inches(0.4), Inches(0.15), W - Inches(0.8), Inches(0.8),
             size=28, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))


def divider(slide, y):
    add_rect(slide, Inches(0.4), y, W - Inches(0.8), Pt(1.5),
             RGBColor(0xCC, 0xCC, 0xCC))


# ══════════════════════════════════════════════════════════════════
# Слайды
# ══════════════════════════════════════════════════════════════════

prs = new_prs()

# ── 1. Титульный слайд ───────────────────────────────────────────
s = blank_slide(prs)
add_rect(s, 0, 0, W, H, C_ACCENT)

add_text(s, "Система автономного удержания полосы\nна основе нейронных сетей и ПИД-регулятора",
         Inches(0.8), Inches(1.8), W - Inches(1.6), Inches(2.4),
         size=36, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF), align=PP_ALIGN.CENTER)

add_text(s, "Нейронная сеть (LaneCNN)  +  ПИД-регулятор",
         Inches(0.8), Inches(3.8), W - Inches(1.6), Inches(0.6),
         size=20, color=RGBColor(0xAA, 0xC4, 0xE8), align=PP_ALIGN.CENTER)

add_rect(s, Inches(3.5), Inches(4.6), Inches(6.3), Pt(1.5),
         RGBColor(0xFF, 0xFF, 0xFF))

add_text(s, "Филиппов Фёдор  |  Группа М8О-404Б  |  2026",
         Inches(0.8), Inches(4.9), W - Inches(1.6), Inches(0.6),
         size=18, color=RGBColor(0xDD, 0xDD, 0xDD), align=PP_ALIGN.CENTER)


# ── 2. Постановка задачи ─────────────────────────────────────────
s = blank_slide(prs)
header(s, "Постановка задачи")

add_text(s, "Цель: автономное удержание полосы движения без GPS и карт — только по изображению с камеры.",
         Inches(0.5), Inches(1.3), W - Inches(1.0), Inches(0.6),
         size=18, color=C_TEXT)

divider(s, Inches(2.05))

# Два блока рядом
for i, (title, lines) in enumerate([
    ("Нейронная сеть (LaneCNN)",
     ["Вход: кадр камеры grayscale 32×100",
      "Выход: ошибка отклонения e ∈ [−1, 1]",
      "Роль: «чёрный ящик» — оценка положения в полосе"]),
    ("ПИД-регулятор",
     ["Вход: ошибка e(t) от нейросети",
      "Выход: управляющий сигнал u(t)",
      "Цель: минимизировать ∫|e(t)| dt",
      "Сглаживает шум, подавляет перерегулирование"]),
]):
    x = Inches(0.5) + i * Inches(6.5)
    add_rect(s, x, Inches(2.2), Inches(6.0), Inches(0.5), C_ACCENT)
    add_text(s, title, x + Inches(0.15), Inches(2.25), Inches(5.7), Inches(0.45),
             size=16, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
    for j, line in enumerate(lines):
        add_text(s, f"• {line}", x + Inches(0.2),
                 Inches(2.85) + j * Inches(0.52),
                 Inches(5.7), Inches(0.5), size=15, color=C_TEXT)


# ── 3. Данные и модель ───────────────────────────────────────────
s = blank_slide(prs)
header(s, "Данные и архитектура модели")

# Датасет
add_rect(s, Inches(0.5), Inches(1.25), Inches(5.8), Inches(0.45), C_ACCENT)
add_text(s, "Датасет Udacity (jungle)", Inches(0.65), Inches(1.3),
         Inches(5.5), Inches(0.4), size=16, bold=True,
         color=RGBColor(0xFF, 0xFF, 0xFF))
for j, line in enumerate([
    "3 403 записей  →  1 753 сэмпла (стратификация по углу руля)",
    "16.8% «в полосе» (|e| < 0.15)  |  83.2% «вне полосы»",
    "Среда записи: Windows → абсолютные пути исправлены автоматически",
]):
    add_text(s, f"• {line}", Inches(0.65), Inches(1.85) + j * Inches(0.48),
             Inches(5.5), Inches(0.45), size=14, color=C_TEXT)

# Архитектура
add_rect(s, Inches(6.8), Inches(1.25), Inches(6.0), Inches(0.45), C_ACCENT)
add_text(s, "Архитектура LaneCNN", Inches(6.95), Inches(1.3),
         Inches(5.7), Inches(0.4), size=16, bold=True,
         color=RGBColor(0xFF, 0xFF, 0xFF))
arch_lines = [
    "Вход: 1×32×100 (grayscale, нормировка [-1,1])",
    "Conv(8) → ReLU → MaxPool  ×3",
    "Flatten → Dense(256) → Dropout(0.3)",
    "Dense(64) → Dense(1) → Tanh",
    "Выход: угол руля ∈ [−1, 1]",
]
for j, line in enumerate(arch_lines):
    add_text(s, f"• {line}", Inches(6.95), Inches(1.85) + j * Inches(0.48),
             Inches(5.7), Inches(0.45), size=14, color=C_TEXT)

divider(s, Inches(4.5))
add_text(s, "Обучение: Adam (lr=3×10⁻⁴) · MSE Loss · EarlyStopping · ReduceLROnPlateau · Google Colab GPU T4",
         Inches(0.5), Inches(4.6), W - Inches(1.0), Inches(0.5),
         size=14, color=C_SUBTEXT)


# ── 4. Результаты ────────────────────────────────────────────────
s = blank_slide(prs)
header(s, "Результаты: сравнение методов")

add_text(s, "Тестовый трек: 263 кадра (15% от выборки)  |  Метрика CTE = mean(|u(t)|)",
         Inches(0.5), Inches(1.2), W - Inches(1.0), Inches(0.45),
         size=15, color=C_SUBTEXT)

# Таблица
col_x = [Inches(0.5), Inches(5.2), Inches(7.8), Inches(10.4)]
col_w = [Inches(4.5), Inches(2.4), Inches(2.4), Inches(2.3)]
headers_t = ["Метод", "CTE ↓", "В полосе ↑", "Награда"]
rows = [
    ("Только нейросеть",           "0.3258", "20.2%",  "−156",  C_RED),
    ("Нейросеть + ПИД (базовые)",  "0.8359", "2.7%",   "−248",  C_RED),
    ("Нейросеть + ПИД (оптим.)",   "0.0326", "100.0%", "+262",  C_GREEN),
]

# Заголовок таблицы
add_rect(s, Inches(0.5), Inches(1.8), W - Inches(1.0), Inches(0.5),
         RGBColor(0xE8, 0xEE, 0xF7))
for i, (hdr, cx, cw) in enumerate(zip(headers_t, col_x, col_w)):
    add_text(s, hdr, cx + Inches(0.1), Inches(1.82), cw, Inches(0.45),
             size=15, bold=True, color=C_ACCENT)

# Строки
for row_i, (method, cte, pct, rew, color) in enumerate(rows):
    y = Inches(2.4) + row_i * Inches(0.72)
    bg = RGBColor(0xF5, 0xF5, 0xF5) if row_i % 2 == 0 else C_BG
    add_rect(s, Inches(0.5), y, W - Inches(1.0), Inches(0.68), bg)
    vals = [method, cte, pct, rew]
    for i, (val, cx, cw) in enumerate(zip(vals, col_x, col_w)):
        c = color if i > 0 and row_i == 2 else (C_RED if i > 0 and row_i < 2 else C_TEXT)
        b = (row_i == 2)
        add_text(s, val, cx + Inches(0.1), y + Inches(0.1), cw, Inches(0.5),
                 size=15, bold=b, color=c)

add_text(s, "★  Оптимальный ПИД снижает CTE в 10× и обеспечивает 100% удержание полосы",
         Inches(0.5), Inches(4.6), W - Inches(1.0), Inches(0.5),
         size=16, bold=True, color=C_GREEN)


# ── 5. Grid Search и выводы ──────────────────────────────────────
s = blank_slide(prs)
header(s, "Grid Search и выводы")

# Grid Search
add_rect(s, Inches(0.5), Inches(1.25), Inches(5.8), Inches(0.45), C_ACCENT)
add_text(s, "Grid Search: Kp ∈ [0.1, 2.0], Kd ∈ [0.0, 0.5]",
         Inches(0.65), Inches(1.3), Inches(5.5), Inches(0.4),
         size=15, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
gs_lines = [
    "Оптимум: малый Kp (0.1–0.4), Kd ≈ 0",
    "Большой Kd усиливает шум нейросети → CTE растёт",
    "Большой Kp вызывает перерегулирование",
    "ПИД работает как сглаживатель, а не активный регулятор",
]
for j, line in enumerate(gs_lines):
    add_text(s, f"• {line}", Inches(0.65), Inches(1.85) + j * Inches(0.5),
             Inches(5.5), Inches(0.48), size=14, color=C_TEXT)

# Выводы
add_rect(s, Inches(6.8), Inches(1.25), Inches(6.0), Inches(0.45), C_ACCENT)
add_text(s, "Выводы", Inches(6.95), Inches(1.3), Inches(5.7), Inches(0.4),
         size=15, bold=True, color=RGBColor(0xFF, 0xFF, 0xFF))
concl = [
    "Нейросеть без ПИД: нестабильный сигнал, 20% в полосе",
    "Неверные коэф. ПИД ухудшают результат (CTE ×2.5)",
    "Оптимальный ПИД: CTE ÷10, 100% удержание полосы",
    "Связка «нейросеть + ПИД» эффективна только при\nправильном подборе коэффициентов",
    "Подход применим как базовый модуль реальной ADAS",
]
for j, line in enumerate(concl):
    add_text(s, f"{'★' if j == 2 else '•'} {line}",
             Inches(6.95), Inches(1.85) + j * Inches(0.58),
             Inches(5.7), Inches(0.55), size=14,
             bold=(j == 2), color=C_GREEN if j == 2 else C_TEXT)


# ── Сохранение ───────────────────────────────────────────────────
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "diploma_presentation.pptx")
prs.save(OUT)
print(f"Готово: {OUT}")
