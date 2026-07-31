# -*- coding: utf-8 -*-
"""节点列表面板（ui 层）。

以清单形式展示画布全部节点实例（状态色点 + 标题 + 类型名），
并提供「定位 / 重命名 / 删除」管理操作。只调用
``BlueprintGraph`` / ``BlueprintCanvas`` 公开 API，不含业务逻辑
（SPEC-node-list-panel §1.1）。

同步机制（SPEC §1.4 / §1.5）：

- ``graph.node_added`` / ``node_removed`` → 行增删；
- 节点加入时挂接 ``status_changed`` / ``changed`` 到同一槽
  （槽内 ``sender()`` 定位节点，避免闭包持有引用），删除时显式断开；
- ``canvas.selection_changed`` ↔ 列表 ``currentRowChanged`` 双向同步，
  ``_syncing`` 标志位防止信号循环。
"""

from typing import Dict, Optional, Tuple

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.blueprint import BlueprintCanvas, BlueprintGraph
from InstructionX_UIKit.components import Button, ListWidget
from InstructionX_UIKit.theme import T, set_property

__all__ = ["NodeListPanel"]

#: 列表行高（两行信息：标题行 + 类型/状态行）
_ITEM_HEIGHT = 48
#: 按钮尺寸档（与工具条一致的紧凑风格）
_BUTTON_SIZE = "sm"
#: 空态占位文案
_EMPTY_TEXT = "画布暂无节点"
#: 状态色点字符
_STATUS_DOT = "●"
#: 节点状态 → 主题令牌键映射（SPEC §1.3，查表替代 if-elif）
_STATUS_COLOR_KEYS = {
    "idle": "color.text.tertiary",
    "running": "color.primary",
    "done": "color.success",
    "error": "color.danger",
}
#: 未知状态色兜底令牌键
_FALLBACK_COLOR_KEY = "color.text.tertiary"
#: done 状态键（耗时信息追加判断）
_STATUS_DONE = "done"
#: 按钮文案
_LOCATE_TEXT = "定位"
_RENAME_TEXT = "重命名"
_DELETE_TEXT = "删除"
#: 重命名对话框文案
_RENAME_TITLE = "重命名节点"
_RENAME_LABEL = "新标题："


class _NodeRow(QWidget):
    """列表行控件：状态色点 + 标题（第一行）、类型 · 状态（第二行）。

    自身与全部子标签设置 ``WA_TransparentForMouseEvents``：item widget
    默认截获鼠标事件导致点击行不触发列表选中，透明化后点击穿透到
    列表视口，选中行为与原生列表一致（SPEC §1.2 变通）。
    """

    def __init__(self, node, parent: QWidget = None) -> None:
        """构建两行布局并按节点当前数据初始化。

        参数:
            node: ``BlueprintNode``（数据源，仅读取）。
            parent: 父控件。
        """
        super().__init__(parent)
        self._dot = QLabel(_STATUS_DOT)
        self._title = QLabel()
        self._info = QLabel()
        self._build_layout()
        self.refresh(node)

    def refresh(self, node) -> None:
        """按节点当前数据刷新标题 / 信息行 / 状态点颜色。"""
        color_key = _STATUS_COLOR_KEYS.get(node.status, _FALLBACK_COLOR_KEY)
        self._dot.setStyleSheet(f"color: {str(T(color_key))};")
        self._title.setText(node.title)
        self._info.setText(self._info_text(node))

    def _build_layout(self) -> None:
        """装配两行垂直布局并设置鼠标透明（点击穿透到列表视口）。"""
        title_font = self._title.font()
        title_font.setBold(True)
        self._title.setFont(title_font)
        set_property(self._info, "role", "tertiary")
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.addWidget(self._dot)
        header.addWidget(self._title, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.addLayout(header)
        layout.addWidget(self._info)
        transparent = Qt.WidgetAttribute.WA_TransparentForMouseEvents
        for widget in (self, self._dot, self._title, self._info):
            widget.setAttribute(transparent)

    @staticmethod
    def _info_text(node) -> str:
        """信息行文案：``类型名 · 状态``，done 时追加耗时。"""
        text = f"{node.type_name} · {node.status}"
        if node.status == _STATUS_DONE and node.elapsed_ms is not None:
            text += f" · {node.elapsed_ms:.0f} ms"
        return text


class NodeListPanel(QWidget):
    """节点列表面板：全量节点清单 + 定位 / 重命名 / 删除。

    参数:
        graph: ``BlueprintGraph``（数据源，监听增删信号）。
        canvas: ``BlueprintCanvas``（选中同步与定位目标）。
        parent: 父控件。

    公开方法:
        ``row_count()``：当前列表行数（测试断言用）；
        ``current_node_id()``：列表选中行对应的节点 id（无选中为 None）。
    """

    def __init__(self, graph: BlueprintGraph, canvas: BlueprintCanvas,
                 parent: QWidget = None) -> None:
        super().__init__(parent)
        self._graph = graph
        self._canvas = canvas
        # node_id -> (列表项, 节点对象)：节点引用用于删除时断开其信号
        self._rows: Dict[str, Tuple[QListWidgetItem, object]] = {}
        self._syncing = False
        self._list = ListWidget(item_height=_ITEM_HEIGHT)
        self._empty_hint = QLabel(_EMPTY_TEXT)
        self._locate_button = Button(_LOCATE_TEXT, size=_BUTTON_SIZE)
        self._rename_button = Button(_RENAME_TEXT, size=_BUTTON_SIZE)
        self._delete_button = Button(_DELETE_TEXT, size=_BUTTON_SIZE)
        self._build_layout()
        self._connect_signals()
        for node in graph.nodes():
            self._add_row(node)
        self._sync_empty_state()
        self._update_action_state()

    # ------------------------------------------------------------------ 对外
    def row_count(self) -> int:
        """当前列表行数。"""
        return self._list.count()

    def current_node_id(self) -> Optional[str]:
        """列表选中行的节点 id（存于 item ``UserRole``），无选中为 None。"""
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    # ------------------------------------------------------------------ 组装
    def _build_layout(self) -> None:
        """装配布局：占位标签 / 列表（互斥显隐）+ 底部按钮行。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_property(self._empty_hint, "role", "tertiary")
        self._empty_hint.hide()
        layout.addWidget(self._empty_hint, 1)
        layout.addWidget(self._list, 1)
        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 0, 0, 0)
        buttons.setSpacing(4)
        for button in (self._locate_button, self._rename_button,
                       self._delete_button):
            buttons.addWidget(button)
        layout.addLayout(buttons)

    def _connect_signals(self) -> None:
        """连接 graph / canvas / 列表 / 按钮信号到对应槽。"""
        self._graph.node_added.connect(self._add_row)
        self._graph.node_removed.connect(self._remove_row)
        self._canvas.selection_changed.connect(self._on_canvas_selection)
        self._list.currentRowChanged.connect(self._on_list_row)
        self._locate_button.clicked.connect(self._locate_current)
        self._rename_button.clicked.connect(self._rename_current)
        self._delete_button.clicked.connect(self._delete_current)

    # ------------------------------------------------------------------ 行增删与刷新
    def _add_row(self, node) -> None:
        """``graph.node_added`` 槽：建行并挂接节点状态 / 变化信号。"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, node.id)
        self._list.addItem(item)
        self._list.setItemWidget(item, _NodeRow(node))
        self._rows[node.id] = (item, node)
        node.status_changed.connect(self._on_node_changed)
        node.changed.connect(self._on_node_changed)
        self._sync_empty_state()

    def _remove_row(self, node_id: str) -> None:
        """``graph.node_removed`` 槽：断开节点信号并移除行。"""
        entry = self._rows.pop(node_id, None)
        if entry is None:
            return
        item, node = entry
        node.status_changed.disconnect(self._on_node_changed)
        node.changed.disconnect(self._on_node_changed)
        self._list.takeItem(self._list.row(item))
        self._sync_empty_state()

    def _on_node_changed(self) -> None:
        """节点 ``status_changed`` / ``changed`` 槽：刷新对应行。"""
        node = self.sender()
        if node is None or node.id not in self._rows:
            return
        item, _ = self._rows[node.id]
        row_widget = self._list.itemWidget(item)
        if row_widget is not None:
            row_widget.refresh(node)

    # ------------------------------------------------------------------ 选中双向同步
    def _on_canvas_selection(self, node_ids: list) -> None:
        """画布 → 列表：单选时高亮对应行，否则清列表选中（守卫防循环）。"""
        if self._syncing:
            return
        self._syncing = True
        self._apply_canvas_selection(node_ids)
        self._syncing = False
        self._update_action_state()

    def _on_list_row(self, _row: int) -> None:
        """列表 → 画布：反向选中节点（守卫防循环）。"""
        if self._syncing:
            return
        self._syncing = True
        node_id = self.current_node_id()
        self._canvas.select_nodes([node_id] if node_id else [])
        self._syncing = False
        self._update_action_state()

    def _apply_canvas_selection(self, node_ids: list) -> None:
        """按画布选中集设置列表当前行（仅单选映射，其余清空）。"""
        if len(node_ids) == 1 and node_ids[0] in self._rows:
            item, _ = self._rows[node_ids[0]]
            self._list.setCurrentRow(self._list.row(item))
        else:
            self._list.setCurrentRow(-1)

    # ------------------------------------------------------------------ 操作按钮（槽 ≤5 行委托）
    def _locate_current(self) -> None:
        """定位：画布视图居中到选中节点。"""
        node_id = self.current_node_id()
        if node_id:
            self._canvas.center_on(node_id)

    def _rename_current(self) -> None:
        """重命名：对话框输入新标题写回 ``node.title``。"""
        node = self._current_node()
        if node is not None:
            self._prompt_rename(node)

    def _delete_current(self) -> None:
        """删除：``graph.remove_node``（连带清理边，行随信号移除）。"""
        node_id = self.current_node_id()
        if node_id:
            self._graph.remove_node(node_id)

    # ------------------------------------------------------------------ 内部
    def _current_node(self):
        """列表选中行对应的节点对象（无选中 / 已删除为 None）。"""
        node_id = self.current_node_id()
        return self._graph.node(node_id) if node_id else None

    def _prompt_rename(self, node) -> None:
        """弹重命名对话框；确认且非空时写回标题并广播变化。"""
        text, ok = QInputDialog.getText(
            self, _RENAME_TITLE, _RENAME_LABEL, text=node.title)
        if ok and text.strip():
            node.title = text.strip()
            node.changed.emit()

    def _sync_empty_state(self) -> None:
        """空态占位与列表互斥显隐。"""
        empty = self._list.count() == 0
        self._empty_hint.setVisible(empty)
        self._list.setVisible(not empty)

    def _update_action_state(self) -> None:
        """按是否有选中行启用 / 禁用三个操作按钮。"""
        enabled = self.current_node_id() is not None
        for button in (self._locate_button, self._rename_button,
                       self._delete_button):
            button.setEnabled(enabled)
