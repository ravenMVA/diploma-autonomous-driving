"""
Генерация PPTX-презентации по дипломному проекту.
Зависимости: только стандартная библиотека Python.
"""
import zipfile, io, textwrap
from xml.etree.ElementTree import Element, SubElement, tostring
from datetime import datetime

# ─── Константы ────────────────────────────────────────────────────────────────
W  = 12192000   # 13.33" × 914400
H  =  6858000   # 7.5"   × 914400
EMU = 914400    # 1 inch

BG      = "0D1B2A"
ACCENT  = "00B4D8"
WHITE   = "FFFFFF"
LIGHT   = "B0C4DE"
YELLOW  = "FFD166"
DARK    = "060F1A"
BLUE2   = "004A6B"


def emu(inches): return int(inches * EMU)
def pt(n):       return int(n * 12700)   # 1 pt = 12700 EMU


# ─── XML helpers ──────────────────────────────────────────────────────────────
NS = {
    "a":   "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p":   "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r":   "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "dc":  "http://purl.org/dc/elements/1.1/",
    "cp":  "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "ep":  "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
}

def tag(prefix, name): return f"{{{NS[prefix]}}}{name}"


def xml_bytes(root):
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + tostring(root, encoding="unicode").encode()


# ─── Slide builder ────────────────────────────────────────────────────────────

class Slide:
    def __init__(self):
        self.shapes = []   # list of (xml_element,)

    def _spTree(self):
        spTree = Element(tag("p","spTree"))
        nvGrpSpPr = SubElement(spTree, tag("p","nvGrpSpPr"))
        cNvPr = SubElement(nvGrpSpPr, tag("p","cNvPr")); cNvPr.set("id","1"); cNvPr.set("name","")
        SubElement(nvGrpSpPr, tag("p","cNvGrpSpPr"))
        SubElement(nvGrpSpPr, tag("p","nvPr"))
        grpSpPr = SubElement(spTree, tag("p","grpSpPr"))
        xfrm = SubElement(grpSpPr, tag("a","xfrm"))
        for sub,v in [("off","0,0"),("ext",f"{W},{H}"),("chOff","0,0"),("chExt",f"{W},{H}")]:
            e = SubElement(xfrm, tag("a",sub))
            if "," in v:
                x,y = v.split(","); e.set("x",x); e.set("y",y) if sub in ("off","chOff") else e.set("cx",x) or e.set("cy",y)
        for sh in self.shapes:
            spTree.append(sh)
        return spTree

    def add_rect(self, left, top, width, height, fill=None, line=None, line_w=pt(0.5), idx=100):
        sp = Element(tag("p","sp"))
        nvSpPr = SubElement(sp, tag("p","nvSpPr"))
        cNvPr = SubElement(nvSpPr, tag("p","cNvPr")); cNvPr.set("id", str(idx)); cNvPr.set("name", f"rect{idx}")
        cNvSpPr = SubElement(nvSpPr, tag("p","cNvSpPr")); cNvSpPr.set("txBox","1")
        SubElement(nvSpPr, tag("p","nvPr"))
        spPr = SubElement(sp, tag("p","spPr"))
        xfrm = SubElement(spPr, tag("a","xfrm"))
        off = SubElement(xfrm, tag("a","off")); off.set("x",str(left)); off.set("y",str(top))
        ext = SubElement(xfrm, tag("a","ext")); ext.set("cx",str(width)); ext.set("cy",str(height))
        prstGeom = SubElement(spPr, tag("a","prstGeom")); prstGeom.set("prst","rect")
        SubElement(prstGeom, tag("a","avLst"))
        if fill:
            solidFill = SubElement(spPr, tag("a","solidFill"))
            srgb = SubElement(solidFill, tag("a","srgbClr")); srgb.set("val", fill)
        else:
            SubElement(spPr, tag("a","noFill"))
        if line:
            ln = SubElement(spPr, tag("a","ln")); ln.set("w", str(line_w))
            sf = SubElement(ln, tag("a","solidFill"))
            sc = SubElement(sf, tag("a","srgbClr")); sc.set("val", line)
        else:
            SubElement(spPr, tag("a","ln"))
        # empty txBody
        txBody = SubElement(sp, tag("p","txBody"))
        SubElement(txBody, tag("a","bodyPr"))
        SubElement(txBody, tag("a","lstStyle"))
        SubElement(txBody, tag("a","p"))
        self.shapes.append(sp)

    def add_text(self, text, left, top, width, height,
                 size=18, bold=False, color=WHITE, align="l",
                 wrap=True, idx=200, italic=False):
        """Добавляет текстовый блок. text может содержать \n для переносов."""
        sp = Element(tag("p","sp"))
        nvSpPr = SubElement(sp, tag("p","nvSpPr"))
        cNvPr = SubElement(nvSpPr, tag("p","cNvPr")); cNvPr.set("id", str(idx)); cNvPr.set("name", f"txt{idx}")
        cNvSpPr = SubElement(nvSpPr, tag("p","cNvSpPr")); cNvSpPr.set("txBox","1")
        SubElement(nvSpPr, tag("p","nvPr"))
        spPr = SubElement(sp, tag("p","spPr"))
        xfrm = SubElement(spPr, tag("a","xfrm"))
        off = SubElement(xfrm, tag("a","off")); off.set("x",str(left)); off.set("y",str(top))
        ext = SubElement(xfrm, tag("a","ext")); ext.set("cx",str(width)); ext.set("cy",str(height))
        prstGeom = SubElement(spPr, tag("a","prstGeom")); prstGeom.set("prst","rect")
        SubElement(prstGeom, tag("a","avLst"))
        SubElement(spPr, tag("a","noFill"))
        ln_el = SubElement(spPr, tag("a","ln"))
        SubElement(ln_el, tag("a","noFill"))

        txBody = SubElement(sp, tag("p","txBody"))
        bodyPr = SubElement(txBody, tag("a","bodyPr"))
        bodyPr.set("wrap", "square" if wrap else "none")
        bodyPr.set("rtlCol", "0")
        SubElement(txBody, tag("a","lstStyle"))

        algn_map = {"l":"l","c":"ctr","r":"r","j":"just"}
        algn = algn_map.get(align,"l")

        lines = text.split("\n")
        for line in lines:
            p = SubElement(txBody, tag("a","p"))
            pPr = SubElement(p, tag("a","pPr")); pPr.set("algn", algn)
            if line.strip() == "":
                SubElement(p, tag("a","endParaRPr")).set("lang","ru-RU")
                continue
            r = SubElement(p, tag("a","r"))
            rPr = SubElement(r, tag("a","rPr"))
            rPr.set("lang","ru-RU"); rPr.set("sz", str(size*100))
            rPr.set("b", "1" if bold else "0")
            rPr.set("i", "1" if italic else "0")
            rPr.set("dirty","0")
            solidFill = SubElement(rPr, tag("a","solidFill"))
            srgb = SubElement(solidFill, tag("a","srgbClr")); srgb.set("val", color)
            SubElement(rPr, tag("a","latin")).set("typeface","Calibri")
            t = SubElement(r, tag("a","t")); t.text = line

        self.shapes.append(sp)

    def build_xml(self, slide_idx, layout_rId="rId1", master_rId="rId2"):
        sld = Element(tag("p","sld"))
        sld.set("xmlns:a", NS["a"])
        sld.set("xmlns:p", NS["p"])
        sld.set("xmlns:r", NS["r"])

        cSld = SubElement(sld, tag("p","cSld"))
        # Background
        bg = SubElement(cSld, tag("p","bg"))
        bgPr = SubElement(bg, tag("p","bgPr"))
        solidFill = SubElement(bgPr, tag("a","solidFill"))
        srgb = SubElement(solidFill, tag("a","srgbClr")); srgb.set("val", BG)
        SubElement(bgPr, tag("a","effectLst"))

        cSld.append(self._spTree())
        SubElement(sld, tag("p","clrMapOvr"))
        SubElement(sld.find(tag("p","clrMapOvr")), tag("a","masterClrMapping"))

        return xml_bytes(sld)

    def build_rels(self, layout_id=1):
        Relationships = Element("Relationships")
        Relationships.set("xmlns","http://schemas.openxmlformats.org/package/2006/relationships")
        rel = SubElement(Relationships, "Relationship")
        rel.set("Id","rId1")
        rel.set("Type","http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout")
        rel.set("Target",f"../slideLayouts/slideLayout{layout_id}.xml")
        return xml_bytes(Relationships)


# ─── SLIDE FACTORIES ──────────────────────────────────────────────────────────

def _stripe(sl, idx=10):
    """Вертикальная акцентная полоса слева"""
    sl.add_rect(0, 0, emu(0.12), H, fill=ACCENT, idx=idx)


def make_slide_title():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_rect(0, emu(6.4), W, emu(1.1), fill=DARK, idx=11)

    sl.add_text("Дипломная работа бакалавра",
                emu(0.4), emu(0.35), emu(12), emu(0.5),
                size=14, color=LIGHT, idx=20)

    sl.add_text("Система автономного управления\nавтомобилем на основе нейронных сетей",
                emu(0.4), emu(1.2), emu(12), emu(2.2),
                size=32, bold=True, color=WHITE, idx=21)

    sl.add_text("Behavioral Cloning  ·  NVIDIA PilotNet CNN  ·  YOLOv8",
                emu(0.4), emu(3.35), emu(12), emu(0.6),
                size=20, color=ACCENT, idx=22)

    sl.add_text("Студент: Филиппов А.  ·  Направление: Информационные технологии  ·  2026",
                emu(0.4), emu(6.52), emu(12.5), emu(0.5),
                size=13, color=LIGHT, idx=30)
    return sl


def make_slide_problem():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Постановка задачи", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    sl.add_text("Проблема", emu(0.3), emu(1.15), emu(6), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=30)
    sl.add_text(
        "•  Традиционные ADAS требуют ручного программирования правил\n"
        "•  Сложно покрыть все дорожные ситуации вручную\n"
        "•  End-to-end обучение позволяет обойти это ограничение",
        emu(0.3), emu(1.62), emu(6.1), emu(1.6),
        size=15, color=WHITE, idx=31)

    sl.add_text("Цель работы", emu(0.3), emu(3.35), emu(6), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=32)
    sl.add_text(
        "Разработать и обучить нейросетевую систему,\n"
        "которая воспроизводит поведение водителя:\n"
        "по изображению с камеры предсказывает угол поворота руля.",
        emu(0.3), emu(3.85), emu(5.8), emu(1.6),
        size=15, color=WHITE, idx=33)

    sl.add_text("Задачи", emu(6.8), emu(1.15), emu(6), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=40)
    sl.add_text(
        "•  Подготовить датасет Udacity (3 камеры)\n"
        "•  Реализовать архитектуру PilotNet CNN\n"
        "•  Обучить модель на записях вождения\n"
        "•  Оценить качество: MSE / MAE / R²\n"
        "•  Интегрировать детекцию объектов YOLOv8",
        emu(6.8), emu(1.62), emu(6.1), emu(2.5),
        size=15, color=WHITE, idx=41)
    return sl


def make_slide_math():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Математическая модель", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    # Левая колонка — формулы
    sl.add_text("Задача регрессии", emu(0.3), emu(1.15), emu(6.1), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=30)
    sl.add_text(
        "Вход:  x = I ∈ R^(66×200×3)  (кадр YUV)\n"
        "Выход: ŷ = f(x; θ) ∈ [−1, 1]  (угол руля)",
        emu(0.3), emu(1.65), emu(6.1), emu(0.9),
        size=15, color=WHITE, idx=31)

    sl.add_text("Функция потерь (MSE)", emu(0.3), emu(2.65), emu(6.1), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=32)
    sl.add_rect(emu(0.3), emu(3.1), emu(6.1), emu(0.8), fill=DARK, line=ACCENT, line_w=pt(1), idx=33)
    sl.add_text(
        "L(θ) = (1/N) Σ (yᵢ − f(xᵢ; θ))²",
        emu(0.5), emu(3.2), emu(5.7), emu(0.7),
        size=17, bold=True, color=ACCENT, align="c", idx=34)

    sl.add_text("Оптимизация (Adam)", emu(0.3), emu(4.1), emu(6.1), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=35)
    sl.add_text(
        "θ_{t+1} = θ_t − α · m̂_t / (√v̂_t + ε)\n"
        "α = 1e-3, β₁ = 0.9, β₂ = 0.999\n"
        "ReduceLROnPlateau при plateau val_loss",
        emu(0.3), emu(4.6), emu(6.1), emu(1.5),
        size=14, color=WHITE, idx=36)

    # Правая колонка
    sl.add_text("Нормализация входа", emu(6.8), emu(1.15), emu(6.1), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=40)
    sl.add_text(
        "x_norm = (x / 127.5) − 1\n"
        "Диапазон пикселей [0,255] → [−1, 1]",
        emu(6.8), emu(1.65), emu(6.1), emu(0.9),
        size=14, color=WHITE, idx=41)

    sl.add_text("Аугментация (вероятность 0.5)", emu(6.8), emu(2.7), emu(6.1), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=42)
    sl.add_text(
        "•  Flip: x' = flip(x), y' = −y\n"
        "•  Яркость: HSV-канал V × U(0.4, 1.2)\n"
        "•  Сдвиг по x: случайный tx ∈ [−50,50] px\n"
        "     → коррекция угла: y' += tx × 0.004\n"
        "•  Случайная тень: половина кадра темнее",
        emu(6.8), emu(3.2), emu(6.1), emu(2.2),
        size=14, color=WHITE, idx=43)

    sl.add_text("Коррекция боковых камер", emu(6.8), emu(5.5), emu(6.1), emu(0.4),
                size=15, bold=True, color=YELLOW, idx=44)
    sl.add_text(
        "y_left = y_center + 0.25    y_right = y_center − 0.25",
        emu(6.8), emu(5.95), emu(6.1), emu(0.5),
        size=13, color=LIGHT, idx=45)
    return sl


def make_slide_dataset():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Данные и предобработка", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    sl.add_text("Датасет", emu(0.3), emu(1.15), emu(5.8), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=30)
    sl.add_text(
        "•  Udacity Self-Driving Car Simulator\n"
        "•  ~24 000 кадров, 3 камеры (left/center/right)\n"
        "•  Метка: угол руля ∈ [−1, 1]\n"
        "•  Формат: CSV + папка с изображениями",
        emu(0.3), emu(1.62), emu(5.8), emu(1.7),
        size=15, color=WHITE, idx=31)

    sl.add_text("Предобработка", emu(0.3), emu(3.5), emu(5.8), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=32)
    sl.add_text(
        "•  Обрезка неба и капота → ROI\n"
        "•  Resize → 66×200 (NVIDIA PilotNet формат)\n"
        "•  BGR → YUV (устойчивее к освещению)\n"
        "•  Нормализация пикселей → [−1, 1]",
        emu(0.3), emu(4.0), emu(5.8), emu(1.7),
        size=15, color=WHITE, idx=33)

    sl.add_text("Аугментация и балансировка", emu(6.8), emu(1.15), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=40)
    sl.add_text(
        "•  Горизонтальный flip + инверсия угла\n"
        "•  Яркость / сдвиг / тень — случайно\n"
        "•  Коррекция угла ±0.25 для боковых камер\n"
        "•  Срез пиков нулевого угла (прямая езда)\n"
        "•  Итого: ~3× разнообразнее",
        emu(6.8), emu(1.62), emu(6), emu(2.3),
        size=15, color=WHITE, idx=41)

    sl.add_rect(emu(6.8), emu(4.2), emu(6), emu(2.1), fill=DARK, line=ACCENT, line_w=pt(1), idx=50)
    sl.add_text(
        "left (−0.25)     center (0)     right (+0.25)\n"
        "       ←──────────────────────→\n"
        "  Угол корректируется для боковых камер",
        emu(7.0), emu(4.35), emu(5.6), emu(1.8),
        size=13, color=LIGHT, align="c", idx=51)
    return sl


def make_slide_architecture():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Архитектура — NVIDIA PilotNet", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)
    sl.add_text("Оригинал: NVIDIA (2016) · End-to-End Learning for Self-Driving Cars",
                emu(0.3), emu(1.1), emu(12), emu(0.35),
                size=12, color=LIGHT, italic=True, idx=22)

    layers = [
        ("Вход: 66×200×3 (YUV)", ""),
        ("Conv2D 5×5 s=2 → 24", "BatchNorm + ELU"),
        ("Conv2D 5×5 s=2 → 36", "BatchNorm + ELU"),
        ("Conv2D 5×5 s=2 → 48", "BatchNorm + ELU"),
        ("Conv2D 3×3 → 64",     "BatchNorm + ELU"),
        ("Conv2D 3×3 → 64",     "BatchNorm + ELU"),
        ("Flatten → 1152",      ""),
        ("Dropout(0.5) → FC 100","ELU"),
        ("Dropout(0.25) → FC 50","ELU"),
        ("FC 10 → ELU → FC 1",  "→ Tanh"),
        ("Выход: угол ∈ [−1,1]",""),
    ]
    row_h = emu(0.44)
    for i, (left_txt, right_txt) in enumerate(layers):
        y = emu(1.55) + i * row_h
        is_io = i == 0 or i == len(layers)-1
        fill = "007A99" if is_io else DARK
        sl.add_rect(emu(0.3), y, emu(5.5), row_h - pt(1),
                    fill=fill, line=ACCENT, line_w=pt(0.5), idx=100+i)
        sl.add_text(left_txt,
                    emu(0.45), y+pt(3), emu(3.2), row_h,
                    size=12, color=WHITE, bold=is_io, idx=200+i)
        if right_txt:
            sl.add_text(right_txt,
                        emu(3.8), y+pt(3), emu(2), row_h,
                        size=11, color=ACCENT, idx=300+i)

    sl.add_text("Ключевые решения", emu(6.8), emu(1.15), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=50)
    sl.add_text(
        "•  BatchNorm — стабилизирует обучение\n"
        "•  ELU вместо ReLU — нет «мёртвых» нейронов\n"
        "•  Dropout 50% / 25% — против переобучения\n"
        "•  Tanh на выходе → [−1, 1]\n"
        "•  Adam + ReduceLROnPlateau\n"
        "•  EarlyStopping patience=10",
        emu(6.8), emu(1.62), emu(6), emu(2.7),
        size=15, color=WHITE, idx=51)

    sl.add_rect(emu(6.8), emu(4.6), emu(6), emu(1.7), fill=DARK, line=ACCENT, line_w=pt(1), idx=60)
    sl.add_text(
        "Параметры обучения\n"
        "Optimizer: Adam  |  LR = 1×10⁻³\n"
        "Loss: MSE  |  Batch = 128\n"
        "Epochs: до 50  |  ~560 000 параметров",
        emu(7.0), emu(4.75), emu(5.6), emu(1.4),
        size=14, color=LIGHT, idx=61)
    return sl


def make_slide_contribution():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Вклад автора", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    sl.add_text("Что взято из литературы", emu(0.3), emu(1.1), emu(5.8), emu(0.45),
                size=16, bold=True, color=LIGHT, idx=30)
    sl.add_text(
        "•  Архитектура PilotNet (NVIDIA, 2016)\n"
        "•  Метод Behavioral Cloning\n"
        "•  Датасет: Udacity Simulator Challenge",
        emu(0.3), emu(1.6), emu(5.8), emu(1.4),
        size=15, color=LIGHT, idx=31)

    sl.add_rect(emu(0.3), emu(3.05), emu(5.8), emu(0.04), fill=ACCENT, idx=32)
    sl.add_text("Авторские доработки и реализация", emu(0.3), emu(3.2), emu(12.5), emu(0.45),
                size=17, bold=True, color=YELLOW, idx=33)

    contributions = [
        ("PyTorch-реализация PilotNet с нуля",
         "BatchNorm + ELU + Dropout — не в оригинале"),
        ("DataLoader с тройной камерой",
         "Угловая коррекция ±0.25, балансировка гистограммы"),
        ("Расширенная аугментация",
         "Яркость, сдвиг, тень, flip — весь пайплайн собственный"),
        ("Цикл обучения и мониторинг",
         "Adam, EarlyStopping, ReduceLR, чекпоинты"),
        ("Интеграция YOLOv8",
         "Совместный пайплайн: управление + детекция объектов"),
        ("5 Jupyter-ноутбуков для Colab",
         "Автоустановка, воспроизводимость, GPU T4"),
    ]
    for i, (title, detail) in enumerate(contributions):
        y = emu(3.75) + i * emu(0.56)
        sl.add_rect(emu(0.3), y+pt(2), pt(7), pt(7), fill=ACCENT, idx=400+i)
        sl.add_text(title,
                    emu(0.6), y, emu(6.3), emu(0.35),
                    size=14, bold=True, color=WHITE, idx=500+i)
        sl.add_text(f"    {detail}",
                    emu(0.6), y+emu(0.28), emu(12.3), emu(0.3),
                    size=12, color=LIGHT, idx=600+i)
    return sl


def make_slide_yolo():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Детекция объектов — YOLOv8", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    sl.add_text("Зачем", emu(0.3), emu(1.15), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=30)
    sl.add_text(
        "•  PilotNet управляет рулём, но «не видит» препятствий\n"
        "•  YOLOv8n добавляет распознавание объектов на дороге\n"
        "•  Совместный пайплайн = управление + восприятие сцены",
        emu(0.3), emu(1.62), emu(6), emu(1.5),
        size=15, color=WHITE, idx=31)

    sl.add_text("Совместный пайплайн", emu(0.3), emu(3.3), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=32)
    sl.add_rect(emu(0.3), emu(3.8), emu(6), emu(2.9), fill=DARK, line=ACCENT, line_w=pt(1), idx=33)
    sl.add_text(
        "[ Кадр 66×200 YUV ]\n"
        "\n"
        "[ PilotNet ]        [ YOLOv8n ]\n"
        "    угол θ           bbox + label\n"
        "\n"
        "[ Визуализация / управление ]",
        emu(0.5), emu(3.95), emu(5.6), emu(2.5),
        size=14, color=LIGHT, align="c", idx=34)

    sl.add_text("Модель YOLOv8n", emu(6.8), emu(1.15), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=40)
    sl.add_text(
        "•  Претренирована на COCO (80 классов)\n"
        "•  Inference < 30 мс / кадр на CPU\n"
        "•  Классы: car, truck, person, traffic light…\n"
        "•  Zero-shot на сценах симулятора\n"
        "•  Без дообучения",
        emu(6.8), emu(1.62), emu(6), emu(2.2),
        size=15, color=WHITE, idx=41)

    sl.add_text("Итоговый результат", emu(6.8), emu(4.0), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=42)
    sl.add_rect(emu(6.8), emu(4.5), emu(6), emu(2), fill=DARK, line=ACCENT, line_w=pt(1), idx=43)
    sl.add_text(
        "На каждом кадре:\n"
        "  → предсказан угол руля\n"
        "  → отмечены объекты с классами\n"
        "  → единый вывод в реальном времени",
        emu(7.0), emu(4.65), emu(5.6), emu(1.7),
        size=14, color=LIGHT, idx=44)
    return sl


def make_slide_done():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Что выполнено", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    done = [
        "Архитектура PilotNet реализована на PyTorch",
        "DataLoader: 3 камеры, аугментация, балансировка",
        "Цикл обучения: Adam, MSE loss, EarlyStopping",
        "Оценка: MSE / MAE / R², визуализация ошибок",
        "YOLOv8 детекция + объединённый пайплайн",
        "5 Jupyter-ноутбуков для Google Colab (GPU T4)",
        "Автоматическая установка (00_install.ipynb)",
        "Совместимость с PyTorch 2.6+, публикация на GitHub",
    ]
    for i, item in enumerate(done):
        y = emu(1.15) + i * emu(0.68)
        sl.add_rect(emu(0.3), y + emu(0.1), emu(0.32), emu(0.32), fill=ACCENT, idx=100+i)
        sl.add_text("✓", emu(0.3), y + emu(0.06), emu(0.35), emu(0.38),
                    size=13, bold=True, color=BG, align="c", idx=200+i)
        sl.add_text(item,
                    emu(0.8), y, emu(12.2), emu(0.55),
                    size=17, color=WHITE, idx=300+i)
    return sl


def make_slide_results():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Ожидаемые результаты", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    metrics = [
        ("MSE", "< 0.01",  "Средняя квадр.\nошибка угла"),
        ("MAE", "< 0.07",  "Средняя абс.\nошибка"),
        ("R²",  "> 0.85",  "Коэффициент\nдетерминации"),
    ]
    for i, (name, val, desc) in enumerate(metrics):
        x = emu(0.3 + i * 4.2)
        sl.add_rect(x, emu(1.2), emu(3.9), emu(2.0),
                    fill=DARK, line=ACCENT, line_w=pt(1.5), idx=100+i)
        sl.add_text(name, x+emu(0.1), emu(1.3), emu(3.7), emu(0.45),
                    size=18, bold=True, color=ACCENT, align="c", idx=200+i)
        sl.add_text(val, x+emu(0.1), emu(1.75), emu(3.7), emu(0.65),
                    size=30, bold=True, color=YELLOW, align="c", idx=300+i)
        sl.add_text(desc, x+emu(0.1), emu(2.45), emu(3.7), emu(0.55),
                    size=12, color=LIGHT, align="c", idx=400+i)

    sl.add_text("Визуализации", emu(0.3), emu(3.4), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=50)
    sl.add_text(
        "•  Кривые train / val loss по эпохам\n"
        "•  Scatter: предсказания vs. истинные углы\n"
        "•  Гистограмма остатков (распределение ошибок)",
        emu(0.3), emu(3.9), emu(6), emu(1.5),
        size=15, color=WHITE, idx=51)

    sl.add_text("Среда и время обучения", emu(6.8), emu(3.4), emu(6), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=52)
    sl.add_text(
        "•  Google Colab, GPU NVIDIA T4\n"
        "•  Python 3.10, PyTorch 2.6, Ultralytics YOLOv8\n"
        "•  Время обучения: ~20–40 мин",
        emu(6.8), emu(3.9), emu(6), emu(1.5),
        size=15, color=WHITE, idx=53)
    return sl


def make_slide_plan():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Дальнейшие шаги", emu(0.3), emu(0.2), emu(12), emu(0.7),
                size=28, bold=True, color=ACCENT, idx=20)
    sl.add_rect(emu(0.3), emu(0.95), emu(5), emu(0.04), fill=ACCENT, idx=21)

    sl.add_text("Ближайшие", emu(0.3), emu(1.15), emu(12), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=30)
    near = [
        ("Запустить обучение в Colab",         "→ получить итоговые метрики"),
        ("Загрузить датасет на Google Drive",   "→ проверить end-to-end пайплайн"),
        ("Сформировать графики и таблицы",      "→ для главы «Результаты»"),
    ]
    for i, (task, note) in enumerate(near):
        y = emu(1.65) + i * emu(0.85)
        sl.add_rect(emu(0.3), y+emu(0.12), pt(7), pt(7), fill=ACCENT, idx=100+i)
        sl.add_text(task,  emu(0.6), y, emu(6.3), emu(0.5),
                    size=16, bold=True, color=WHITE, idx=200+i)
        sl.add_text(note, emu(7.0), y, emu(6), emu(0.5),
                    size=15, color=LIGHT, idx=300+i)

    sl.add_rect(emu(0.3), emu(4.3), emu(12.5), emu(0.04), fill=ACCENT, idx=40)
    sl.add_text("Перспективы", emu(0.3), emu(4.45), emu(12), emu(0.4),
                size=17, bold=True, color=YELLOW, idx=41)
    sl.add_text(
        "•  LSTM / GRU — учёт истории кадров для сглаживания управления\n"
        "•  Дообучение YOLOv8 на сценах симулятора\n"
        "•  Демо-видео: реальный прогон в Udacity Simulator\n"
        "•  Написание глав диплома (архитектура, результаты, выводы)",
        emu(0.3), emu(4.95), emu(12.5), emu(2.0),
        size=16, color=WHITE, idx=42)
    return sl


def make_slide_final():
    sl = Slide()
    _stripe(sl, 10)
    sl.add_text("Итог", emu(0.3), emu(0.4), emu(12.6), emu(0.7),
                size=32, bold=True, color=ACCENT, align="c", idx=20)

    bullets = [
        "Реализована end-to-end система Behavioral Cloning на PyTorch",
        "Архитектура: NVIDIA PilotNet CNN (BatchNorm + ELU + Dropout)",
        "Данные: Udacity Simulator, 3 камеры, аугментация, балансировка",
        "Мат. модель: MSE-регрессия, Adam, нормализация YUV-входа",
        "Авторский вклад: полная реализация + YOLOv8 интеграция",
        "Вся система воспроизводима в Colab за один запуск",
    ]
    for i, b in enumerate(bullets):
        y = emu(1.3) + i * emu(0.7)
        sl.add_rect(emu(1.3), y+emu(0.2), pt(9), pt(9), fill=ACCENT, idx=100+i)
        sl.add_text(b, emu(1.7), y, emu(11), emu(0.6),
                    size=18, color=WHITE, idx=200+i)

    sl.add_rect(emu(1.5), emu(5.5), emu(10), emu(1.3),
                fill=BLUE2, line=ACCENT, line_w=pt(1.5), idx=50)
    sl.add_text("Спасибо за внимание!\nГотов ответить на вопросы.",
                emu(1.7), emu(5.6), emu(9.6), emu(1.1),
                size=22, bold=True, color=WHITE, align="c", idx=51)
    return sl


# ─── PPTX ASSEMBLY ────────────────────────────────────────────────────────────

CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml"  ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml"
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml"
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml"
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml"
            ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
{slide_overrides}
  <Override PartName="/docProps/core.xml"
            ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml"
            ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

THEME = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="Theme1">
  <a:themeElements>
    <a:clrScheme name="Office">
      <a:dk1><a:sysClr lastClr="000000" val="windowText"/></a:dk1>
      <a:lt1><a:sysClr lastClr="ffffff" val="window"/></a:lt1>
      <a:dk2><a:srgbClr val="1F497D"/></a:dk2>
      <a:lt2><a:srgbClr val="EEECE1"/></a:lt2>
      <a:accent1><a:srgbClr val="00B4D8"/></a:accent1>
      <a:accent2><a:srgbClr val="FFD166"/></a:accent2>
      <a:accent3><a:srgbClr val="4BACC6"/></a:accent3>
      <a:accent4><a:srgbClr val="8064A2"/></a:accent4>
      <a:accent5><a:srgbClr val="4F81BD"/></a:accent5>
      <a:accent6><a:srgbClr val="00B050"/></a:accent6>
      <a:hlink><a:srgbClr val="0563C1"/></a:hlink>
      <a:folHlink><a:srgbClr val="954F72"/></a:folHlink>
    </a:clrScheme>
    <a:fontScheme name="Office">
      <a:majorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:majorFont>
      <a:minorFont><a:latin typeface="Calibri"/><a:ea typeface=""/><a:cs typeface=""/></a:minorFont>
    </a:fontScheme>
    <a:fmtScheme name="Office">
      <a:fillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="50000"/><a:satMod val="300000"/></a:schemeClr></a:gs><a:gs pos="35000"><a:schemeClr val="phClr"><a:tint val="37000"/><a:satMod val="300000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="15000"/><a:satMod val="350000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="1"/></a:gradFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:shade val="51000"/><a:satMod val="130000"/></a:schemeClr></a:gs><a:gs pos="80000"><a:schemeClr val="phClr"><a:shade val="93000"/><a:satMod val="130000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="94000"/><a:satMod val="135000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>
      </a:fillStyleLst>
      <a:lnStyleLst>
        <a:ln w="9525" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"><a:shade val="95000"/><a:satMod val="105000"/></a:schemeClr></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="25400" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>
        <a:ln w="38100" cap="flat" cmpd="sng" algn="ctr"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>
      </a:lnStyleLst>
      <a:effectStyleLst>
        <a:effectStyle><a:effectLst><a:outerShdw blurRad="40000" dist="20000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="38000"/></a:srgbClr></a:outerShdw></a:effectLst></a:effectStyle>
        <a:effectStyle><a:effectLst><a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr></a:outerShdw></a:effectLst></a:effectStyle>
        <a:effectStyle><a:effectLst><a:outerShdw blurRad="40000" dist="23000" dir="5400000" rotWithShape="0"><a:srgbClr val="000000"><a:alpha val="35000"/></a:srgbClr></a:outerShdw></a:effectLst><a:scene3d><a:camera prst="orthographicFront"><a:rot lat="0" lon="0" rev="0"/></a:camera><a:lightRig rig="threePt" dir="t"><a:rot lat="0" lon="0" rev="1200000"/></a:lightRig></a:scene3d><a:sp3d><a:bevelT w="63500" h="25400"/></a:sp3d></a:effectStyle>
      </a:effectStyleLst>
      <a:bgFillStyleLst>
        <a:solidFill><a:schemeClr val="phClr"/></a:solidFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="40000"/><a:satMod val="350000"/></a:schemeClr></a:gs><a:gs pos="40000"><a:schemeClr val="phClr"><a:tint val="45000"/><a:satMod val="350000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:shade val="20000"/><a:satMod val="350000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>
        <a:gradFill rotWithShape="1"><a:gsLst><a:gs pos="0"><a:schemeClr val="phClr"><a:tint val="80000"/><a:shade val="80000"/></a:schemeClr></a:gs><a:gs pos="100000"><a:schemeClr val="phClr"><a:tint val="50000"/><a:shade val="44000"/></a:schemeClr></a:gs></a:gsLst><a:lin ang="16200000" scaled="0"/></a:gradFill>
      </a:bgFillStyleLst>
    </a:fmtScheme>
  </a:themeElements>
</a:theme>"""

SLIDE_MASTER = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/><a:chOff x="0" y="0"/><a:chExt cx="12192000" cy="6858000"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>
  <p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>
  <p:txStyles><p:titleStyle><a:lvl1pPr algn="ctr"><a:defRPr lang="ru-RU" sz="2800" b="1"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:titleStyle><p:bodyStyle><a:lvl1pPr><a:defRPr lang="ru-RU" sz="1800"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:bodyStyle><p:otherStyle><a:lvl1pPr><a:defRPr lang="ru-RU"><a:solidFill><a:srgbClr val="FFFFFF"/></a:solidFill><a:latin typeface="Calibri"/></a:defRPr></a:lvl1pPr></p:otherStyle></p:txStyles>
</p:sldMaster>"""

SLIDE_MASTER_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>"""

SLIDE_LAYOUT = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
             xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
             xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
             type="blank" preserve="1">
  <p:cSld name="Blank"><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/><a:chOff x="0" y="0"/><a:chExt cx="12192000" cy="6858000"/></a:xfrm></p:grpSpPr></p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>"""

SLIDE_LAYOUT_RELS = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>"""


def build_presentation_xml(n_slides):
    p = Element(tag("p","presentation"))
    p.set("xmlns:a", NS["a"])
    p.set("xmlns:p", NS["p"])
    p.set("xmlns:r", NS["r"])
    sz = SubElement(p, tag("p","sldSz"))
    sz.set("cx", str(W)); sz.set("cy", str(H))
    notesSz = SubElement(p, tag("p","notesSz"))
    notesSz.set("cx","6858000"); notesSz.set("cy","9144000")
    sldMasterIdLst = SubElement(p, tag("p","sldMasterIdLst"))
    sm = SubElement(sldMasterIdLst, tag("p","sldMasterId"))
    sm.set("id","2147483648"); sm.set(tag("r","id"),"rId1")
    sldIdLst = SubElement(p, tag("p","sldIdLst"))
    for i in range(n_slides):
        s = SubElement(sldIdLst, tag("p","sldId"))
        s.set("id", str(256+i)); s.set(tag("r","id"), f"rId{i+2}")
    return xml_bytes(p)


def build_presentation_rels(n_slides):
    Rels = Element("Relationships")
    Rels.set("xmlns","http://schemas.openxmlformats.org/package/2006/relationships")
    r = SubElement(Rels, "Relationship")
    r.set("Id","rId1")
    r.set("Type","http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster")
    r.set("Target","slideMasters/slideMaster1.xml")
    for i in range(n_slides):
        rel = SubElement(Rels, "Relationship")
        rel.set("Id", f"rId{i+2}")
        rel.set("Type","http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide")
        rel.set("Target", f"slides/slide{i+1}.xml")
    return xml_bytes(Rels)


def build_core_xml():
    cp = Element(tag("cp","coreProperties"))
    cp.set("xmlns:cp", NS["cp"])
    cp.set("xmlns:dc", NS["dc"])
    cp.set("xmlns:xsi", NS["xsi"])
    t = SubElement(cp, tag("dc","title")); t.text = "Система автономного управления автомобилем"
    c = SubElement(cp, tag("dc","creator")); c.text = "Филиппов А."
    return xml_bytes(cp)


def build_app_xml(n_slides):
    ep = Element(tag("ep","Properties"))
    ep.set("xmlns:ep", NS["ep"])
    slides = SubElement(ep, tag("ep","Slides")); slides.text = str(n_slides)
    app = SubElement(ep, tag("ep","Application")); app.text = "Python PPTX Generator"
    return xml_bytes(ep)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    slides = [
        make_slide_title(),
        make_slide_problem(),
        make_slide_math(),
        make_slide_dataset(),
        make_slide_architecture(),
        make_slide_contribution(),
        make_slide_yolo(),
        make_slide_done(),
        make_slide_results(),
        make_slide_plan(),
        make_slide_final(),
    ]
    n = len(slides)

    slide_overrides = "\n".join(
        f'  <Override PartName="/ppt/slides/slide{i+1}.xml"\n'
        f'            ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        for i in range(n)
    )

    out = "presentation.pptx"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   CONTENT_TYPES.format(slide_overrides=slide_overrides))
        z.writestr("_rels/.rels", ROOT_RELS)
        z.writestr("ppt/presentation.xml", build_presentation_xml(n))
        z.writestr("ppt/_rels/presentation.xml.rels", build_presentation_rels(n))
        z.writestr("ppt/theme/theme1.xml", THEME)
        z.writestr("ppt/slideMasters/slideMaster1.xml", SLIDE_MASTER)
        z.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", SLIDE_MASTER_RELS)
        z.writestr("ppt/slideLayouts/slideLayout1.xml", SLIDE_LAYOUT)
        z.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", SLIDE_LAYOUT_RELS)
        z.writestr("docProps/core.xml", build_core_xml())
        z.writestr("docProps/app.xml", build_app_xml(n))

        for i, sl in enumerate(slides):
            z.writestr(f"ppt/slides/slide{i+1}.xml", sl.build_xml(i+1))
            z.writestr(f"ppt/slides/_rels/slide{i+1}.xml.rels", sl.build_rels())

    print(f"OK  Saved: {out}  ({n} slides)")


if __name__ == "__main__":
    main()
