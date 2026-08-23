# -*- coding: utf-8 -*-
"""设计令牌演示页：色板 / 字阶 / 字重 / 间距 / 圆角 / 阴影 / 断点 / 动效。

所有可视化均实时读取 ``InstructionX_UIKit.tokens`` 与 ``T()``，亮 / 暗切换后自动换肤。
色板采用「亮 / 暗对照」：每个语义色同时展示两套主题的取值。
文案经 ``bind_tr`` 按 ``tokens`` 分组取词（语言切换由 MainWidget 重建本页刷新）。
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import tokens as tk
from InstructionX_UIKit.theme import T, ThemeManager, apply_shadow, set_property

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, col, hint_label, make_page, row

__all__ = ["create_page"]


# ---------------------------------------------------------------------------
# 色板
# ---------------------------------------------------------------------------

#: [(色组取词键, [语义色键, ...]), ...]
_COLOR_GROUPS = [
    ("bg", ["bg.base", "bg.subtle", "bg.muted", "bg.elevated"]),
    ("border", ["border", "border.strong"]),
    ("text", ["text.primary", "text.secondary", "text.tertiary", "text.disabled"]),
    ("primary", ["primary", "primary.hover", "primary.pressed", "primary.subtle", "on.primary"]),
    ("success", ["success", "success.hover", "success.subtle"]),
    ("warning", ["warning", "warning.subtle"]),
    ("danger", ["danger", "danger.hover", "danger.subtle"]),
    ("overlay", ["overlay"]),
]


class _SplitChip(QFrame):
    """亮 / 暗对照色块：左半亮色值，右半暗色值。"""

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = f"color.{key}"
        self.setMinimumSize(120, 44)

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        half = rect.width() // 2
        left = rect.adjusted(0, 0, -(rect.width() - half), 0)
        right = rect.adjusted(half, 0, 0, 0)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(tk.LIGHT[self._key]))
        p.drawRoundedRect(left, 6, 6)
        p.setBrush(QColor(tk.DARK[self._key]))
        p.drawRoundedRect(right, 6, 6)
        # 分隔线 + 外框
        p.setPen(QPen(QColor(T("color.border.strong"))))
        p.drawLine(rect.center().x(), rect.top(), rect.center().x(), rect.bottom())
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(T("color.border"))))
        p.drawRoundedRect(rect, 6, 6)
        p.end()


class _ColorCard(QFrame):
    """单个语义色卡片：对照色块 + 名称 + 亮 / 暗十六进制。"""

    def __init__(self, key: str, tr, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(4)
        lay.addWidget(_SplitChip(key))
        name = QLabel(key)
        f = QFont()
        f.setPixelSize(T("font.sm"))
        f.setWeight(QFont.Weight(QFont.Medium))
        name.setFont(f)
        lay.addWidget(name)
        full = f"color.{key}"
        hex_lab = QLabel(tr("card.hex", light=tk.LIGHT[full], dark=tk.DARK[full]))
        hex_f = QFont()
        hex_f.setPixelSize(T("font.xs"))
        hex_lab.setFont(hex_f)
        set_property(hex_lab, "role", "tertiary")
        lay.addWidget(hex_lab)


def _colors_section(tr) -> QFrame:
    box = Section(tr("section.colors"))
    for group_key, keys in _COLOR_GROUPS:
        box.layout().addWidget(hint_label(tr(f"color_group.{group_key}"), role="secondary"))
        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(10)
        for i, key in enumerate(keys):
            grid.addWidget(_ColorCard(key, tr), i // 4, i % 4)
        box.layout().addWidget(grid_host)
    return box


# ---------------------------------------------------------------------------
# 字阶 / 字重
# ---------------------------------------------------------------------------

#: (令牌键, 标签取词键)
_FONT_SCALES = [
    ("font.xs", "scale.xs"), ("font.sm", "scale.sm"), ("font.md", "scale.md"),
    ("font.lg", "scale.lg"), ("font.title.sm", "scale.title_sm"),
    ("font.title.md", "scale.title_md"), ("font.title.lg", "scale.title_lg"),
    ("font.display", "scale.display"), ("font.hero", "scale.hero"),
]

_FONT_WEIGHTS = [
    ("font.weight.regular", "weight.regular"),
    ("font.weight.medium", "weight.medium"),
    ("font.weight.semibold", "weight.semibold"),
    ("font.weight.bold", "weight.bold"),
]


def _scale_line(sample: QLabel, value_text: str, prop: str) -> QWidget:
    """一行「真实渲染示例 + 数值标签（text.tertiary，底对齐）」。"""
    line = QWidget()
    lay = QHBoxLayout(line)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    lay.addWidget(sample, 0, Qt.AlignBottom)
    value = hint_label(value_text, role="tertiary")
    value.setProperty(f"{prop}_value", sample.property(prop))
    lay.addWidget(value, 0, Qt.AlignBottom)
    lay.addStretch(1)
    return line


def _type_section(tr) -> QFrame:
    """字阶 / 字重真实渲染。

    注意：全局 QSS 的 ``QWidget { font-size: ... }`` 会覆盖 ``setFont`` 的
    字号（实测 Qt 6.11），因此示例文本改用实例级 QSS 声明 font-size /
    font-weight——实例规则比基座规则更具体，可稳定胜出，同时使
    ``label.font().pixelSize() / weight()`` 与令牌一致，便于自动化校验。
    """
    box = Section(tr("section.type"))
    box.layout().addWidget(hint_label(tr("type.scale_hint"), role="secondary"))
    for key, label_key in _FONT_SCALES:
        px = T(key)
        sample = QLabel(tr("type.scale_sample", label=tr(label_key), px=px))
        sample.setStyleSheet(f"font-size: {px}px;")
        sample.setProperty("type_scale", key)
        box.layout().addWidget(_scale_line(sample, f"{key} = {px}px", "type_scale"))
    box.layout().addSpacing(6)
    box.layout().addWidget(hint_label(tr("type.weight_hint"), role="secondary"))
    for key, label_key in _FONT_WEIGHTS:
        w = T(key)
        sample = QLabel(tr("type.weight_sample", label=tr(label_key)))
        sample.setStyleSheet(f"font-size: {T('font.lg')}px; font-weight: {w};")
        sample.setProperty("type_weight", key)
        box.layout().addWidget(_scale_line(sample, f"{key} = {w}", "type_weight"))
    return box


# ---------------------------------------------------------------------------
# 间距 / 圆角
# ---------------------------------------------------------------------------

class _Bar(QWidget):
    """间距可视化：一条指定宽度的高度条。"""

    def __init__(self, width: int, parent=None):
        super().__init__(parent)
        self.setFixedSize(max(width, 2), 18)
        ThemeManager.instance().theme_changed.connect(lambda *_: self.update())

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(T("color.primary")))
        p.drawRoundedRect(self.rect(), 4, 4)
        p.end()


class _RadiusBox(QWidget):
    """圆角可视化：一个指定圆角的填充方块。"""

    def __init__(self, radius: int, parent=None):
        super().__init__(parent)
        self._radius = radius
        self.setFixedSize(72, 48)
        ThemeManager.instance().theme_changed.connect(lambda *_: self.update())

    def paintEvent(self, event):  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(T("color.primary"))))
        p.setBrush(QColor(T("color.primary.subtle")))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1),
                          min(self._radius, 24), min(self._radius, 24))
        p.end()


def _spacing_radius_section(tr) -> QFrame:
    box = Section(tr("section.spacing"))
    box.layout().addWidget(hint_label(tr("spacing.hint"), role="secondary"))
    for key in ["space.0", "space.05", "space.1", "space.2", "space.3",
                "space.4", "space.5", "space.6", "space.8", "space.10",
                "space.12", "space.16"]:
        v = T(key)
        box.layout().addWidget(row(QLabel(f"{key} = {v}px"), _Bar(v)))
    box.layout().addSpacing(6)
    box.layout().addWidget(hint_label(tr("radius.hint"), role="secondary"))
    rad_row = QWidget()
    rad_lay = QHBoxLayout(rad_row)
    rad_lay.setContentsMargins(0, 0, 0, 0)
    rad_lay.setSpacing(16)
    for key in ["radius.sm", "radius.md", "radius.lg", "radius.xl", "radius.pill"]:
        v = T(key)
        item = col(_RadiusBox(v), hint_label(f"{key}\n{v}px", role="tertiary"))
        item.layout().setSpacing(4)
        rad_lay.addWidget(item, 0, Qt.AlignTop)
    rad_lay.addStretch(1)
    box.layout().addWidget(rad_row)
    return box


# ---------------------------------------------------------------------------
# 阴影 / 断点 / 动效
# ---------------------------------------------------------------------------

def _shadow_section(tr) -> QFrame:
    box = Section(tr("section.shadow"))
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(12, 16, 12, 16)
    lay.setSpacing(40)
    for level, label_key in (("sm", "shadow.sm"), ("md", "shadow.md"),
                             ("lg", "shadow.lg")):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFixedSize(140, 90)
        apply_shadow(card, level)
        inner = QVBoxLayout(card)
        lab = QLabel(tr(label_key))
        lab.setAlignment(Qt.AlignCenter)
        inner.addWidget(lab)
        lay.addWidget(card, 0, Qt.AlignCenter)
    lay.addStretch(1)
    box.layout().addWidget(host)
    return box


def _breakpoint_section(tr) -> QFrame:
    box = Section(tr("section.breakpoint"))
    desc = [
        ("xs", "< 640"), ("sm", "640 – 767"), ("md", "768 – 1023"),
        ("lg", "1024 – 1439"), ("xl", "≥ 1440"),
    ]
    for name, rng in desc:
        thr = T(f"breakpoint.{name}")
        box.layout().addWidget(hint_label(
            tr("breakpoint.line", name=name, range=rng, threshold=thr),
            role="secondary"))
    cur = _CurrentBreakpoint(tr)
    box.layout().addWidget(cur)
    return box


class _CurrentBreakpoint(QLabel):
    """实时显示当前窗口宽度对应的断点。"""

    def __init__(self, tr, parent=None):
        super().__init__(parent)
        self._tr = tr
        self._refresh()
        f = QFont()
        f.setWeight(QFont.Weight(QFont.Bold))
        self.setFont(f)

    def _refresh(self):
        w = self.window().width() if self.window() else 0
        bp = tk.Breakpoint.from_width(w)
        self.setText(self._tr("breakpoint.current", width=w, bp=bp))

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self._refresh()


def _motion_section(tr) -> QFrame:
    box = Section(tr("section.motion"))
    box.layout().addWidget(hint_label(tr("motion.duration_hint"), role="secondary"))
    for name, ms in tk.DURATION.items():
        bar = _Bar(int(ms / 2))  # 缩放以便观察
        box.layout().addWidget(row(QLabel(f"{name} = {ms}ms"), bar))
    box.layout().addSpacing(6)
    box.layout().addWidget(hint_label(tr("motion.easing_hint"), role="secondary"))
    for name in tk.EASING:
        box.layout().addWidget(hint_label(
            tr("motion.easing_item", name=name), role="tertiary"))
    return box


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------

def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """设计令牌演示页。"""
    tr = bind_tr(i18n, "tokens")
    sections = [
        _colors_section(tr),
        _type_section(tr),
        _spacing_radius_section(tr),
        _shadow_section(tr),
        _breakpoint_section(tr),
        _motion_section(tr),
    ]
    return make_page(tr("title"), tr("desc"), sections)
