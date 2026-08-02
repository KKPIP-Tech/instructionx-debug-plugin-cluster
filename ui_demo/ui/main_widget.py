# -*- coding: utf-8 -*-
"""UI Demo 插件主控件：左侧导航树 + 右侧演示页堆叠。

布局与交互以 InstructionX_UIKit 仓库 ``demo/main_window.py`` 为基准：
- 左侧 ``QTreeWidget`` 按 ``pages.NAV`` 注册表构建「分类 → 页面」两级导航；
- 右侧 ``QStackedWidget`` 懒加载并缓存演示页；
- 不提供主题切换入口——全局主题由框架统一管理，页面经 ``T()`` 令牌自动跟随。
"""

import json
from pathlib import Path

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
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._ui_config = _load_ui_config()
        self._page_cache: dict = {}
        self._build_layout()
        self._select_first_page()

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
        for _cat_key, cat_title, pages in NAV:
            cat_item = self._make_category_item(cat_title, cat_font)
            for page_key, page_title, factory in pages:
                self._add_page_item(cat_item, page_key, page_title, factory)
            cat_item.setExpanded(True)
        self._tree.currentItemChanged.connect(self._on_nav)
        return self._tree

    def _make_category_item(self, title: str, font: QFont) -> QTreeWidgetItem:
        """创建不可选的分类节点并加入树根部。"""
        item = QTreeWidgetItem([title])
        item.setFont(0, font)
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        self._tree.addTopLevelItem(item)
        return item

    @staticmethod
    def _add_page_item(cat_item: QTreeWidgetItem, key: str, title: str, factory) -> None:
        """在分类节点下挂载页面叶子节点（UserRole 存页面键与工厂）。"""
        child = QTreeWidgetItem([title])
        child.setData(0, Qt.UserRole, (key, factory))
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
            factory: 页面工厂，遵循 ``create_page() -> QWidget`` 约定。
        """
        if page_key not in self._page_cache:
            page = factory()
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
