# -*- coding: utf-8 -*-
"""
Генерация PPTX-презентации по дипломному проекту.
Зависимости: только стандартная библиотека Python.
"""
import zipfile

# ─── Размеры ──────────────────────────────────────────────────────────────────
W = 12192000   # 13.33 дюйма × 914400
H =  6858000   # 7.5  дюйма × 914400

def emu(inches): return int(inches * 914400)
def pt(n):       return int(n * 12700)

# ─── Цвета ────────────────────────────────────────────────────────────────────
BG     = "0D1B2A"
ACCENT = "00B4D8"
WHITE  = "FFFFFF"
LIGHT  = "B0C4DE"
YELLOW = "FFD166"
DARK   = "060F1A"
BLUE2  = "004A6B"

# ─── Namespace-декларации для слайдов ────────────────────────────────────────
SLD_NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
          'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')

# ─── Примитивы XML ────────────────────────────────────────────────────────────

def solid_fill(color):
    return f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'

def no_fill():
    return '<a:noFill/>'

def no_line():
    return '<a:ln><a:noFill/></a:ln>'

def line_xml(color, w=pt(1)):
    return f'<a:ln w="{w}">{solid_fill(color)}</a:ln>'

def xfrm(x, y, cx, cy):
    return (f'<a:xfrm><a:off x="{x}" y="{y}"/>'
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>')

def sp_pr(x, y, cx, cy, fill_xml, line_xml_str):
    return (f'<p:spPr>{xfrm(x,y,cx,cy)}'
            f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
            f'{fill_xml}{line_xml_str}</p:spPr>')

def nv_sp_pr(idx, name):
    return (f'<p:nvSpPr>'
            f'<p:cNvPr id="{idx}" name="{name}"/>'
            f'<p:cNvSpPr txBox="1"/>'
            f'<p:nvPr/>'
            f'</p:nvSpPr>')


def rect_shape(idx, x, y, cx, cy, fill=None, line_color=None, line_w=pt(1)):
    fill_xml = solid_fill(fill) if fill else no_fill()
    ln_xml   = line_xml(line_color, line_w) if line_color else no_line()
    body = ('<p:txBody><a:bodyPr/><a:lstStyle/><a:p/></p:txBody>')
    return (f'<p:sp>'
            f'{nv_sp_pr(idx, "r"+str(idx))}'
            f'{sp_pr(x,y,cx,cy, fill_xml, ln_xml)}'
            f'{body}'
            f'</p:sp>')


def text_shape(idx, x, y, cx, cy, lines,
               size=18, bold=False, italic=False,
               color=WHITE, align="l", wrap=True):
    """lines: list[str]  — каждая строка отдельным <a:p>"""
    fill_xml = no_fill()
    ln_xml   = no_line()
    wrap_attr = "square" if wrap else "none"
    aligns = {"l": "l", "c": "ctr", "r": "r"}
    algn = aligns.get(align, "l")

    paras = []
    for line in lines:
        b_val = "1" if bold else "0"
        i_val = "1" if italic else "0"
        if line == "":
            paras.append('<a:p><a:endParaRPr lang="ru-RU"/></a:p>')
        else:
            safe = (line.replace("&","&amp;")
                        .replace("<","&lt;")
                        .replace(">","&gt;")
                        .replace('"',"&quot;"))
            paras.append(
                f'<a:p>'
                f'<a:pPr algn="{algn}"/>'
                f'<a:r>'
                f'<a:rPr lang="ru-RU" sz="{size*100}" b="{b_val}" i="{i_val}" dirty="0">'
                f'{solid_fill(color)}'
                f'<a:latin typeface="Calibri"/>'
                f'</a:rPr>'
                f'<a:t>{safe}</a:t>'
                f'</a:r>'
                f'</a:p>'
            )
    body = (f'<p:txBody>'
            f'<a:bodyPr wrap="{wrap_attr}" rtlCol="0"/>'
            f'<a:lstStyle/>'
            + "".join(paras) +
            f'</p:txBody>')
    return (f'<p:sp>'
            f'{nv_sp_pr(idx, "t"+str(idx))}'
            f'{sp_pr(x,y,cx,cy, fill_xml, ln_xml)}'
            f'{body}'
            f'</p:sp>')


def txt(idx, x, y, cx, cy, text, **kw):
    """Удобная обёртка: text с \\n разбивается на строки."""
    return text_shape(idx, x, y, cx, cy, text.split("\n"), **kw)


def slide_xml(shapes_xml):
    """Собирает полный XML слайда из списка строк-шейпов."""
    bg = (f'<p:bg><p:bgPr>'
          f'{solid_fill(BG)}'
          f'<a:effectLst/>'
          f'</p:bgPr></p:bg>')

    sp_tree = (f'<p:spTree>'
               f'<p:nvGrpSpPr>'
               f'<p:cNvPr id="1" name=""/>'
               f'<p:cNvGrpSpPr/>'
               f'<p:nvPr/>'
               f'</p:nvGrpSpPr>'
               f'<p:grpSpPr>'
               f'<a:xfrm>'
               f'<a:off x="0" y="0"/>'
               f'<a:ext cx="{W}" cy="{H}"/>'
               f'<a:chOff x="0" y="0"/>'
               f'<a:chExt cx="{W}" cy="{H}"/>'
               f'</a:xfrm>'
               f'</p:grpSpPr>'
               + "".join(shapes_xml) +
               f'</p:spTree>')

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            f'<p:sld {SLD_NS}>'
            f'<p:cSld>{bg}{sp_tree}</p:cSld>'
            f'<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>'
            f'</p:sld>')


def slide_rels():
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" '
            'Target="../slideLayouts/slideLayout1.xml"/>'
            '</Relationships>')


# ─── Вспомогательные блоки ───────────────────────────────────────────────────

def stripe(base=0):
    """Голубая вертикальная полоса слева."""
    return rect_shape(base+1, 0, 0, emu(0.12), H, fill=ACCENT)

def header(idx, title):
    """Заголовок слайда + линия под ним."""
    return [
        txt(idx,   emu(0.3), emu(0.2), emu(12), emu(0.7),
            title, size=28, bold=True, color=ACCENT),
        rect_shape(idx+1, emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT),
    ]

def section(idx, x, y, cx, cy, label, items, label_color=YELLOW, item_color=WHITE, size=15):
    shapes = [txt(idx, x, y, cx, emu(0.45), label, size=17, bold=True, color=label_color)]
    shapes.append(txt(idx+1, x, y+emu(0.52), cx, cy, "\n".join(items), size=size, color=item_color))
    return shapes

def box(idx, x, y, cx, cy, lines, size=14, color=LIGHT, align="l"):
    shapes = [
        rect_shape(idx, x, y, cx, cy, fill=DARK, line_color=ACCENT, line_w=pt(1)),
        txt(idx+1, x+emu(0.15), y+emu(0.15), cx-emu(0.3), cy-emu(0.3),
            "\n".join(lines), size=size, color=color, align=align),
    ]
    return shapes


# ─── СЛАЙДЫ ──────────────────────────────────────────────────────────────────

def slide_title():
    s = [
        stripe(0),
        rect_shape(5, 0, emu(6.4), W, emu(1.1), fill=DARK),
        txt(10, emu(0.4), emu(0.35), emu(12), emu(0.5),
            "Дипломная работа бакалавра", size=14, color=LIGHT),
        txt(11, emu(0.4), emu(1.2), emu(12), emu(2.2),
            "Система автономного управления\nавтомобилем на основе нейронных сетей",
            size=32, bold=True, color=WHITE),
        txt(12, emu(0.4), emu(3.35), emu(12), emu(0.6),
            "Behavioral Cloning  |  NVIDIA PilotNet CNN  |  YOLOv8",
            size=19, color=ACCENT),
        txt(13, emu(0.4), emu(6.52), emu(12.5), emu(0.5),
            "Студент: Филиппов А.  |  Направление: Информационные технологии  |  2026",
            size=13, color=LIGHT),
    ]
    return slide_xml(s)


def slide_problem():
    s = [stripe(0)] + header(10, "Постановка задачи")
    s += section(20, emu(0.3), emu(1.15), emu(6.1), emu(1.6), "Проблема", [
        "• Традиционные ADAS требуют ручного программирования правил",
        "• Сложно покрыть все дорожные ситуации вручную",
        "• End-to-end обучение позволяет обойти это ограничение",
    ])
    s += section(30, emu(0.3), emu(3.35), emu(6.1), emu(1.6), "Цель работы", [
        "Разработать нейросетевую систему, которая",
        "воспроизводит поведение водителя:",
        "по изображению с камеры предсказывает",
        "угол поворота руля.",
    ])
    s += section(40, emu(6.8), emu(1.15), emu(6.1), emu(2.8), "Задачи", [
        "• Подготовить датасет Udacity (3 камеры)",
        "• Реализовать архитектуру PilotNet CNN",
        "• Обучить модель на записях вождения",
        "• Оценить качество: MSE / MAE / R2",
        "• Интегрировать детекцию объектов YOLOv8",
    ])
    return slide_xml(s)


def slide_math():
    s = [stripe(0)] + header(10, "Математическая модель")
    s += section(20, emu(0.3), emu(1.15), emu(6.1), emu(0.9), "Задача регрессии", [
        "Вход:  x = I  (66x200x3, YUV-кадр)",
        "Выход: y = f(x; theta) in [-1, 1]  (угол руля)",
    ])
    s += section(30, emu(0.3), emu(2.55), emu(6.1), emu(0.4), "Функция потерь (MSE)", [])
    s += box(32, emu(0.3), emu(3.0), emu(6.1), emu(0.75), [
        "L(theta) = (1/N) * sum( (yi - f(xi; theta))^2 )"
    ], size=17, color=ACCENT, align="c")
    s += section(40, emu(0.3), emu(3.95), emu(6.1), emu(1.4), "Оптимизатор Adam", [
        "theta_{t+1} = theta_t - lr * m_t / (sqrt(v_t) + eps)",
        "lr = 1e-3, beta1=0.9, beta2=0.999",
        "ReduceLROnPlateau при plateau val_loss",
    ])
    s += section(50, emu(6.8), emu(1.15), emu(6.1), emu(0.8), "Нормализация входа", [
        "x_norm = (x / 127.5) - 1",
        "Диапазон пикселей [0,255] -> [-1, 1]",
    ])
    s += section(60, emu(6.8), emu(2.6), emu(6.1), emu(2.4), "Аугментация (p = 0.5)", [
        "• Flip: x' = flip(x),  y' = -y",
        "• Яркость: HSV-канал V * U(0.4, 1.2)",
        "• Сдвиг по x: tx in [-50,50] px",
        "    -> y' += tx * 0.004",
        "• Случайная тень (половина кадра)",
    ])
    s += section(70, emu(6.8), emu(5.2), emu(6.1), emu(0.8), "Коррекция боковых камер", [
        "y_left = y_center + 0.25   |   y_right = y_center - 0.25",
    ], label_color=YELLOW, item_color=LIGHT, size=13)
    return slide_xml(s)


def slide_dataset():
    s = [stripe(0)] + header(10, "Данные и предобработка")
    s += section(20, emu(0.3), emu(1.15), emu(5.8), emu(1.7), "Датасет", [
        "• Udacity Self-Driving Car Simulator",
        "• ~24 000 кадров, 3 камеры (left/center/right)",
        "• Метка: угол руля в [-1, 1]",
        "• Формат: CSV + папка с изображениями",
    ])
    s += section(30, emu(0.3), emu(3.5), emu(5.8), emu(1.7), "Предобработка", [
        "• Обрезка неба и капота (ROI)",
        "• Resize -> 66x200 (NVIDIA PilotNet формат)",
        "• BGR -> YUV (устойчивее к освещению)",
        "• Нормализация пикселей -> [-1, 1]",
    ])
    s += section(40, emu(6.8), emu(1.15), emu(6.0), emu(2.3), "Аугментация и балансировка", [
        "• Горизонтальный flip + инверсия угла",
        "• Яркость / сдвиг / тень -- случайно",
        "• Коррекция угла +-0.25 для боковых камер",
        "• Срез пиков нулевого угла (прямая езда)",
        "• Итого: ~3x разнообразнее данных",
    ])
    s += box(50, emu(6.8), emu(4.2), emu(6.0), emu(2.0), [
        "left (-0.25)    center (0)    right (+0.25)",
        "    <------------------------------->"
        "  Коррекция угла для боковых камер",
    ], size=13, align="c")
    return slide_xml(s)


def slide_architecture():
    s = [stripe(0)] + header(10, "Архитектура -- NVIDIA PilotNet")
    s.append(txt(12, emu(0.3), emu(1.1), emu(12), emu(0.35),
                 "Оригинал: NVIDIA (2016) -- End-to-End Learning for Self-Driving Cars",
                 size=12, italic=True, color=LIGHT))

    layers = [
        ("Вход: 66x200x3  (YUV)", ""),
        ("Conv2D 5x5 s=2, 24 фильтра", "BatchNorm + ELU"),
        ("Conv2D 5x5 s=2, 36 фильтров", "BatchNorm + ELU"),
        ("Conv2D 5x5 s=2, 48 фильтров", "BatchNorm + ELU"),
        ("Conv2D 3x3, 64 фильтра", "BatchNorm + ELU"),
        ("Conv2D 3x3, 64 фильтра", "BatchNorm + ELU"),
        ("Flatten -> 1152", ""),
        ("Dropout(0.5) -> FC 100", "ELU"),
        ("Dropout(0.25) -> FC 50", "ELU"),
        ("FC 10 -> ELU -> FC 1", "-> Tanh"),
        ("Выход: угол в [-1, 1]", ""),
    ]
    row_h = emu(0.44)
    for i, (left_txt, right_txt) in enumerate(layers):
        y = emu(1.55) + i * row_h
        is_io = (i == 0 or i == len(layers)-1)
        fill = "007A99" if is_io else DARK
        s.append(rect_shape(100+i, emu(0.3), y, emu(5.5), row_h-pt(1),
                             fill=fill, line_color=ACCENT, line_w=pt(0.5)))
        s.append(txt(200+i, emu(0.45), y+pt(3), emu(3.2), row_h,
                     left_txt, size=12, bold=is_io, color=WHITE))
        if right_txt:
            s.append(txt(300+i, emu(3.8), y+pt(3), emu(2.0), row_h,
                         right_txt, size=11, color=ACCENT))

    s += section(50, emu(6.8), emu(1.15), emu(6.0), emu(2.7), "Ключевые решения", [
        "• BatchNorm -- стабилизирует обучение",
        "• ELU вместо ReLU -- нет мёртвых нейронов",
        "• Dropout 50%/25% -- против переобучения",
        "• Tanh на выходе -> [-1, 1]",
        "• Adam + ReduceLROnPlateau",
        "• EarlyStopping patience=10",
    ])
    s += box(60, emu(6.8), emu(4.6), emu(6.0), emu(1.7), [
        "Optimizer: Adam  |  LR = 1e-3",
        "Loss: MSE  |  Batch = 128",
        "Epochs: до 50  |  ~560 000 параметров",
    ], size=14)
    return slide_xml(s)


def slide_contribution():
    s = [stripe(0)] + header(10, "Вклад автора")

    s += section(20, emu(0.3), emu(1.1), emu(6.0), emu(1.2),
                 "Что взято из литературы", [
        "• Архитектура PilotNet (NVIDIA, 2016)",
        "• Метод Behavioral Cloning",
        "• Датасет: Udacity Simulator Challenge",
    ], label_color=LIGHT, item_color=LIGHT)

    s.append(rect_shape(29, emu(0.3), emu(2.95), emu(12.5), emu(0.04), fill=ACCENT))
    s.append(txt(30, emu(0.3), emu(3.1), emu(12.5), emu(0.45),
                 "Авторские доработки и реализация", size=17, bold=True, color=YELLOW))

    contribs = [
        ("PyTorch-реализация PilotNet с нуля",
         "BatchNorm + ELU + Dropout -- не в оригинале NVIDIA"),
        ("DataLoader с тройной камерой",
         "Угловая коррекция +-0.25, балансировка гистограммы"),
        ("Расширенная аугментация",
         "Яркость, сдвиг, тень, flip -- весь пайплайн собственный"),
        ("Цикл обучения и мониторинг",
         "Adam, EarlyStopping, ReduceLR, чекпоинты"),
        ("Интеграция YOLOv8",
         "Совместный пайплайн: управление + детекция объектов"),
        ("5 Jupyter-ноутбуков для Colab",
         "Автоустановка, воспроизводимость, GPU T4"),
    ]
    for i, (title, detail) in enumerate(contribs):
        y = emu(3.75) + i * emu(0.56)
        s.append(rect_shape(400+i, emu(0.3), y+emu(0.1), emu(0.3), emu(0.3), fill=ACCENT))
        s.append(txt(500+i, emu(0.75), y, emu(6.1), emu(0.35),
                     title, size=14, bold=True, color=WHITE))
        s.append(txt(600+i, emu(0.75), y+emu(0.3), emu(12.2), emu(0.3),
                     "    " + detail, size=12, color=LIGHT))
    return slide_xml(s)


def slide_yolo():
    s = [stripe(0)] + header(10, "Детекция объектов -- YOLOv8")

    s += section(20, emu(0.3), emu(1.15), emu(6.0), emu(1.5), "Зачем", [
        "• PilotNet управляет рулём, но не видит препятствий",
        "• YOLOv8n добавляет распознавание объектов на дороге",
        "• Совместный пайплайн = управление + восприятие сцены",
    ])
    s.append(txt(30, emu(0.3), emu(3.3), emu(6.0), emu(0.45),
                 "Совместный пайплайн", size=17, bold=True, color=YELLOW))
    s += box(31, emu(0.3), emu(3.85), emu(6.0), emu(2.9), [
        "[ Кадр 66x200 YUV ]",
        "",
        "[ PilotNet ]       [ YOLOv8n ]",
        "    угол theta        bbox + label",
        "",
        "[ Визуализация / управление ]",
    ], size=14, align="c")

    s += section(40, emu(6.8), emu(1.15), emu(6.0), emu(2.2), "Модель YOLOv8n", [
        "• Претренирована на COCO (80 классов)",
        "• Inference < 30 мс / кадр на CPU",
        "• Классы: car, truck, person, traffic light...",
        "• Zero-shot на сценах симулятора",
    ])
    s += section(50, emu(6.8), emu(4.0), emu(6.0), emu(1.7), "Результат на кадре", [
        "• Предсказан угол руля",
        "• Отмечены объекты с классами и confidence",
        "• Единый вывод в реальном времени",
    ])
    return slide_xml(s)


def slide_done():
    s = [stripe(0)] + header(10, "Что выполнено")

    done = [
        "Архитектура PilotNet реализована на PyTorch",
        "DataLoader: 3 камеры, аугментация, балансировка",
        "Цикл обучения: Adam, MSE loss, EarlyStopping",
        "Оценка: MSE / MAE / R2, визуализация ошибок",
        "YOLOv8 детекция + объединённый пайплайн",
        "5 Jupyter-ноутбуков для Google Colab (GPU T4)",
        "Автоматическая установка (00_install.ipynb)",
        "Совместимость с PyTorch 2.6+, публикация на GitHub",
    ]
    for i, item in enumerate(done):
        y = emu(1.15) + i * emu(0.68)
        s.append(rect_shape(100+i, emu(0.3), y+emu(0.1), emu(0.3), emu(0.3), fill=ACCENT))
        s.append(txt(200+i, emu(0.77), y, emu(12.2), emu(0.55),
                     item, size=17, color=WHITE))
    return slide_xml(s)


def slide_results():
    s = [stripe(0)] + header(10, "Ожидаемые результаты")

    metrics = [
        ("MSE", "< 0.01",  "Средняя квадр. ошибка"),
        ("MAE", "< 0.07",  "Средняя абс. ошибка"),
        ("R2",  "> 0.85",  "Коэффициент детерминации"),
    ]
    for i, (name, val, desc) in enumerate(metrics):
        x = emu(0.3 + i * 4.2)
        s.append(rect_shape(100+i, x, emu(1.2), emu(3.9), emu(2.0),
                             fill=DARK, line_color=ACCENT, line_w=pt(1.5)))
        s.append(txt(200+i, x+emu(0.1), emu(1.3), emu(3.7), emu(0.45),
                     name, size=18, bold=True, color=ACCENT, align="c"))
        s.append(txt(300+i, x+emu(0.1), emu(1.77), emu(3.7), emu(0.65),
                     val, size=28, bold=True, color=YELLOW, align="c"))
        s.append(txt(400+i, x+emu(0.1), emu(2.48), emu(3.7), emu(0.5),
                     desc, size=12, color=LIGHT, align="c"))

    s += section(50, emu(0.3), emu(3.4), emu(6.0), emu(1.5), "Визуализации", [
        "• Кривые train / val loss по эпохам",
        "• Scatter: предсказания vs. истинные углы",
        "• Гистограмма остатков",
    ])
    s += section(60, emu(6.8), emu(3.4), emu(6.0), emu(1.5), "Среда и время", [
        "• Google Colab, GPU NVIDIA T4",
        "• Python 3.10, PyTorch 2.6, Ultralytics YOLOv8",
        "• Время обучения: ~20-40 мин",
    ])
    return slide_xml(s)


def slide_plan():
    s = [stripe(0)] + header(10, "Дальнейшие шаги")

    s.append(txt(20, emu(0.3), emu(1.15), emu(12), emu(0.4),
                 "Ближайшие", size=17, bold=True, color=YELLOW))
    near = [
        ("Запустить обучение в Colab",          "->  получить итоговые метрики"),
        ("Загрузить датасет на Google Drive",    "->  проверить end-to-end пайплайн"),
        ("Сформировать графики и таблицы",       "->  для главы Результаты"),
    ]
    for i, (task, note) in enumerate(near):
        y = emu(1.65) + i * emu(0.85)
        s.append(rect_shape(100+i, emu(0.3), y+emu(0.12), pt(7), pt(7), fill=ACCENT))
        s.append(txt(200+i, emu(0.6), y, emu(6.3), emu(0.5),
                     task, size=16, bold=True, color=WHITE))
        s.append(txt(300+i, emu(7.0), y, emu(6.0), emu(0.5),
                     note, size=15, color=LIGHT))

    s.append(rect_shape(40, emu(0.3), emu(4.3), emu(12.5), emu(0.04), fill=ACCENT))
    s += section(41, emu(0.3), emu(4.45), emu(12.5), emu(1.9), "Перспективы", [
        "• LSTM / GRU -- учёт истории кадров для сглаживания управления",
        "• Дообучение YOLOv8 на сценах симулятора",
        "• Демо-видео: реальный прогон в Udacity Simulator",
        "• Написание глав диплома (архитектура, результаты, выводы)",
    ])
    return slide_xml(s)


def slide_final():
    s = [stripe(0)]
    s.append(txt(10, emu(0.3), emu(0.4), W-emu(0.3), emu(0.7),
                 "Итог", size=32, bold=True, color=ACCENT, align="c"))

    bullets = [
        "Реализована end-to-end система Behavioral Cloning на PyTorch",
        "Архитектура: NVIDIA PilotNet CNN (BatchNorm + ELU + Dropout)",
        "Данные: Udacity Simulator, 3 камеры, аугментация, балансировка",
        "Мат. модель: MSE-регрессия, Adam, нормализация YUV-входа",
        "Авторский вклад: полная реализация + YOLOv8 интеграция",
        "Вся система воспроизводима в Colab за один запуск",
    ]
    for i, b in enumerate(bullets):
        y = emu(1.3) + i * emu(0.68)
        s.append(rect_shape(100+i, emu(1.3), y+emu(0.18), pt(9), pt(9), fill=ACCENT))
        s.append(txt(200+i, emu(1.7), y, emu(11.0), emu(0.6),
                     b, size=18, color=WHITE))

    s.append(rect_shape(50, emu(1.5), emu(5.5), emu(10), emu(1.2),
                        fill=BLUE2, line_color=ACCENT, line_w=pt(1.5)))
    s.append(txt(51, emu(1.7), emu(5.6), emu(9.6), emu(1.0),
                 "Спасибо за внимание!\nГотов ответить на вопросы.",
                 size=22, bold=True, color=WHITE, align="c"))
    return slide_xml(s)


# ─── Статические XML-файлы ────────────────────────────────────────────────────

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml"  ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
{slide_overrides}
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

THEME = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Diploma">
  <a:themeElements>
    <a:clrScheme name="Diploma">
      <a:dk1><a:sysClr lastClr="000000" val="windowText"/></a:dk1>
      <a:lt1><a:sysClr lastClr="ffffff" val="window"/></a:lt1>
      <a:dk2><a:srgbClr val="0D1B2A"/></a:dk2>
      <a:lt2><a:srgbClr val="B0C4DE"/></a:lt2>
      <a:accent1><a:srgbClr val="00B4D8"/></a:accent1>
      <a:accent2><a:srgbClr val="FFD166"/></a:accent2>
      <a:accent3><a:srgbClr val="4BACC6"/></a:accent3>
      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
      <a:accent5><a:srgbClr val="4F81BD"/></a:accent5>
      <a:accent6><a:srgbClr val="00B050"/></a:accent6>
      <a:hlink><a:srgbClr val="0563C1"/></a:hlink>
      <a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Diploma">
      <a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Diploma">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="30000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="30000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
        <a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
        <a:effectStyle><a:effectLst/></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>"""

SLIDE_MASTER = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/><a:chOff x="0" y="0"/><a:chExt cx="12192000" cy="6858000"/></a:xfrm></p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles>
    <p:titleStyle><a:lvl1pPr><a:defRPr lang="ru-RU" sz="2800" b="1"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:titleStyle>
    <p:bodyStyle><a:lvl1pPr><a:defRPr lang="ru-RU" sz="1800"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:bodyStyle>
    <p:otherStyle><a:lvl1pPr><a:defRPr lang="ru-RU"><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:otherStyle>
  </p:txStyles>
</p:sldMaster>"""

SLIDE_MASTER_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""

SLIDE_LAYOUT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             type="blank" preserve="1">
  <p:cSld name="Blank">
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/><a:chOff x="0" y="0"/><a:chExt cx="12192000" cy="6858000"/></a:xfrm></p:grpSpPr>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""

SLIDE_LAYOUT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""

CORE_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <dc:title>Avtonomnoe upravlenie avtomobilem</dc:title>
  <dc:creator>Filippov A.</dc:creator>
</cp:coreProperties>"""

APP_XML_TPL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Python PPTX Generator</Application>
  <Slides>{n}</Slides>
</Properties>"""


def presentation_xml(n):
    slide_ids = "".join(
        f'<p:sldId id="{256+i}" r:id="rId{i+2}"/>' for i in range(n)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f'<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
        f'<p:sldIdLst>{slide_ids}</p:sldIdLst>'
        f'<p:sldSz cx="{W}" cy="{H}"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        '</p:presentation>'
    )


def presentation_rels(n):
    rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>']
    for i in range(n):
        rels.append(
            f'<Relationship Id="rId{i+2}" '
            f'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
            f'Target="slides/slide{i+1}.xml"/>'
        )
    rels.append('</Relationships>')
    return "\n".join(rels)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    slides = [
        slide_title(),
        slide_problem(),
        slide_math(),
        slide_dataset(),
        slide_architecture(),
        slide_contribution(),
        slide_yolo(),
        slide_done(),
        slide_results(),
        slide_plan(),
        slide_final(),
    ]
    n = len(slides)

    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{i+1}.xml" '
        f'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(n)
    )

    out = "presentation.pptx"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        def w(name, content):
            if isinstance(content, str):
                content = content.encode("utf-8")
            z.writestr(name, content)

        w("[Content_Types].xml", CONTENT_TYPES.format(slide_overrides=slide_overrides))
        w("_rels/.rels", ROOT_RELS)
        w("ppt/presentation.xml", presentation_xml(n))
        w("ppt/_rels/presentation.xml.rels", presentation_rels(n))
        w("ppt/theme/theme1.xml", THEME)
        w("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
        w("ppt/slideMasters/_rels/slideMaster1.xml.rels", SLIDE_MASTER_RELS)
        w("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
        w("ppt/slideLayouts/_rels/slideLayout1.xml.rels", SLIDE_LAYOUT_RELS)
        w("docProps/core.xml", CORE_XML)
        w("docProps/app.xml", APP_XML_TPL.format(n=n))
        for i, xml in enumerate(slides):
            w(f"ppt/slides/slide{i+1}.xml", xml)
            w(f"ppt/slides/_rels/slide{i+1}.xml.rels", slide_rels())

    print(f"Saved: {out}  ({n} slides)")


if __name__ == "__main__":
    main()
