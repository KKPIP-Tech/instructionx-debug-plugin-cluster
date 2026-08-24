# -*- coding: utf-8 -*-
"""组件 · 展示演示页：19 个数据展示组件，每组件一页，覆盖主要变体。

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
from .markdown_view import create_markdown_view_page
from .playground import PlaygroundPanel, with_playground

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

    .. 漂移风险提示::

        ``paintEvent`` 复制了 UIKit 基类 ``Timeline`` 的整段绘制逻辑以暴露
        绘制参数；UIKit 升级修改基类绘制实现时此处会漂移，需人工同步
        （上游提供 setter 前应持续保留本说明）。
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
        ctx = _TimelinePaintContext(self, painter)
        prev_dot_y, y = self._paint_items(painter, ctx)
        if self._pending:
            self._paint_pending(painter, ctx, y, prev_dot_y)
        painter.end()

    def _paint_items(self, painter, ctx):
        """逐项绘制连接线 / 节点 / 文本，返回 (末节点 y 坐标, 下一行起始 y)。"""
        y = 10
        prev_dot_y = None
        for item in self._items:
            row_h = self._row_height(item)
            dot_y = y + 11
            if prev_dot_y is not None:
                painter.setPen(QPen(ctx.line_color, self.line_width, self.line_style))
                painter.drawLine(ctx.dot_x, prev_dot_y, ctx.dot_x, dot_y)
            self._paint_dot(painter, ctx, item, dot_y)
            self._paint_item_text(painter, ctx, item, y)
            prev_dot_y = dot_y
            y += row_h
        return prev_dot_y, y

    def _paint_dot(self, painter, ctx, item, dot_y) -> None:
        """绘制节点：带图标时绘制图标，否则绘制实心圆点。"""
        icon = item["icon"]
        if isinstance(icon, QIcon) and not icon.isNull():
            painter.fillRect(QRect(ctx.dot_x - 7, dot_y - 7, 14, 14),
                             QColor(T("color.bg.base")))
            icon.paint(painter, QRect(ctx.dot_x - 7, dot_y - 7, 14, 14))
            return
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color_of(item))
        painter.drawEllipse(ctx.dot_x - ctx.r, dot_y - ctx.r, ctx.r * 2, ctx.r * 2)

    def _paint_item_text(self, painter, ctx, item, y) -> None:
        """绘制条目标题文本与（可选）时间文本。"""
        painter.setFont(ctx.font_text)
        painter.setPen(ctx.text_primary)
        painter.drawText(ctx.text_rect(y, 22), ctx.align, item["text"])
        if item["time"]:
            painter.setFont(ctx.font_time)
            painter.setPen(ctx.text_tertiary)
            painter.drawText(ctx.text_rect(y + 22, 16), ctx.align, item["time"])

    def _paint_pending(self, painter, ctx, y, prev_dot_y) -> None:
        """绘制尾部 pending：虚线 + 空心节点 + 计数文本。"""
        dot_y = y + 30
        painter.setPen(QPen(ctx.line_color, self.line_width, Qt.DashLine))
        start_y = prev_dot_y if prev_dot_y is not None else y
        painter.drawLine(ctx.dot_x, start_y, ctx.dot_x, dot_y)
        painter.setPen(QPen(QColor(T("color.primary")), 1.5))
        painter.setBrush(QColor(T("color.bg.base")))
        painter.drawEllipse(ctx.dot_x - ctx.r, dot_y - ctx.r, ctx.r * 2, ctx.r * 2)
        painter.setFont(ctx.font_text)
        painter.setPen(ctx.text_tertiary)
        painter.drawText(ctx.text_rect(dot_y - 11, 22), ctx.align,
                         str(self._pending))


class _TimelinePaintContext:
    """``TimelineEx`` 单次 paintEvent 的共享上下文（颜色 / 字体 / 几何量）。"""

    def __init__(self, tl, painter):
        self.line_color = QColor(T("color.border"))
        self.text_primary = QColor(T("color.text.primary"))
        self.text_tertiary = QColor(T("color.text.tertiary"))
        self.font_text = painter.font()
        self.font_text.setPixelSize(int(tl.title_font_size))
        self.font_time = painter.font()
        self.font_time.setPixelSize(int(tl.time_font_size))
        self.right = tl.axis_side == "right"
        self.w = tl.width()
        self.dot_x = self.w - 16 if self.right else 16
        self.r = int(tl.dot_radius)
        self.align = (Qt.AlignVCenter | Qt.AlignRight) if self.right \
            else (Qt.AlignVCenter | Qt.AlignLeft)

    def text_rect(self, y, h) -> QRect:
        """按轴侧计算文本绘制矩形。"""
        if self.right:
            return QRect(8, y, self.dot_x - 20, h)
        return QRect(36, y, self.w - 44, h)


_TL_ICONS = [
    QStyle.StandardPixmap.SP_FileDialogNewFolder,
    QStyle.StandardPixmap.SP_DialogApplyButton,
    QStyle.StandardPixmap.SP_ArrowForward,
]


class _TimelineDemo:
    """时间轴演示页的状态与构建逻辑（游乐场回调拆为方法以满足行数限制）。

    持有演示状态、``TimelineEx`` 实例与条目模板；面板回调经属性读写当前实例。
    """

    def __init__(self, tr):
        self._tr = tr
        self.state = {
            "colors": [None, "success", None],  # None = 主题 primary
            "icon_mode": False,
            "pending_on": True,
            "pending_text": tr("timeline.pending_default"),
        }
        self.tl = TimelineEx(pending=self.state["pending_text"])
        self.tl.setMinimumHeight(260)
        self.items = [(tr(f"timeline.item.{i}"), t) for i, t in
                      ((1, "2026-07-21 09:30"), (2, "2026-07-21 09:32"),
                       (3, "2026-07-21 09:35"))]

    def rebuild_items(self) -> None:
        """按当前状态重建时间轴条目（颜色 / 图标模式变化时调用）。"""
        self.tl.clear()
        for i, (text, time) in enumerate(self.items):
            icon = self.tl.style().standardIcon(_TL_ICONS[i]) \
                if self.state["icon_mode"] else None
            self.tl.add_item(text, time=time, color=self.state["colors"][i],
                             icon=icon)

    def apply_pending(self, *_):
        """按开关状态应用 pending 文本。"""
        self.tl.set_pending(
            self.state["pending_text"] if self.state["pending_on"] else None)

    def build_panel(self) -> PlaygroundPanel:
        """构建参数游乐场面板（注册顺序即面板展示顺序）。"""
        panel = PlaygroundPanel(self._tr("timeline.panel_title"))
        self._register_color_params(panel)
        self._register_pending_params(panel)
        self._register_line_params(panel)
        self._register_layout_params(panel)
        self._register_font_params(panel)
        return panel

    def _register_color_params(self, panel) -> None:
        """注册三个节点的颜色选择参数。"""
        tr, state = self._tr, self.state
        color_opts = [(tr("timeline.opt.theme"), None),
                      (tr("timeline.opt.success"), "success"),
                      (tr("timeline.opt.warning"), "warning"),
                      (tr("timeline.opt.danger"), "danger")]
        for i in range(3):
            panel.add_choice(
                tr("timeline.p.node_color", n=i + 1), color_opts, state["colors"][i],
                lambda v, i=i: (state["colors"].__setitem__(i, v),
                                self.rebuild_items()),
                key=f"color{i}")

    def _register_pending_params(self, panel) -> None:
        """注册 pending 开关 / 文本与节点图标模式参数。"""
        tr, state = self._tr, self.state
        panel.add_bool(tr("timeline.p.pending_on"), True,
                       lambda v: (state.__setitem__("pending_on", v),
                                  self.apply_pending()), key="pending_on")
        panel.add_text(tr("timeline.p.pending_text"), state["pending_text"],
                       lambda v: (state.__setitem__("pending_text", v),
                                  self.apply_pending()), key="pending_text")
        panel.add_choice(tr("timeline.p.icon_mode"),
                         [(tr("timeline.opt.dot"), False),
                          (tr("timeline.opt.icon"), True)],
                         False,
                         lambda v: (state.__setitem__("icon_mode", v),
                                    self.rebuild_items()), key="icon_mode")

    def _register_line_params(self, panel) -> None:
        """注册连接线样式 / 线宽与节点半径参数。"""
        tr, tl = self._tr, self.tl
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

    def _register_layout_params(self, panel) -> None:
        """注册行距与轴线位置参数。"""
        tr, tl = self._tr, self.tl
        panel.add_int(tr("timeline.p.spacing"), 0, 0, 24,
                      lambda v: (setattr(tl, "extra_spacing", v),
                                 tl.updateGeometry(), tl.update()),
                      key="spacing")
        panel.add_choice(tr("timeline.p.axis_side"),
                         [(tr("timeline.opt.left"), "left"),
                          (tr("timeline.opt.right"), "right")], "left",
                         lambda v: (setattr(tl, "axis_side", v), tl.update()),
                         key="axis_side")

    def _register_font_params(self, panel) -> None:
        """注册标题 / 时间字号参数。"""
        tr, tl = self._tr, self.tl
        panel.add_int(tr("timeline.p.font_size"), 13, 10, 18,
                      lambda v: (setattr(tl, "title_font_size", v), tl.update()),
                      key="font_size")
        panel.add_int(tr("timeline.p.time_font_size"), 11, 8, 14,
                      lambda v: (setattr(tl, "time_font_size", v), tl.update()),
                      key="time_font_size")


def create_timeline_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """时间轴演示页：参数游乐场（状态与构建逻辑见 ``_TimelineDemo``）。"""
    tr = _tr_of(i18n)
    s = Section(tr("timeline.sec"))
    demo = _TimelineDemo(tr)
    demo.rebuild_items()
    panel = demo.build_panel()
    s.layout().addWidget(with_playground(demo.tl, panel))
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
    anchor.clicked.connect(lambda: pop.show_for(anchor, placement="bottom"))
    s.layout().addWidget(row(anchor))
    s.layout().addWidget(hint_label(tr("popover.hint"), role="tertiary"))
    page = make_page(tr("popover.title"), tr("popover.desc"), [s])
    # 弹出层无父控件，随页面实例持有防止被 GC（页面销毁即释放，
    # 不使用模块级列表以免无限增长）
    page._keep_popups = [pop]
    return page


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
    ("markdown_view", create_markdown_view_page),
]
