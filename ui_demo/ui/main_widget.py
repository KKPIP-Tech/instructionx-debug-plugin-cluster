# -*- coding: utf-8 -*-
"""UI Demo 插件主控件：左侧导航树 + 右侧演示页堆叠。

布局与交互以 InstructionX_UIKit 仓库 ``demo/main_window.py`` 为基准：
- 左侧 ``QTreeWidget`` 按 ``pages.NAV`` 注册表构建「分类 → 页面」两级导航；
- 右侧 ``QStackedWidget`` 懒加载并缓存演示页；
- 不提供主题切换入口——全局主题由框架统一管理，页面经 ``T()`` 令牌自动跟随。

多语言：导航标题与全部演示页经 ``ILocalizationFacade`` 取词（分组 ``nav`` /
各页面分组）；语言切换（框架语言或本插件语言覆盖）时重设导航文案、
清空页面缓存并以新语言重建当前页（演示页为构建期取词，重建即刷新）。
"""

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.i18n import get_language_manager
from core.interfaces import ILocalizationFacade

from .pages import NAV

# 插件配置文件（布局参数唯一来源，缺失/损坏时回退到内置默认值）
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "default.json"

#: 内置默认布局参数（与 config/default.json 保持一致）
_DEFAULT_UI_CONFIG = {
    "nav_min_width": 200,
    "nav_max_width": 320,
    "nav_default_width": 240,
    "nav_indent": 16,
}

#: 树节点数据角色：UserRole 存 (页面键, 工厂)；UserRole+1 存取词键后缀
_KEY_ROLE = Qt.UserRole + 1


def _load_ui_config() -> dict:
    """读取 config/default.json 的 ui 段，失败时回退内置默认值。"""
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(_DEFAULT_UI_CONFIG)
    ui = data.get("ui")
    if not isinstance(ui, dict):
        return dict(_DEFAULT_UI_CONFIG)
    merged = dict(_DEFAULT_UI_CONFIG)
    merged.update({k: v for k, v in ui.items() if k in merged})
    return merged


class MainWidget(QWidget):
    """UIKit 组件橱窗主控件。

    职责：依据 ``pages.NAV`` 注册表构建导航树，按需创建并缓存演示页。
    页面内容全部来自 ``ui/pages/``（移植自 UIKit 仓库 Demo），本类不含演示逻辑。

    参数:
        parent: 父控件。
        i18n: 取词门面（可为 None，降级显示键名）。
        plugin_id: 插件 UUID（用于甄别 ``plugin_language_changed`` 信号归属）。
    """

    def __init__(self, parent: QWidget | None = None,
                 i18n: Optional[ILocalizationFacade] = None,
                 plugin_id: Optional[str] = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._plugin_id = plugin_id
        self._ui_config = _load_ui_config()
        self._page_cache: dict = {}
        self._current_key: Optional[str] = None
        self._build_layout()
        self._select_first_page()
        self._connect_language_signals()

    # ------------------------------------------------------------------ 取词
    def _tr(self, key: str, /, **params) -> str:
        """取导航分组文案；门面未注入时优雅降级返回键名。"""
        if self._i18n is None:
            return key
        return self._i18n.tr("nav", key, **params)

    def _connect_language_signals(self) -> None:
        """监听框架 / 本插件语言变化（门面未注入时不监听，无需刷新）。"""
        if self._i18n is None:
            return
        manager = get_language_manager()
        manager.language_changed.connect(self._retranslate_ui)
        manager.plugin_language_changed.connect(self._on_plugin_language_changed)

    # ------------------------------------------------------------------ 布局
    def _build_layout(self) -> None:
        """构建「导航树 | 页面堆叠」二分栏布局。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_nav())
        splitter.addWidget(self._build_stack())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        default_width = self._ui_config["nav_default_width"]
        splitter.setSizes([default_width, 1040 - default_width])
        splitter.setCollapsible(1, False)
        root.addWidget(splitter, 1)

    def _build_nav(self) -> QTreeWidget:
        """从 NAV 注册表构建两级导航树（分类不可选、默认展开）。"""
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.setMinimumWidth(self._ui_config["nav_min_width"])
        self._tree.setMaximumWidth(self._ui_config["nav_max_width"])
        self._tree.setIndentation(self._ui_config["nav_indent"])
        cat_font = QFont()
        cat_font.setWeight(QFont.Weight(QFont.Bold))
        for cat_key, pages in NAV:
            cat_item = self._make_category_item(cat_key, cat_font)
            for page_key, factory in pages:
                self._add_page_item(cat_item, page_key, factory)
            cat_item.setExpanded(True)
        self._tree.currentItemChanged.connect(self._on_nav)
        return self._tree

    def _make_category_item(self, cat_key: str, font: QFont) -> QTreeWidgetItem:
        """创建不可选的分类节点并加入树根部（标题经门面取词）。"""
        item = QTreeWidgetItem([self._tr(f"cat.{cat_key}")])
        item.setFont(0, font)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        item.setData(0, _KEY_ROLE, cat_key)
        self._tree.addTopLevelItem(item)
        return item

    def _add_page_item(self, cat_item: QTreeWidgetItem, key: str, factory) -> None:
        """在分类节点下挂载页面叶子节点（UserRole 存页面键与工厂）。"""
        child = QTreeWidgetItem([self._tr(f"page.{key}")])
        child.setData(0, Qt.UserRole, (key, factory))
        child.setData(0, _KEY_ROLE, key)
        cat_item.addChild(child)

    def _build_stack(self) -> QStackedWidget:
        """创建右侧演示页堆叠容器。"""
        self._stack = QStackedWidget()
        return self._stack

    # ------------------------------------------------------------------ 导航
    def _select_first_page(self) -> None:
        """默认选中第一个分类下的第一个页面。"""
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            if cat.childCount():
                self._tree.setCurrentItem(cat.child(0))
                return

    def _on_nav(self, current: QTreeWidgetItem | None, _previous) -> None:
        """导航切换：分类头跳到首个子页，叶子节点加载对应演示页。"""
        if current is None:
            return
        data = current.data(0, Qt.UserRole)
        if data is None:
            if current.childCount():
                self._tree.setCurrentItem(current.child(0))
            return
        page_key, factory = data
        self.show_page(page_key, factory)

    def show_page(self, page_key: str, factory) -> None:
        """懒加载并切换到指定演示页（公开，供遍历验证调用）。

        Args:
            page_key: 页面唯一键（NAV 注册表第一项）。
            factory: 页面工厂，遵循 ``create_page(i18n=None) -> QWidget`` 约定。
        """
        self._current_key = page_key
        if page_key not in self._page_cache:
            page = factory(self._i18n)
            self._page_cache[page_key] = page
            self._stack.addWidget(page)
        self._stack.setCurrentWidget(self._page_cache[page_key])

    def nav_leaves(self) -> list:
        """返回 [(page_key, page_title, tree_item)]，覆盖导航树全部叶子页。"""
        leaves = []
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                key, _factory = child.data(0, Qt.UserRole)
                leaves.append((key, child.text(0), child))
        return leaves

    # ------------------------------------------------------------------ 语言切换
    def _on_plugin_language_changed(self, plugin_id: str, _language: str) -> None:
        """插件语言覆盖变化：仅当属于本插件时刷新。"""
        if self._plugin_id is not None and plugin_id != self._plugin_id:
            return
        self._retranslate_ui()

    def _retranslate_ui(self, *_args) -> None:
        """重设导航文案并清空页面缓存，以当前语言重建当前页。"""
        self._retranslate_nav()
        for page in self._page_cache.values():
            self._stack.removeWidget(page)
            page.deleteLater()
        self._page_cache.clear()
        self._reselect_current_page()

    def _retranslate_nav(self) -> None:
        """按当前语言重设导航树全部分类 / 页面标题。"""
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            cat.setText(0, self._tr(f"cat.{cat.data(0, _KEY_ROLE)}"))
            for j in range(cat.childCount()):
                child = cat.child(j)
                child.setText(0, self._tr(f"page.{child.data(0, _KEY_ROLE)}"))

    def _reselect_current_page(self) -> None:
        """缓存清空后重新选中并重建当前页（找不到则回退第一页）。"""
        item = self._find_leaf(self._current_key)
        if item is None:
            self._select_first_page()
            return
        self._tree.setCurrentItem(item)
        data = item.data(0, Qt.UserRole)
        if data is not None:
            self.show_page(data[0], data[1])

    def _find_leaf(self, page_key: Optional[str]) -> QTreeWidgetItem | None:
        """按页面键查找导航树叶子节点。"""
        if page_key is None:
            return None
        for i in range(self._tree.topLevelItemCount()):
            cat = self._tree.topLevelItem(i)
            for j in range(cat.childCount()):
                child = cat.child(j)
                if child.data(0, _KEY_ROLE) == page_key:
                    return child
        return None
