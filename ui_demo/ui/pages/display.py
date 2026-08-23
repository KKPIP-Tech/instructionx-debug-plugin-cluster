# -*- coding: utf-8 -*-
"""组件 · 展示演示页：18 个数据展示组件，每组件一页，覆盖主要变体。

页面 = 标题 + 说明 + 分区演示，紧凑排布；亮 / 暗主题切换自动换肤。
文案经 ``bind_tr`` 按 ``display`` 分组取词（键前缀 = 组件导航键）。
"""

from typing import Optional

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.components.avatar import Avatar
from InstructionX_UIKit.components.badge import Badge
from InstructionX_UIKit.components.calendar import Calendar
from InstructionX_UIKit.components.card import Card
from InstructionX_UIKit.components.carousel import Carousel
from InstructionX_UIKit.components.collapse import Collapse
from InstructionX_UIKit.components.comment import CommentView
from InstructionX_UIKit.components.descriptions import Descriptions
from InstructionX_UIKit.components.empty import Empty
from InstructionX_UIKit.components.image_view import ImageView
from InstructionX_UIKit.components.list_view import ListWidget
from InstructionX_UIKit.components.popover import Popover
from InstructionX_UIKit.components.qrcode_view import QRCodeView
from InstructionX_UIKit.components.statistic import Statistic
from InstructionX_UIKit.components.table import Table
from InstructionX_UIKit.components.timeline import Timeline
from InstructionX_UIKit.components.tooltip import set_tooltip
from InstructionX_UIKit.components.tree import Tree
from InstructionX_UIKit.theme import T, set_property

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, col, hint_label, make_page, row
from .playground import PlaygroundPanel, with_playground

_POPOVERS = []  # 防止弹出层被 GC

#: 走马灯演示页背景色
_CAROUSEL_COLORS = ["#7C5CFC", "#3E7E5F", "#C08A3E"]


def _tr_of(i18n):
    """本页统一取词闭包（分组 ``display``）。"""
    return bind_tr(i18n, "display")


def _gradient_pixmap(w=240, h=160, c1="#3F5E8C", c2="#6BA98A"):
    """生成一张渐变测试图。"""
    pm = QPixmap(w, h)
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, QColor(c1))
    grad.setColorAt(1, QColor(c2))
    painter = QPainter(pm)
    painter.fillRect(pm.rect(), grad)
    painter.end()
    return pm


def _disabled(widget) -> QWidget:
    widget.setEnabled(False)
    return widget


def create_avatar_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("avatar.sec"))
    img = Avatar(size="lg")
    img.set_image(_gradient_pixmap(80, 80))
    s.layout().addWidget(row(
        Avatar(tr("avatar.name.1"), size="lg"),
        Avatar(tr("avatar.name.2"), shape="square", size="lg"),
        img, Avatar(size="lg"), Avatar(tr("avatar.name.3"), size=28)))
    return make_page(tr("avatar.title"), tr("avatar.desc"), [s])


def create_badge_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("badge.sec"))
    s.layout().addWidget(row(
        Badge(QPushButton(tr("badge.btn.messages")), count=5),
        Badge(QPushButton(tr("badge.btn.notifications")), count=120),
        Badge(QPushButton(tr("badge.btn.dot")), dot=True),
        Badge(count=8),
        Badge(dot=True, color="success")))
    return make_page(tr("badge.title"), tr("badge.desc"), [s])


def create_card_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("card.sec"))
    card = Card(tr("card.order.title"), hoverable=True)
    extra = QPushButton(tr("card.order.more"))
    set_property(extra, "variant", "link")
    set_property(extra, "size", "sm")
    card.set_extra(extra)
    card.body_layout().addWidget(QLabel(tr("card.order.body")))
    card.set_footer(tr("card.order.footer"))
    card2 = Card(tr("card.plain.title"), bordered=False)
    card2.body_layout().addWidget(QLabel(tr("card.plain.body")))
    s.layout().addWidget(row(card, card2))
    return make_page(tr("card.title"), tr("card.desc"), [s])


def create_descriptions_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("descriptions.sec"))
    desc = Descriptions(tr("descriptions.title"), bordered=True)
    desc.set_items([
        (tr("descriptions.label.name"), tr("descriptions.value.name")),
        (tr("descriptions.label.phone"), "138****8000"),
        (tr("descriptions.label.city"), tr("descriptions.value.city")),
        (tr("descriptions.label.mail"), "zhang@example.com"),
        (tr("descriptions.label.role"), tr("descriptions.value.role")),
        (tr("descriptions.label.status"), tr("descriptions.value.status")),
    ])
    s.layout().addWidget(desc)
    return make_page(tr("descriptions.page_title"), tr("descriptions.desc"), [s])


def create_list_view_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("list_view.sec"))
    lw = ListWidget(item_height=36)
    lw.add_items([tr(f"list_view.item.{k}") for k in
                  ("inbox", "starred", "sent", "drafts", "trash")])
    lw.setCurrentRow(1)
    lw.setFixedSize(300, 240)
    s.layout().addWidget(row(lw))
    return make_page(tr("list_view.title"), tr("list_view.desc"), [s])


def create_table_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("table.sec"))
    table = Table()
    regions = [tr(f"table.region.{k}") for k in ("east", "north", "south", "southwest")]
    table.set_data(
        [tr("table.header.name"), tr("table.header.dept"), tr("table.header.sales")],
        [[tr("table.name.1"), regions[0], 12800],
         [tr("table.name.2"), regions[1], 9600],
         [tr("table.name.3"), regions[2], 15320],
         [tr("table.name.4"), regions[3], 8450]])
    table.setFixedHeight(200)
    s.layout().addWidget(table)
    empty = Table()
    empty.set_data([tr("table.header.name"), tr("table.header.dept")], [])
    empty.set_empty_text(tr("table.empty"))
    empty.setFixedHeight(120)
    s.layout().addWidget(empty)
    return make_page(tr("table.title"), tr("table.desc"), [s])


def create_tree_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("tree.sec"))
    tree = Tree(checkable=True)
    tree.set_data([
        (tr("tree.fruit"), [(tr("tree.apple"), [(tr("tree.fuji"), []),
                                                (tr("tree.gala"), [])]),
                            (tr("tree.banana"), [])]),
        (tr("tree.veg"), [(tr("tree.cabbage"), []), (tr("tree.radish"), [])]),
    ])
    tree.expand_all()
    tree.setFixedSize(320, 240)
    s.layout().addWidget(row(tree))
    return make_page(tr("tree.title"), tr("tree.desc"), [s])


class TimelineEx(Timeline):
    """时间轴游乐场扩展（demo 侧子类，不改动 InstructionX_UIKit）。

    InstructionX_UIKit ``Timeline`` 仅暴露 ``add_item`` / ``set_pending`` 等数据 API，
    线条样式 / 粗细、节点半径、行距、字号、轴侧等绘制参数没有 setter；
    这里以子类属性 + 重写 ``paintEvent`` / ``_row_height`` 的方式暴露，
    数据层面仍完全复用基类 API。
    """

    def __init__(self, pending: str = None, parent=None):
        super().__init__(pending, parent)
        self.line_width = 1.0               # 连接线宽 px
        self.line_style = Qt.SolidLine      # 连接线样式
        self.dot_radius = 5                 # 节点半径 px
        self.extra_spacing = 0              # 每行附加间距 px
        self.axis_side = "left"             # 轴线位置：left / right
        self.title_font_size = T("font.md")
        self.time_font_size = T("font.xs")

    def _row_height(self, item) -> int:
        base = 46 if item["time"] else 30
        return base + int(self.extra_spacing)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        line_color = QColor(T("color.border"))
        text_primary = QColor(T("color.text.primary"))
        text_tertiary = QColor(T("color.text.tertiary"))

        font_text = painter.font()
        font_text.setPixelSize(int(self.title_font_size))
        font_time = painter.font()
        font_time.setPixelSize(int(self.time_font_size))

        right = self.axis_side == "right"
        w = self.width()
        dot_x = w - 16 if right else 16
        r = int(self.dot_radius)
        align = (Qt.AlignVCenter | Qt.AlignRight) if right \
            else (Qt.AlignVCenter | Qt.AlignLeft)

        def text_rect(y, h):
            if right:
                return QRect(8, y, dot_x - 20, h)
            return QRect(36, y, w - 44, h)

        y = 10
        prev_dot_y = None
        for item in self._items:
            row_h = self._row_height(item)
            dot_y = y + 11
            if prev_dot_y is not None:
                painter.setPen(QPen(line_color, self.line_width, self.line_style))
                painter.drawLine(dot_x, prev_dot_y, dot_x, dot_y)
            icon = item["icon"]
            if isinstance(icon, QIcon) and not icon.isNull():
                painter.fillRect(QRect(dot_x - 7, dot_y - 7, 14, 14),
                                 QColor(T("color.bg.base")))
                icon.paint(painter, QRect(dot_x - 7, dot_y - 7, 14, 14))
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(self._color_of(item))
                painter.drawEllipse(dot_x - r, dot_y - r, r * 2, r * 2)
            painter.setFont(font_text)
            painter.setPen(text_primary)
            painter.drawText(text_rect(y, 22), align, item["text"])
            if item["time"]:
                painter.setFont(font_time)
                painter.setPen(text_tertiary)
                painter.drawText(text_rect(y + 22, 16), align, item["time"])
            prev_dot_y = dot_y
            y += row_h

        # 尾部 pending：虚线 + 空心节点
        if self._pending:
            dot_y = y + 30
            painter.setPen(QPen(line_color, self.line_width, Qt.DashLine))
            start_y = prev_dot_y if prev_dot_y is not None else y
            painter.drawLine(dot_x, start_y, dot_x, dot_y)
            painter.setPen(QPen(QColor(T("color.primary")), 1.5))
            painter.setBrush(QColor(T("color.bg.base")))
            painter.drawEllipse(dot_x - r, dot_y - r, r * 2, r * 2)
            painter.setFont(font_text)
            painter.setPen(text_tertiary)
            painter.drawText(text_rect(dot_y - 11, 22), align,
                             str(self._pending))
        painter.end()


_TL_ICONS = [
    QStyle.StandardPixmap.SP_FileDialogNewFolder,
    QStyle.StandardPixmap.SP_DialogApplyButton,
    QStyle.StandardPixmap.SP_ArrowForward,
]


def create_timeline_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("timeline.sec"))
    state = {
        "colors": [None, "success", None],  # None = 主题 primary
        "icon_mode": False,
        "pending_on": True,
        "pending_text": tr("timeline.pending_default"),
    }
    tl = TimelineEx(pending=state["pending_text"])
    tl.setMinimumHeight(260)
    items = [(tr(f"timeline.item.{i}"), t) for i, t in
             ((1, "2026-07-21 09:30"), (2, "2026-07-21 09:32"),
              (3, "2026-07-21 09:35"))]

    def rebuild_items():
        tl.clear()
        for i, (text, time) in enumerate(items):
            icon = tl.style().standardIcon(_TL_ICONS[i]) \
                if state["icon_mode"] else None
            tl.add_item(text, time=time, color=state["colors"][i], icon=icon)

    def apply_pending(*_):
        tl.set_pending(state["pending_text"] if state["pending_on"] else None)

    rebuild_items()

    panel = PlaygroundPanel(tr("timeline.panel_title"))
    color_opts = [(tr("timeline.opt.theme"), None), (tr("timeline.opt.success"), "success"),
                  (tr("timeline.opt.warning"), "warning"),
                  (tr("timeline.opt.danger"), "danger")]
    for i in range(3):
        panel.add_choice(
            tr("timeline.p.node_color", n=i + 1), color_opts, state["colors"][i],
            lambda v, i=i: (state["colors"].__setitem__(i, v), rebuild_items()),
            key=f"color{i}")
    panel.add_bool(tr("timeline.p.pending_on"), True,
                   lambda v: (state.__setitem__("pending_on", v),
                              apply_pending()), key="pending_on")
    panel.add_text(tr("timeline.p.pending_text"), state["pending_text"],
                   lambda v: (state.__setitem__("pending_text", v),
                              apply_pending()), key="pending_text")
    panel.add_choice(tr("timeline.p.icon_mode"),
                     [(tr("timeline.opt.dot"), False), (tr("timeline.opt.icon"), True)],
                     False,
                     lambda v: (state.__setitem__("icon_mode", v),
                                rebuild_items()), key="icon_mode")
    panel.add_choice(tr("timeline.p.line_style"),
                     [(tr("timeline.opt.solid"), Qt.SolidLine),
                      (tr("timeline.opt.dashed"), Qt.DashLine),
                      (tr("timeline.opt.dotted"), Qt.DotLine)], Qt.SolidLine,
                     lambda v: (setattr(tl, "line_style", v), tl.update()),
                     key="line_style")
    panel.add_int(tr("timeline.p.line_width"), 1, 1, 4,
                  lambda v: (setattr(tl, "line_width", float(v)), tl.update()),
                  key="line_width")
    panel.add_int(tr("timeline.p.dot_radius"), 5, 3, 9,
                  lambda v: (setattr(tl, "dot_radius", v), tl.update()),
                  key="dot_radius")
    panel.add_int(tr("timeline.p.spacing"), 0, 0, 24,
                  lambda v: (setattr(tl, "extra_spacing", v),
                             tl.updateGeometry(), tl.update()),
                  key="spacing")
    panel.add_choice(tr("timeline.p.axis_side"),
                     [(tr("timeline.opt.left"), "left"),
                      (tr("timeline.opt.right"), "right")], "left",
                     lambda v: (setattr(tl, "axis_side", v), tl.update()),
                     key="axis_side")
    panel.add_int(tr("timeline.p.font_size"), 13, 10, 18,
                  lambda v: (setattr(tl, "title_font_size", v), tl.update()),
                  key="font_size")
    panel.add_int(tr("timeline.p.time_font_size"), 11, 8, 14,
                  lambda v: (setattr(tl, "time_font_size", v), tl.update()),
                  key="time_font_size")

    s.layout().addWidget(with_playground(tl, panel))
    return make_page(tr("timeline.title"), tr("timeline.desc"), [s])


def create_statistic_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("statistic.sec"))
    s1 = Statistic(tr("statistic.users"), 12800)
    s1.set_suffix(tr("statistic.suffix.people"))
    s1.set_trend(12.5)
    s2 = Statistic(tr("statistic.revenue"), 93456.78, precision=2)
    s2.set_prefix("¥")
    s2.set_trend(-3.2)
    s3 = Statistic(tr("statistic.tickets"), 42)
    s.layout().addWidget(row(s1, s2, s3, spacing=48))
    return make_page(tr("statistic.title"), tr("statistic.desc"), [s])


def create_calendar_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("calendar.sec"))
    cal = Calendar()
    cal.setFixedSize(420, 340)
    s.layout().addWidget(row(cal))
    return make_page(tr("calendar.title"), tr("calendar.desc"), [s])


def create_carousel_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("carousel.sec"))
    carousel = Carousel()
    for i, color in enumerate(_CAROUSEL_COLORS):
        page = QLabel(tr("carousel.page", n=i + 1))
        page.setAlignment(Qt.AlignCenter)
        page.setStyleSheet(
            f"background-color: {color}; color: white; font-size: 20px; "
            f"border-radius: 8px; margin: 4px;")
        carousel.add_page(page)
    carousel.setFixedSize(520, 260)
    s.layout().addWidget(row(carousel))
    return make_page(tr("carousel.title"), tr("carousel.desc"), [s])


def create_image_view_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("image_view.sec"))
    ok = ImageView(_gradient_pixmap(400, 300))
    ok.setFixedSize(220, 165)
    bad = ImageView("/nonexistent/path/to/image.png")
    bad.setFixedSize(220, 165)
    s.layout().addWidget(row(ok, bad))
    s.layout().addWidget(hint_label(tr("image_view.hint"), role="tertiary"))
    return make_page(tr("image_view.title"), tr("image_view.desc"), [s])


def create_qrcode_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("qrcode_view.sec"))
    s.layout().addWidget(row(
        QRCodeView("https://example.com/uik", size=130),
        QRCodeView(tr("qrcode_view.content"), size=130, error_correction="H"),
        spacing=24))
    return make_page(tr("qrcode_view.title"), tr("qrcode_view.desc"), [s])


def create_comment_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("comment.sec"))
    c = CommentView(tr("comment.author.1"), tr("comment.body.1"),
                    tr("comment.time.1"),
                    actions=[tr("comment.action.reply"), tr("comment.action.like")])
    c.add_reply(CommentView(tr("comment.author.2"), tr("comment.body.2"),
                            tr("comment.time.2"),
                            actions=[tr("comment.action.reply")]))
    c.add_reply(CommentView(tr("comment.author.3"), tr("comment.body.3"),
                            tr("comment.time.3")))
    s.layout().addWidget(c)
    return make_page(tr("comment.title"), tr("comment.desc"), [s])


def create_collapse_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("collapse.sec"))
    cl = Collapse()
    cl.add_panel(tr("collapse.q1"), tr("collapse.a1"), expanded=True)
    cl.add_panel(tr("collapse.q2"), tr("collapse.a2"))
    cl.add_panel(tr("collapse.q3"), QLabel(tr("collapse.a3")))
    cl.setMinimumWidth(480)
    cl.setMinimumHeight(260)
    s.layout().addWidget(cl)
    return make_page(tr("collapse.title"), tr("collapse.desc"), [s])


def create_empty_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("empty.sec"))
    empty = Empty(tr("empty.text"))
    empty.set_action(tr("empty.action"))
    empty.setMinimumHeight(280)
    s.layout().addWidget(empty)
    return make_page(tr("empty.title"), tr("empty.desc"), [s])


def create_tooltip_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("tooltip.sec"))
    btn = QPushButton(tr("tooltip.btn.hover"))
    set_property(btn, "variant", "primary")
    set_tooltip(btn, tr("tooltip.tip.rich"), title=tr("tooltip.tip.title"))
    btn2 = QPushButton(tr("tooltip.btn.plain"))
    set_tooltip(btn2, tr("tooltip.tip.plain"))
    s.layout().addWidget(row(btn, btn2))
    s.layout().addWidget(hint_label(tr("tooltip.hint"), role="tertiary"))
    return make_page(tr("tooltip.title"), tr("tooltip.desc"), [s])


def create_popover_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("popover.sec"))
    anchor = QPushButton(tr("popover.btn"))
    set_property(anchor, "variant", "primary")
    pop = Popover(tr("popover.pop.title"), tr("popover.pop.body"))
    _POPOVERS.append(pop)
    anchor.clicked.connect(lambda: pop.show_for(anchor, placement="bottom"))
    s.layout().addWidget(row(anchor))
    s.layout().addWidget(hint_label(tr("popover.hint"), role="tertiary"))
    return make_page(tr("popover.title"), tr("popover.desc"), [s])


#: 展示组件页注册表：(导航键, 页面工厂)；标题由 MainWidget 经 ``nav:page.<键>`` 取词
DISPLAY_PAGES = [
    ("avatar", create_avatar_page),
    ("badge", create_badge_page),
    ("card", create_card_page),
    ("descriptions", create_descriptions_page),
    ("list_view", create_list_view_page),
    ("table", create_table_page),
    ("tree", create_tree_page),
    ("timeline", create_timeline_page),
    ("statistic", create_statistic_page),
    ("calendar", create_calendar_page),
    ("carousel", create_carousel_page),
    ("image_view", create_image_view_page),
    ("qrcode_view", create_qrcode_page),
    ("comment", create_comment_page),
    ("collapse", create_collapse_page),
    ("empty", create_empty_page),
    ("tooltip", create_tooltip_page),
    ("popover", create_popover_page),
]
