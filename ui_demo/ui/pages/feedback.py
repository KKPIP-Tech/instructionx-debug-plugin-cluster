# -*- coding: utf-8 -*-
"""组件 · 反馈演示页：19 个导航与反馈组件，每组件一页，覆盖主要变体。

弹出类组件（对话框 / 抽屉 / 通知 / 轻提示 / 气泡确认 / 漫游引导）以
触发按钮演示；其余以内联变体演示。亮 / 暗主题切换自动换肤。
文案经 ``bind_tr`` 按 ``feedback`` 分组取词（键前缀 = 组件导航键）。
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.components.alert import Alert
from InstructionX_UIKit.components.anchor import Anchor
from InstructionX_UIKit.components.breadcrumb import Breadcrumb
from InstructionX_UIKit.components.dialog import Dialog
from InstructionX_UIKit.components.drawer import Drawer
from InstructionX_UIKit.components.dropdown import DropdownButton
from InstructionX_UIKit.components.message import Message
from InstructionX_UIKit.components.nav_menu import NavMenu
from InstructionX_UIKit.components.notification import Notification
from InstructionX_UIKit.components.page_header import PageHeader
from InstructionX_UIKit.components.pagination import Pagination
from InstructionX_UIKit.components.popconfirm import Popconfirm
from InstructionX_UIKit.components.progress_bar import CircleProgress, ProgressBar
from InstructionX_UIKit.components.result import ResultView
from InstructionX_UIKit.components.skeleton import Skeleton
from InstructionX_UIKit.components.spinner import Spinner
from InstructionX_UIKit.components.steps import Steps
from InstructionX_UIKit.components.tabs import Tabs
from InstructionX_UIKit.components.tour import Tour
from InstructionX_UIKit.theme import T, set_property

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, col, hint_label, make_page, row
from .playground import PlaygroundPanel, swap_widget, with_playground


def _tr_of(i18n):
    """本页统一取词闭包（分组 ``feedback``）。"""
    return bind_tr(i18n, "feedback")


def _primary(text):
    btn = QPushButton(text)
    set_property(btn, "variant", "primary")
    return btn


def _disabled(widget) -> QWidget:
    widget.setEnabled(False)
    return widget


def create_tabs_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("tabs.sec"))
    for variant in ("line", "card", "segmented"):
        t = Tabs(variant)
        for i in range(1, 4):
            page_name = tr(f"tabs.tab.{i}")
            lab = QLabel(tr("tabs.content", variant=variant, page=page_name))
            lab.setAlignment(Qt.AlignCenter)
            lab.setMinimumHeight(70)
            t.addTab(lab, page_name)
        t.setCurrentIndex(1)
        s.layout().addWidget(t)
    return make_page(tr("tabs.title"), tr("tabs.desc"), [s])


def _anchor_scroll_content(tr):
    """构建锚点演示的滚动内容区，返回 (滚动区, 锚点元数据, 区块控件列表)。"""
    area = QScrollArea()
    area.setWidgetResizable(True)
    content = QWidget()
    vbox = QVBoxLayout(content)
    vbox.setSpacing(12)
    sections = []
    metas = [("base", tr("anchor.sec.1")), ("safe", tr("anchor.sec.2")),
             ("notify", tr("anchor.sec.3")), ("about", tr("anchor.sec.4"))]
    for key, title in metas:
        sec = QLabel(title + "\n" + (tr("anchor.body") + "\n") * 5)
        sec.setFrameShape(QFrame.Shape.StyledPanel)
        vbox.addWidget(sec)
        sections.append(sec)
    area.setWidget(content)
    return area, metas, sections


def create_anchor_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("anchor.sec"))
    host = QWidget()
    lay = QHBoxLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(16)
    anchor = Anchor()
    anchor.setFixedWidth(150)
    area, metas, sections = _anchor_scroll_content(tr)
    anchor.set_items([(k, t, w) for (k, t), w in zip(metas, sections)])
    anchor.bind_scroll_area(area)
    lay.addWidget(anchor)
    lay.addWidget(area, 1)
    host.setMinimumHeight(300)
    s.layout().addWidget(host)
    return make_page(tr("anchor.title"), tr("anchor.desc"), [s])


def create_breadcrumb_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("breadcrumb.sec"))
    s.layout().addWidget(Breadcrumb([tr(f"breadcrumb.first.{i}") for i in range(1, 5)]))
    s.layout().addWidget(Breadcrumb([tr(f"breadcrumb.second.{i}") for i in range(1, 4)],
                                    separator=">"))
    return make_page(tr("breadcrumb.title"), tr("breadcrumb.desc"), [s])


def create_dropdown_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("dropdown.sec"))
    dd = DropdownButton(tr("dropdown.btn"))
    dd.add_item("edit", tr("dropdown.item.edit"), shortcut="Ctrl+E")
    dd.add_item("share", tr("dropdown.item.share"))
    dd.add_item("disabled", tr("dropdown.item.disabled"), enabled=False)
    dd.add_separator()
    dd.add_item("del", tr("dropdown.item.delete"), danger=True)
    s.layout().addWidget(row(dd))
    s.layout().addWidget(hint_label(tr("dropdown.hint"), role="tertiary"))
    return make_page(tr("dropdown.title"), tr("dropdown.desc"), [s])


def create_nav_menu_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("nav_menu.sec"))
    nav = NavMenu()
    nav.setFixedSize(250, 400)
    group1, group2 = tr("nav_menu.group.1"), tr("nav_menu.group.2")
    nav.add_group(group1)
    nav.add_item("dash", tr("nav_menu.item.dashboard"), group=group1)
    nav.add_item("monitor", tr("nav_menu.item.monitor"), group=group1)
    nav.add_group(group2)
    nav.add_item("user", tr("nav_menu.item.users"), group=group2)
    nav.add_item("role", tr("nav_menu.item.roles"), group=group2)
    nav.add_item("setting", tr("nav_menu.item.settings"))
    nav.set_current("monitor")
    s.layout().addWidget(row(nav))
    return make_page(tr("nav_menu.title"), tr("nav_menu.desc"), [s])


def create_page_header_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("page_header.sec"))
    ph = PageHeader(tr("page_header.order.title"), tr("page_header.order.sub"))
    ph.set_breadcrumb([tr(f"page_header.order.bc.{i}") for i in range(1, 4)])
    ph.add_action(QPushButton(tr("page_header.action.export")))
    ph.add_action(_primary(tr("page_header.action.edit")))
    ph2 = PageHeader(tr("page_header.settings.title"), tr("page_header.settings.sub"),
                     show_back=False)
    wrapper = col(ph, ph2, spacing=24)
    s.layout().addWidget(wrapper)
    return make_page(tr("page_header.title"), tr("page_header.desc"), [s])


def create_pagination_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("pagination.sec"))
    pg = Pagination(total=256, page_size=10, current=6)
    pg.set_show_jumper(True)
    pg.set_show_size_changer(True, options=(10, 20, 50))
    s.layout().addWidget(pg)
    s.layout().addWidget(Pagination(total=45, page_size=10))
    return make_page(tr("pagination.title"), tr("pagination.desc"), [s])


class StepsEx(Steps):
    """步骤条游乐场扩展（demo 侧子类，不改动 InstructionX_UIKit）。

    InstructionX_UIKit ``Steps`` 的方向为构造参数，节点半径 / 连接线宽与样式为模块
    常量、无 setter；这里以子类属性 + 重写绘制方法暴露这些演示参数，
    并额外提供「点击节点切换当前步骤」开关（基类无鼠标交互）。

    .. 漂移风险提示::

        ``_paint_horizontal`` / ``_paint_vertical`` / ``_draw_node`` 复制了
        UIKit 基类 ``Steps`` 的绘制逻辑以暴露绘制参数；UIKit 升级修改基类绘制
        实现时此处会漂移，需人工同步（上游提供 setter 前应持续保留本说明）。
    """

    def __init__(self, orientation=Qt.Horizontal, parent=None):
        super().__init__(orientation, parent)
        self.node_radius = 12            # 节点半径 px
        self.link_width = 2.0            # 连接线宽 px
        self.link_style = Qt.SolidLine   # 连接线样式
        self.clickable = False           # 点击节点切换当前步骤

    # -- 参数化绘制（逻辑与基类一致，仅替换半径 / 线宽 / 线型） ------------
    def _paint_horizontal(self, p) -> None:
        n = len(self._steps)
        if n == 0:
            return
        r = self.node_radius
        fonts = self._fonts()
        seg = self.width() / n
        cy = 26.0
        for i, st in enumerate(self._steps):
            self._paint_step_horizontal(p, i, n, st, seg, r, cy, fonts)

    def _paint_step_horizontal(self, p, i, n, st, seg, r, cy, fonts) -> None:
        """绘制单个水平步骤：连接线（非末位）+ 节点 + 文本。"""
        status = self.status_of(i)
        cx = i * seg + r + 4
        fm = QFontMetrics(fonts[0])
        title_w = fm.horizontalAdvance(st["title"])
        text_x = cx + r + 8
        if i < n - 1:
            x_start = text_x + title_w + 10
            x_end = (i + 1) * seg + 2
            if x_end > x_start:
                self._draw_link(p, status, QPointF(x_start, cy), QPointF(x_end, cy))
        self._draw_node(p, cx, cy, status, i)
        self._draw_texts(p, st, status, text_x, cy, *fonts, align_top=False)

    def _paint_vertical(self, p) -> None:
        n = len(self._steps)
        if n == 0:
            return
        r = self.node_radius
        fonts = self._fonts()
        row = max(56.0, self.height() / max(n, 1))
        cx = 20.0
        for i, st in enumerate(self._steps):
            self._paint_step_vertical(p, i, n, st, row, r, cx, fonts)

    def _paint_step_vertical(self, p, i, n, st, row, r, cx, fonts) -> None:
        """绘制单个垂直步骤：连接线（非末位）+ 节点 + 文本。"""
        status = self.status_of(i)
        cy = i * row + r + 6
        if i < n - 1:
            y_start = cy + r + 4
            y_end = (i + 1) * row + 6 - 4
            if y_end > y_start:
                self._draw_link(p, status, QPointF(cx, y_start), QPointF(cx, y_end))
        self._draw_node(p, cx, cy, status, i)
        self._draw_texts(p, st, status, cx + r + 10, cy, *fonts, align_top=False)

    def _draw_link(self, p, status, start, end) -> None:
        """绘制节点间连接线：颜色随前驱节点状态，线宽 / 线型取演示参数。"""
        color = T("color.primary") if status == "finish" else T("color.border")
        pen = QPen(QColor(color))
        pen.setWidthF(self.link_width)
        pen.setStyle(self.link_style)
        p.setPen(pen)
        p.drawLine(start, end)

    def _draw_node(self, p, cx, cy, status, index) -> None:
        r = self.node_radius
        fill, border, glyph, _title = self._colors(status)
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.setBrush(fill)
        pen = QPen(border)
        pen.setWidthF(1.6)
        p.setPen(pen)
        p.drawEllipse(rect)
        scale = r / 12.0  # 基类字形按 r=12 设计，随半径缩放
        if status == "finish":
            self._draw_finish_glyph(p, cx, cy, scale, glyph)
        elif status == "error":
            self._draw_error_glyph(p, cx, cy, scale, glyph)
        else:
            self._draw_index_glyph(p, rect, glyph, index)

    def _draw_finish_glyph(self, p, cx, cy, scale, glyph) -> None:
        """绘制完成态对勾字形。"""
        pen = QPen(glyph)
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawPolyline([
            QPointF(cx - 5.0 * scale, cy + 0.5 * scale),
            QPointF(cx - 1.5 * scale, cy + 4.0 * scale),
            QPointF(cx + 5.5 * scale, cy - 3.5 * scale),
        ])

    def _draw_error_glyph(self, p, cx, cy, scale, glyph) -> None:
        """绘制错误态叉形字形。"""
        pen = QPen(glyph)
        pen.setWidthF(1.8)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(cx - 3.5 * scale, cy - 3.5 * scale),
                   QPointF(cx + 3.5 * scale, cy + 3.5 * scale))
        p.drawLine(QPointF(cx + 3.5 * scale, cy - 3.5 * scale),
                   QPointF(cx - 3.5 * scale, cy + 3.5 * scale))

    def _draw_index_glyph(self, p, rect, glyph, index) -> None:
        """绘制默认 / 进行态的序号文本字形。"""
        font = QFont(self.font())
        font.setPixelSize(T("font.sm"))
        font.setWeight(QFont.DemiBold)
        p.setFont(font)
        p.setPen(glyph)
        p.drawText(rect, Qt.AlignCenter, str(index + 1))

    # -- 点击切换当前步骤（基类无此交互，可选开启） ------------------------
    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self.clickable and self._steps:
            n = len(self._steps)
            pos = event.position()
            if self._orientation == Qt.Horizontal:
                idx = int(pos.x() // (self.width() / n))
            else:
                idx = int(pos.y() // max(56.0, self.height() / max(n, 1)))
            self.set_current(idx)
        super().mousePressEvent(event)


def _steps_pool(tr) -> list:
    """步骤条示例步骤池（标题, 描述）。"""
    return [(tr(f"steps.pool.{i}.title"), tr(f"steps.pool.{i}.desc"))
            for i in range(1, 6)]


def _steps_default_state() -> dict:
    """步骤条游乐场默认状态（显式状态 None = 按 current 推导）。"""
    return {
        "orientation": "horizontal",
        "current": 1,
        "count": 4,
        "status": {1: None, 2: "error"},  # 显式状态；None = 按 current 推导
        "node_radius": 12,
        "link_width": 2.0,
        "link_style": Qt.SolidLine,
        "clickable": True,
    }


def _steps_status_options(tr) -> list:
    """单步显式状态选项（自动 / 等待 / 进行 / 完成 / 错误）。"""
    return [(tr("steps.opt.auto"), None), (tr("steps.opt.wait"), "wait"),
            (tr("steps.opt.process"), "process"),
            (tr("steps.opt.finish"), "finish"),
            (tr("steps.opt.error"), "error")]


class _StepsDemo:
    """步骤条演示页的状态与构建逻辑（把游乐场闭包拆为方法以满足行数限制）。

    持有演示状态、步骤实例与当前步数 spin；``build`` 在方向 / 步骤数变化时
    重建 ``StepsEx`` 实例（orientation 为构造参数），面板回调经属性读写当前实例。
    """

    def __init__(self, tr):
        self._tr = tr
        self.state = _steps_default_state()
        self.pool = _steps_pool(tr)
        self.host = QWidget()
        self.host.setMinimumHeight(230)
        self.st: Optional[StepsEx] = None
        self.cur_spin = None

    def build(self) -> None:
        """方向 / 步骤数变化时重建实例（orientation 为构造参数）。"""
        state = self.state
        st = StepsEx(Qt.Horizontal if state["orientation"] == "horizontal"
                     else Qt.Vertical)
        st.node_radius = state["node_radius"]
        st.link_width = state["link_width"]
        st.link_style = state["link_style"]
        st.clickable = state["clickable"]
        st.set_steps(self.pool[:state["count"]])
        st.set_current(state["current"])
        self.st = st
        for idx, status in state["status"].items():
            if status and idx < state["count"]:
                st.set_status(idx, status)
        swap_widget(self.host, st, alignment=Qt.AlignmentFlag.AlignTop)
        self.cur_spin.setMaximum(state["count"] - 1)

    def apply_status(self, idx):
        """生成按索引注册单步显式状态的面板回调。"""
        def apply(v):
            self.state["status"][idx] = v
            if self.st is None or idx >= len(self.st._steps):
                return
            if v is None:  # 无公开「清除显式状态」API：属性赋值恢复自动推导
                self.st._steps[idx]["status"] = None
                self.st.update()
            else:
                self.st.set_status(idx, v)
        return apply

    def build_panel(self) -> PlaygroundPanel:
        """构建参数游乐场面板（注册顺序即面板展示顺序）。"""
        panel = PlaygroundPanel(self._tr("steps.panel_title"))
        self._register_structure_params(panel)
        self._register_node_params(panel)
        self._register_link_params(panel)
        self._register_clickable_param(panel)
        return panel

    def _register_structure_params(self, panel) -> None:
        """注册方向 / 当前步 / 步骤数 / 单步显式状态参数。"""
        tr, state = self._tr, self.state
        panel.add_choice(tr("steps.p.orientation"),
                         [(tr("steps.opt.horizontal"), "horizontal"),
                          (tr("steps.opt.vertical"), "vertical")],
                         "horizontal",
                         lambda v: (state.__setitem__("orientation", v), self.build()),
                         key="orientation")
        self.cur_spin = panel.add_int(
            tr("steps.p.current"), 1, 0, 3,
            lambda v: (state.__setitem__("current", v), self.st.set_current(v)),
            key="current")
        panel.add_int(tr("steps.p.count"), 4, 2, 5,
                      lambda v: (state.__setitem__("count", v), self.build()),
                      key="count")
        opts = _steps_status_options(tr)
        panel.add_choice(tr("steps.p.status2"), opts, None, self.apply_status(1),
                         key="status1")
        panel.add_choice(tr("steps.p.status3"), opts, "error", self.apply_status(2),
                         key="status2")

    def _register_node_params(self, panel) -> None:
        """注册节点半径参数。"""
        tr, state = self._tr, self.state
        panel.add_int(tr("steps.p.node_radius"), 12, 8, 16,
                      lambda v: (state.__setitem__("node_radius", v),
                                 setattr(self.st, "node_radius", v), self.st.update()),
                      key="node_radius")

    def _register_link_params(self, panel) -> None:
        """注册连接线样式与线宽参数。"""
        tr, state = self._tr, self.state
        panel.add_choice(tr("steps.p.link_style"),
                         [(tr("steps.opt.solid"), Qt.SolidLine),
                          (tr("steps.opt.dashed"), Qt.DashLine),
                          (tr("steps.opt.dotted"), Qt.DotLine)], Qt.SolidLine,
                         lambda v: (state.__setitem__("link_style", v),
                                    setattr(self.st, "link_style", v), self.st.update()),
                         key="link_style")
        panel.add_int(tr("steps.p.link_width"), 2, 1, 5,
                      lambda v: (state.__setitem__("link_width", float(v)),
                                 setattr(self.st, "link_width", float(v)),
                                 self.st.update()),
                      key="link_width")

    def _register_clickable_param(self, panel) -> None:
        """注册「点击节点切换当前步骤」开关。"""
        tr, state = self._tr, self.state
        panel.add_bool(tr("steps.p.clickable"), True,
                       lambda v: (state.__setitem__("clickable", v),
                                  setattr(self.st, "clickable", v)), key="clickable")


def create_steps_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """步骤条演示页：内联实例 + 参数游乐场（状态与构建逻辑见 ``_StepsDemo``）。"""
    tr = _tr_of(i18n)
    s = Section(tr("steps.sec"))
    demo = _StepsDemo(tr)
    panel = demo.build_panel()
    demo.build()
    s.layout().addWidget(with_playground(demo.host, panel))
    return make_page(tr("steps.title"), tr("steps.desc"), [s])


def create_alert_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("alert.sec"))
    s.layout().addWidget(Alert("info", tr("alert.info.title"), tr("alert.info.body")))
    s.layout().addWidget(Alert("success", tr("alert.success.title"),
                               tr("alert.success.body")))
    warn = Alert("warning", tr("alert.warning.title"), tr("alert.warning.body"),
                 closable=True)
    warn.add_action(tr("alert.warning.action"))
    s.layout().addWidget(warn)
    err = Alert("error", tr("alert.error.title"), tr("alert.error.body"), closable=True)
    err.add_action(tr("alert.error.action"))
    s.layout().addWidget(err)
    return make_page(tr("alert.title"), tr("alert.desc"), [s])


def create_dialog_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("dialog.sec"))
    btn1 = _primary(tr("dialog.btn.confirm"))
    btn1.clicked.connect(lambda: Dialog.confirm(
        btn1.window(), tr("dialog.confirm.title"), tr("dialog.confirm.body")))
    btn2 = QPushButton(tr("dialog.btn.info"))
    btn2.clicked.connect(lambda: Dialog.info(
        btn2.window(), tr("dialog.info.title"), tr("dialog.info.body")))
    s.layout().addWidget(row(btn1, btn2))
    s.layout().addWidget(hint_label(tr("dialog.hint"), role="tertiary"))
    return make_page(tr("dialog.title"), tr("dialog.desc"), [s])


def create_drawer_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("drawer.sec"))
    btns = []
    opened = []  # 已打开抽屉随页面实例持有（防止被 GC；页面销毁即释放）
    for pos in ("right", "left", "top", "bottom"):
        b = _primary(tr("drawer.btn", pos=pos))
        b.clicked.connect(lambda _=False, p=pos, bb=b: _open_drawer(bb, p, tr, opened))
        btns.append(b)
    s.layout().addWidget(row(*btns))
    s.layout().addWidget(hint_label(tr("drawer.hint"), role="tertiary"))
    page = make_page(tr("drawer.title"), tr("drawer.desc"), [s])
    page._keep_popups = opened
    return page


def _open_drawer(btn, position, tr, keep):
    """打开一个抽屉并登记到页面级持有列表（防止演示期间被 GC）。"""
    dr = Drawer(btn.window(), position=position, size=300,
                title=tr("drawer.btn", pos=position))
    dr.set_content(QLabel(tr("drawer.content", pos=position)))
    keep.append(dr)
    dr.open()


def create_notification_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("notification.sec"))
    btns = []
    for kind in ("success", "error", "info", "warning"):
        label = tr(f"notification.btn.{kind}")
        b = _primary(label) if kind in ("success", "error") else QPushButton(label)
        b.clicked.connect(lambda _=False, k=kind, bb=b: getattr(Notification, k)(
            bb.window(), tr("notification.msg_title", kind=k),
            tr("notification.body")))
        btns.append(b)
    s.layout().addWidget(row(*btns))
    s.layout().addWidget(hint_label(tr("notification.hint"), role="tertiary"))
    return make_page(tr("notification.title"), tr("notification.desc"), [s])


def create_message_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("message.sec"))
    btns = []
    for kind in ("success", "warning", "info", "error"):
        label = tr(f"message.btn.{kind}")
        b = _primary(label) if kind in ("success", "error") else QPushButton(label)
        b.clicked.connect(lambda _=False, k=kind, bb=b: getattr(Message, k)(
            bb.window(), tr("message.text", kind=k)))
        btns.append(b)
    s.layout().addWidget(row(*btns))
    s.layout().addWidget(hint_label(tr("message.hint"), role="tertiary"))
    return make_page(tr("message.title"), tr("message.desc"), [s])


def create_popconfirm_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("popconfirm.sec"))
    btn = _primary(tr("popconfirm.btn"))
    btn.clicked.connect(lambda: Popconfirm.confirm(btn, tr("popconfirm.text")))
    s.layout().addWidget(row(btn))
    s.layout().addWidget(hint_label(tr("popconfirm.hint"), role="tertiary"))
    return make_page(tr("popconfirm.title"), tr("popconfirm.desc"), [s])


def create_result_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("result.sec"))
    rv1 = ResultView("success", tr("result.success.title"), tr("result.success.sub"))
    rv1.add_action(tr("result.action.home"), variant="primary")
    rv1.add_action(tr("result.action.detail"))
    rv2 = ResultView("404", tr("result.notfound.title"), tr("result.notfound.sub"))
    rv2.add_action(tr("result.action.home"), variant="primary")
    rv3 = ResultView("error", tr("result.error.title"), tr("result.error.sub"))
    s.layout().addWidget(row(rv1, rv2, rv3, spacing=24))
    return make_page(tr("result.title"), tr("result.desc"), [s])


def create_skeleton_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("skeleton.sec"))
    sk = Skeleton(avatar=True, title=True, rows=3, button=True, active=True)
    sk.setMinimumWidth(420)
    s.layout().addWidget(sk)
    s.layout().addWidget(hint_label(tr("skeleton.hint"), role="tertiary"))
    return make_page(tr("skeleton.title"), tr("skeleton.desc"), [s])


def create_spinner_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("spinner.sec"))
    s.layout().addWidget(row(
        Spinner(size="sm", tip=tr("spinner.tip.loading")), Spinner(size="md"),
        Spinner(size="lg", tip=tr("spinner.tip.wait")), spacing=40))
    return make_page(tr("spinner.title"), tr("spinner.desc"), [s])


def create_progress_bar_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("progress_bar.sec"))
    bars = col(
        ProgressBar(45), ProgressBar(70, status="success"),
        ProgressBar(30, status="warning"), ProgressBar(55, status="error"))
    bars.setMinimumWidth(420)
    s.layout().addWidget(bars)
    s.layout().addWidget(row(
        CircleProgress(75), CircleProgress(45, status="success"),
        CircleProgress(90, status="error"), spacing=32))
    return make_page(tr("progress_bar.title"), tr("progress_bar.desc"), [s])


def create_tour_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("tour.sec"))
    target1 = _primary(tr("tour.target.a"))
    target2 = QPushButton(tr("tour.target.b"))
    start = _primary(tr("tour.btn.start"))
    opened = []  # 引导层实例随页面持有（防止被 GC；页面销毁即释放）

    def _start():
        tour = Tour(start.window())
        tour.add_step(target1, tr("tour.step.1.title"), tr("tour.step.1.body"))
        tour.add_step(target2, tr("tour.step.2.title"), tr("tour.step.2.body"))
        opened.append(tour)
        tour.start()

    start.clicked.connect(_start)
    s.layout().addWidget(row(target1, target2, start))
    s.layout().addWidget(hint_label(tr("tour.hint"), role="tertiary"))
    page = make_page(tr("tour.title"), tr("tour.desc"), [s])
    page._keep_popups = opened
    return page


#: 反馈组件页注册表：(导航键, 页面工厂)；标题由 MainWidget 经 ``nav:page.<键>`` 取词
FEEDBACK_PAGES = [
    ("tabs", create_tabs_page),
    ("anchor", create_anchor_page),
    ("breadcrumb", create_breadcrumb_page),
    ("dropdown", create_dropdown_page),
    ("nav_menu", create_nav_menu_page),
    ("page_header", create_page_header_page),
    ("pagination", create_pagination_page),
    ("steps", create_steps_page),
    ("alert", create_alert_page),
    ("dialog", create_dialog_page),
    ("drawer", create_drawer_page),
    ("notification", create_notification_page),
    ("message", create_message_page),
    ("popconfirm", create_popconfirm_page),
    ("result", create_result_page),
    ("skeleton", create_skeleton_page),
    ("spinner", create_spinner_page),
    ("progress_bar", create_progress_bar_page),
    ("tour", create_tour_page),
]
