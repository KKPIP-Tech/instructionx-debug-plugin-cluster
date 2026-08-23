# -*- coding: utf-8 -*-
"""布局演示的示例数据与卡片构建器（Demo 程序专用）。

InstructionX_UIKit 的 12 个布局预设全部为 API 驱动、不含任何假数据；
本模块集中存放演示用的示例内容（原是布局内置的占位数据，已迁入
Demo），``layouts.py`` 各演示页从这里取数据并传给布局。

多语言：模块级数据常量全部改为 ``xxx(tr)`` 构建函数（``tr`` 由
``common.bind_tr`` 绑定 ``layout_samples`` 分组），语言切换时页面重建
即以新语言取数。

同时，每个布局给出 ``USAGE`` 单行调用示例（代码即文档，不翻译），
演示页顶部以灰字代码标签展示，开发者照此即可用 Kit 复现相同效果。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.theme import T, ThemeManager
from InstructionX_UIKit.layouts.helpers import (
    TokenColorChip,
    apply_token_font,
    titled_card,
)

# ---------------------------------------------------------------------------
# 各布局的单行用法示例（演示页顶部灰字代码标签；代码即文档，不翻译）
# ---------------------------------------------------------------------------

USAGE = {
    "top_nav_bar": 'create_top_nav_bar(brand="控制台", menu_items=[...], cards=[(标题, 描述, 色块键), ...])',
    "holy_grail": 'create_holy_grail(title="圣杯布局", nav_items=[...], center=widget, side=widget)',
    "card_grid": 'create_card_grid(items=[("数据看板", "描述", "color.primary.subtle"), ...])',
    "single_column": 'create_single_column(title=..., subtitle=..., paragraphs=[...], actions=[(文本, variant)])',
    "sidebar_layout": 'create_sidebar_layout(brand="控制台", nav_items=[(图标名, 文本)], content=widget)',
    "master_detail": 'create_master_detail(items=[(标题, 摘要, 正文)], title="收件箱")',
    "split_panel": 'create_split_panel(nav_items=[...], list_items=[...], content=widget)',
    "dashboard_grid": 'create_dashboard_grid(cards=[card × 9])  # 依次占 3/3/3/3/8/4/6/6/12 列跨度',
    "hero_section": 'create_hero_section(kicker=..., title=..., primary_text="开始使用", secondary_text="查看文档")',
    "centered_container": 'create_centered_container(title=..., actions=[...], cards=[(标题, 描述, 色块键)])',
    "waterfall": 'create_waterfall(items=[(标题, 色块键, 档位2-6), ...])',
    "media_left_right": 'create_media_left_right(sections=[(标题, 正文, 色块键)], link_text="了解更多")',
}

# ---------------------------------------------------------------------------
# 顶部导航栏
# ---------------------------------------------------------------------------

def top_nav_bar(tr) -> dict:
    """顶部导航栏布局示例数据。"""
    return dict(
        brand=tr("tnb.brand"),
        menu_items=tuple(tr(f"tnb.menu.{k}") for k in
                         ("home", "products", "docs", "community", "about")),
        search_placeholder=tr("tnb.search_placeholder"),
        user_text=tr("tnb.user_text"),
        title=tr("tnb.title"),
        subtitle=tr("tnb.subtitle"),
        cards=tuple(
            (tr(f"tnb.card.{i}.title"), tr(f"tnb.card.{i}.desc"), key)
            for i, key in enumerate(
                ("color.primary.subtle", "color.success.subtle",
                 "color.warning.subtle", "color.danger.subtle"), start=1)),
    )

# ---------------------------------------------------------------------------
# 圣杯布局
# ---------------------------------------------------------------------------

def holy_grail(tr) -> dict:
    """圣杯布局示例数据。"""
    return dict(
        title=tr("hg.title"),
        nav_items=tuple(tr(f"hg.nav.{i}") for i in range(1, 6)),
        header_actions=(tr("hg.action.refresh"), tr("hg.action.settings")),
        footer_note=tr("hg.footer_note"),
        status=tr("hg.status"),
    )


def build_holy_grail_center(tr) -> QWidget:
    """圣杯布局主内容区示例：标题 + 色块 + 说明段落。"""
    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(T("space.2"), T("space.2"), T("space.2"), T("space.2"))
    lay.setSpacing(T("space.3"))
    title = QLabel(tr("hg.center.title"))
    apply_token_font(title, "font.title.md", "font.weight.semibold")
    lay.addWidget(title)
    chip = TokenColorChip("color.primary.subtle", "radius.md")
    chip.setMinimumHeight(T("space.16") * 2)
    lay.addWidget(chip)
    for text in (tr("hg.center.para.1"), tr("hg.center.para.2")):
        para = QLabel(text)
        para.setProperty("role", "secondary")
        para.setWordWrap(True)
        lay.addWidget(para)
    lay.addStretch(1)
    return panel


def build_holy_grail_side(tr) -> QWidget:
    """圣杯布局右侧栏示例：相关信息列表。"""
    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(T("space.2"))
    head = QLabel(tr("hg.side.head"))
    apply_token_font(head, "font.sm", "font.weight.semibold")
    head.setProperty("role", "tertiary")
    lay.addWidget(head)
    listing = QListWidget()
    listing.addItems(tr(f"hg.side.item.{i}") for i in range(1, 5))
    lay.addWidget(listing, 1)
    return panel

# ---------------------------------------------------------------------------
# 卡片网格
# ---------------------------------------------------------------------------

def card_grid_items(tr) -> tuple:
    """示例卡片数据（标题、描述、色块令牌）。"""
    color_keys = ("color.primary.subtle", "color.success.subtle",
                  "color.warning.subtle", "color.danger.subtle")
    return tuple(
        (tr(f"cg.card.{i}.title"), tr(f"cg.card.{i}.desc"), color_keys[(i - 1) % 4])
        for i in range(1, 9))

# ---------------------------------------------------------------------------
# 单列堆叠
# ---------------------------------------------------------------------------

def single_column(tr) -> dict:
    """单列堆叠布局示例数据。"""
    return dict(
        kicker=tr("sc.kicker"),
        title=tr("sc.title"),
        subtitle=tr("sc.subtitle"),
        cover_key="color.primary.subtle",
        paragraphs=tuple(tr(f"sc.para.{i}") for i in range(1, 4)),
        quote=tr("sc.quote"),
        actions=((tr("sc.action.read"), "primary"), (tr("sc.action.fav"), "default")),
    )

# ---------------------------------------------------------------------------
# 侧边栏布局
# ---------------------------------------------------------------------------

def sidebar_nav_items(tr) -> tuple:
    """导航项示例：（图标名, 文本），图标取自 InstructionX_UIKit.icons。"""
    return tuple((icon, tr(f"sb.nav.{icon}")) for icon in
                 ("home", "component", "chart", "layout", "animation", "settings"))


def _stat_card(title, value, note):
    """构造内容区顶部的统计卡片。"""
    card = QFrame()
    card.setFrameShape(QFrame.StyledPanel)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(T("space.4"), T("space.3"), T("space.4"), T("space.3"))
    lay.setSpacing(T("space.1"))
    head = QLabel(title)
    head.setProperty("role", "secondary")
    lay.addWidget(head)
    number = QLabel(value)
    apply_token_font(number, "font.display", "font.weight.bold")
    lay.addWidget(number)
    foot = QLabel(note)
    foot.setProperty("role", "tertiary")
    apply_token_font(foot, "font.sm")
    lay.addWidget(foot)
    return card


def _sidebar_stats(tr) -> QGridLayout:
    """内容区顶部三张统计卡片。"""
    stats = QGridLayout()
    stats.setSpacing(T("space.4"))
    stats.addWidget(_stat_card(tr("sb.stat.users.title"), "12,846",
                               tr("sb.stat.users.note")), 0, 0)
    stats.addWidget(_stat_card(tr("sb.stat.projects.title"), "36",
                               tr("sb.stat.projects.note")), 0, 1)
    stats.addWidget(_stat_card(tr("sb.stat.todo.title"), "9",
                               tr("sb.stat.todo.note")), 0, 2)
    return stats


def _sidebar_panel(tr) -> QFrame:
    """内容区主体面板：色块 + 说明。"""
    panel = QFrame()
    panel.setFrameShape(QFrame.StyledPanel)
    panel_lay = QVBoxLayout(panel)
    panel_lay.setContentsMargins(T("space.4"), T("space.4"), T("space.4"), T("space.4"))
    panel_lay.setSpacing(T("space.2"))
    chip = TokenColorChip("color.primary.subtle", "radius.md")
    chip.setMinimumHeight(T("space.16") * 2)
    panel_lay.addWidget(chip)
    note = QLabel(tr("sb.panel.note"))
    note.setProperty("role", "secondary")
    note.setWordWrap(True)
    panel_lay.addWidget(note)
    return panel


def build_sidebar_content(tr) -> QWidget:
    """侧边栏布局内容区示例：面包屑 + 标题 + 统计卡 + 内容面板。"""
    content = QWidget()
    lay = QVBoxLayout(content)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(T("space.4"))

    crumb = QLabel(tr("sb.crumb"))
    crumb.setProperty("role", "tertiary")
    apply_token_font(crumb, "font.sm")
    lay.addWidget(crumb)
    title = QLabel(tr("sb.title"))
    apply_token_font(title, "font.title.lg", "font.weight.semibold")
    lay.addWidget(title)
    lay.addLayout(_sidebar_stats(tr))
    lay.addWidget(_sidebar_panel(tr), 1)
    return content

# ---------------------------------------------------------------------------
# 列表-详情
# ---------------------------------------------------------------------------

def master_detail(tr) -> dict:
    """列表-详情布局示例数据（条目：标题, 摘要, 详情正文）。"""
    items = tuple(
        (tr(f"md.item.{i}.title"), tr(f"md.item.{i}.summary"), tr(f"md.item.{i}.body"))
        for i in range(1, 6))
    return dict(
        items=items,
        title=tr("md.title"),
        actions=((tr("md.action.read"), "primary"), (tr("md.action.archive"), "default")),
    )

# ---------------------------------------------------------------------------
# 分栏面板
# ---------------------------------------------------------------------------

def split_panel(tr) -> dict:
    """分栏面板布局示例数据。"""
    return dict(
        nav_items=tuple(tr(f"sp.nav.{i}") for i in range(1, 5)),
        list_items=tuple(tr(f"sp.list.{i}") for i in range(1, 7)),
    )


def build_split_panel_content(tr) -> QWidget:
    """分栏面板内容区示例：标题 + 色块 + 说明。"""
    panel = QWidget()
    lay = QVBoxLayout(panel)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(T("space.3"))
    title = QLabel(tr("sp.content.title"))
    apply_token_font(title, "font.title.md", "font.weight.semibold")
    lay.addWidget(title)
    chip = TokenColorChip("color.primary.subtle", "radius.md")
    chip.setMinimumHeight(T("space.16") + T("space.8"))
    lay.addWidget(chip)
    note = QLabel(tr("sp.content.note"))
    note.setProperty("role", "secondary")
    note.setWordWrap(True)
    lay.addWidget(note)
    lay.addStretch(1)
    return panel

# ---------------------------------------------------------------------------
# 仪表盘网格
# ---------------------------------------------------------------------------

#: 示例柱状图相对高度（0~1）
_DEMO_BAR_VALUES = (0.45, 0.70, 0.55, 0.90, 0.62, 0.80, 0.50, 0.66)


class _DemoBarChart(QWidget):
    """主题感知示例柱状图（Demo 数据）：自绘，paintEvent 实时取令牌色。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(T("space.16") * 2)
        ThemeManager.instance().theme_changed.connect(self.update)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        gap = T("space.2")
        radius = T("radius.sm")
        count = len(_DEMO_BAR_VALUES)
        bar_w = max(T("space.1"), (self.width() - gap * (count + 1)) // count)
        for i, ratio in enumerate(_DEMO_BAR_VALUES):
            bar_h = int((self.height() - T("space.2")) * ratio)
            x = gap + i * (bar_w + gap)
            painter.setBrush(QColor(T("color.primary")))
            painter.drawRoundedRect(x, self.height() - bar_h, bar_w, bar_h, radius, radius)


def _dash_stat_cards(tr) -> list:
    """仪表盘前 4 张统计卡片（依次占 3/3/3/3 列跨度）。"""
    cards = []
    specs = (("users", "24,317"), ("projects", "142"),
             ("revenue", "¥86,400"), ("alerts", "3"))
    for name, value in specs:
        card, lay = titled_card(tr(f"db.stat.{name}.title"))
        number = QLabel(value)
        apply_token_font(number, "font.display", "font.weight.bold")
        lay.addWidget(number)
        foot = QLabel(tr(f"db.stat.{name}.note"))
        foot.setProperty("role", "secondary")
        apply_token_font(foot, "font.sm")
        lay.addWidget(foot)
        lay.addStretch(1)
        cards.append(card)
    return cards


def _dash_feed_card(tr) -> QFrame:
    """「最新动态」卡片（8 列跨度）。"""
    card, lay = titled_card(tr("db.feed.title"))
    for i in range(1, 5):
        line = QHBoxLayout()
        line.setSpacing(T("space.2"))
        dot = TokenColorChip("color.primary", "radius.pill")
        dot.setFixedSize(T("space.2"), T("space.2"))
        line.addWidget(dot, 0, Qt.AlignVCenter)
        label = QLabel(tr(f"db.feed.{i}"))
        label.setProperty("role", "secondary")
        line.addWidget(label, 1)
        lay.addLayout(line)
    lay.addStretch(1)
    return card


def _dash_quota_card(tr) -> QFrame:
    """「资源用量」卡片（6 列跨度）。"""
    card, lay = titled_card(tr("db.quota.title"))
    for name_key, value in (("storage", 65), ("compute", 42)):
        label = QLabel(tr(f"db.quota.{name_key}"))
        label.setProperty("role", "secondary")
        lay.addWidget(label)
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(value)
        lay.addWidget(bar)
    lay.addStretch(1)
    return card


def _dash_todo_card(tr) -> QFrame:
    """「本周待办」卡片（6 列跨度）。"""
    card, lay = titled_card(tr("db.todo.title"))
    for i in range(1, 4):
        label = QLabel(f"· {tr(f'db.todo.{i}')}")
        label.setProperty("role", "secondary")
        lay.addWidget(label)
    lay.addStretch(1)
    return card


def _dash_banner_card(tr) -> QFrame:
    """「公告」卡片（12 列跨度）。"""
    card, lay = titled_card(tr("db.banner.title"))
    banner = QLabel(tr("db.banner.text"))
    banner.setProperty("role", "secondary")
    banner.setWordWrap(True)
    lay.addWidget(banner)
    return card


def build_dashboard_cards(tr) -> list:
    """构建仪表盘 9 张示例卡片（依次对应 3/3/3/3/8/4/6/6/12 列跨度）。"""
    cards = _dash_stat_cards(tr)
    chart_card, chart_lay = titled_card(tr("db.chart.title"))
    chart_lay.addWidget(_DemoBarChart(), 1)
    cards.append(chart_card)
    cards.append(_dash_feed_card(tr))
    cards.append(_dash_quota_card(tr))
    cards.append(_dash_todo_card(tr))
    cards.append(_dash_banner_card(tr))
    return cards

# ---------------------------------------------------------------------------
# 英雄区
# ---------------------------------------------------------------------------

def hero_section(tr) -> dict:
    """英雄区布局示例数据。"""
    return dict(
        kicker=tr("hero.kicker"),
        title=tr("hero.title"),
        subtitle=tr("hero.subtitle"),
        primary_text=tr("hero.primary"),
        secondary_text=tr("hero.secondary"),
        hint=tr("hero.hint"),
    )

# ---------------------------------------------------------------------------
# 居中容器
# ---------------------------------------------------------------------------

def centered_container(tr) -> dict:
    """居中容器布局示例数据。"""
    color_keys = ("color.primary", "color.success", "color.warning")
    cards = tuple(
        (tr(f"cc.card.{i}.title"), tr(f"cc.card.{i}.desc"), color_keys[(i - 1) % 3])
        for i in range(1, 7))
    return dict(
        title=tr("cc.title"),
        subtitle=tr("cc.subtitle"),
        actions=((tr("cc.action.save"), "primary"), (tr("cc.action.cancel"), "default")),
        cards=cards,
        note=tr("cc.note"),
    )

# ---------------------------------------------------------------------------
# 瀑布流
# ---------------------------------------------------------------------------

def waterfall_items(tr) -> tuple:
    """示例卡片：（标题, 色块令牌, 内容量档位 2-6, 元信息）。"""
    color_keys = ("color.primary.subtle", "color.success.subtle",
                  "color.warning.subtle", "color.danger.subtle")
    ratios = (3, 5, 2, 4, 6, 3, 5, 2, 4, 6, 3, 5)
    return tuple(
        (tr(f"wf.item.{i}"), color_keys[(i - 1) % 4], ratios[i - 1],
         tr("wf.meta", n=f"{i:02d}"))
        for i in range(1, 13))

# ---------------------------------------------------------------------------
# 图文左右
# ---------------------------------------------------------------------------

def media_left_right(tr) -> dict:
    """图文左右布局示例数据。"""
    color_keys = ("color.primary.subtle", "color.success.subtle",
                  "color.warning.subtle")
    sections = tuple(
        (tr(f"ml.section.{i}.title"), tr(f"ml.section.{i}.body"), color_keys[i - 1])
        for i in range(1, 4))
    return dict(sections=sections, link_text=tr("ml.link"))
