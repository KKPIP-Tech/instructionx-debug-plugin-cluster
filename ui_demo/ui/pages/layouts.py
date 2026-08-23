# -*- coding: utf-8 -*-
"""布局预设演示页：12 个布局预设，每页以实尺寸嵌入对应布局。

布局本身（InstructionX_UIKit.layouts）为 API 驱动、不含假数据；
本页负责生成示例内容（见 ``layout_samples.py``，数据经 ``tr`` 取词）
并传入布局。每个演示页顶部有「用法」分区，展示该布局的单行调用示例，
开发者照此即可用 Kit 复现相同效果。
"""

from typing import Optional

from PySide6.QtWidgets import QFrame, QWidget

from InstructionX_UIKit.layouts.card_grid import create_card_grid
from InstructionX_UIKit.layouts.centered_container import create_centered_container
from InstructionX_UIKit.layouts.dashboard_grid import create_dashboard_grid
from InstructionX_UIKit.layouts.hero_section import create_hero_section
from InstructionX_UIKit.layouts.holy_grail import create_holy_grail
from InstructionX_UIKit.layouts.master_detail import create_master_detail
from InstructionX_UIKit.layouts.media_left_right import create_media_left_right
from InstructionX_UIKit.layouts.sidebar_layout import create_sidebar_layout
from InstructionX_UIKit.layouts.single_column import create_single_column
from InstructionX_UIKit.layouts.split_panel import create_split_panel
from InstructionX_UIKit.layouts.top_nav_bar import create_top_nav_bar
from InstructionX_UIKit.layouts.waterfall import create_waterfall

from core.interfaces import ILocalizationFacade

from . import layout_samples as samples
from .common import Section, bind_tr, make_page, usage_section


def _build_top_nav_bar(tr) -> QWidget:
    return create_top_nav_bar(**samples.top_nav_bar(tr))


def _build_holy_grail(tr) -> QWidget:
    return create_holy_grail(
        **samples.holy_grail(tr),
        center=samples.build_holy_grail_center(tr),
        side=samples.build_holy_grail_side(tr),
    )


def _build_card_grid(tr) -> QWidget:
    return create_card_grid(items=samples.card_grid_items(tr))


def _build_single_column(tr) -> QWidget:
    return create_single_column(**samples.single_column(tr))


def _build_sidebar_layout(tr) -> QWidget:
    return create_sidebar_layout(
        brand=tr("sidebar.brand"),
        nav_items=samples.sidebar_nav_items(tr),
        content=samples.build_sidebar_content(tr),
    )


def _build_master_detail(tr) -> QWidget:
    return create_master_detail(**samples.master_detail(tr))


def _build_split_panel(tr) -> QWidget:
    return create_split_panel(
        **samples.split_panel(tr),
        content=samples.build_split_panel_content(tr),
    )


def _build_dashboard_grid(tr) -> QWidget:
    return create_dashboard_grid(cards=samples.build_dashboard_cards(tr))


def _build_hero_section(tr) -> QWidget:
    return create_hero_section(**samples.hero_section(tr))


def _build_centered_container(tr) -> QWidget:
    return create_centered_container(**samples.centered_container(tr))


def _build_waterfall(tr) -> QWidget:
    return create_waterfall(items=samples.waterfall_items(tr))


def _build_media_left_right(tr) -> QWidget:
    return create_media_left_right(**samples.media_left_right(tr))


#: (导航键, 布局工厂, 预览高度)；标题 / 说明经 ``<键>.title`` / ``<键>.desc`` 取词
_LAYOUTS = [
    ("top_nav_bar", _build_top_nav_bar, 520),
    ("holy_grail", _build_holy_grail, 560),
    ("card_grid", _build_card_grid, 560),
    ("single_column", _build_single_column, 560),
    ("sidebar_layout", _build_sidebar_layout, 560),
    ("master_detail", _build_master_detail, 560),
    ("split_panel", _build_split_panel, 560),
    ("dashboard_grid", _build_dashboard_grid, 640),
    ("hero_section", _build_hero_section, 480),
    ("centered_container", _build_centered_container, 560),
    ("waterfall", _build_waterfall, 640),
    ("media_left_right", _build_media_left_right, 640),
]


def _embed(key: str, factory, height: int, tr, tr_samples) -> QFrame:
    """把布局以实尺寸嵌入一个分区容器（顶部附「用法」代码标签）。

    布局示例内容由 ``layout_samples`` 模块按 ``layout_samples`` 分组取词，
    故工厂接收 ``tr_samples``；本页自身的标题 / 说明用 ``layouts`` 分组。
    """
    box = Section(tr("preview.title"))
    widget = factory(tr_samples)
    widget.setMinimumHeight(height)
    box.layout().addWidget(widget)
    return box


def _make(key: str, i18n: Optional[ILocalizationFacade]) -> QWidget:
    tr = bind_tr(i18n, "layouts")
    tr_samples = bind_tr(i18n, "layout_samples")
    for k, factory, height in _LAYOUTS:
        if k == key:
            return make_page(tr(f"{key}.title"), tr(f"{key}.desc"), [
                usage_section(samples.USAGE[key], i18n),
                _embed(key, factory, height, tr, tr_samples),
            ])
    raise KeyError(f"未知布局: {key}")


# 逐个页面工厂（create_page(i18n=None) -> QWidget 契约：每布局一个演示页）----

def create_top_nav_bar_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("top_nav_bar", i18n)


def create_holy_grail_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("holy_grail", i18n)


def create_card_grid_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("card_grid", i18n)


def create_single_column_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("single_column", i18n)


def create_sidebar_layout_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("sidebar_layout", i18n)


def create_master_detail_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("master_detail", i18n)


def create_split_panel_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("split_panel", i18n)


def create_dashboard_grid_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("dashboard_grid", i18n)


def create_hero_section_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("hero_section", i18n)


def create_centered_container_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("centered_container", i18n)


def create_waterfall_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("waterfall", i18n)


def create_media_left_right_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    return _make("media_left_right", i18n)


#: 布局页注册表：(导航键, 页面工厂)；标题由 MainWidget 经 ``nav:page.<键>`` 取词
LAYOUT_PAGES = [
    ("top_nav_bar", create_top_nav_bar_page),
    ("holy_grail", create_holy_grail_page),
    ("card_grid", create_card_grid_page),
    ("single_column", create_single_column_page),
    ("sidebar_layout", create_sidebar_layout_page),
    ("master_detail", create_master_detail_page),
    ("split_panel", create_split_panel_page),
    ("dashboard_grid", create_dashboard_grid_page),
    ("hero_section", create_hero_section_page),
    ("centered_container", create_centered_container_page),
    ("waterfall", create_waterfall_page),
    ("media_left_right", create_media_left_right_page),
]
