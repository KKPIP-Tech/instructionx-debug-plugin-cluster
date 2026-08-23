# -*- coding: utf-8 -*-
"""蓝图存档列表面板（ui 层）。

展示 DataProvider 插件资产区 ``graphs/`` 下的全部命名存档（名称 +
节点数 / 保存时间元信息），提供「另存为 / 加载 / 重命名 / 删除」
管理操作（SPEC-graph-list §1.1）。

职责边界（SPEC §1.2）：

- 「重命名 / 删除」是纯存档文件操作，面板内闭环：直接调
  ``BlueprintOpenCVService`` 公开方法，失败中文弹窗 + ERROR 日志，
  成功后自刷列表；
- 「另存为 / 加载」依赖画布快照与恢复，经信号
  ``save_as_requested`` / ``load_requested(str)`` 转发 MainWidget 编排。

行渲染沿用 NodeListPanel 的变通：item widget 设置
``WA_TransparentForMouseEvents``，点击穿透到列表视口保证选中行为。
"""

from datetime import datetime
from typing import Any, Dict, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.components import Button, ListWidget
from InstructionX_UIKit.theme import set_property

from core.interfaces import ILocalizationFacade
from utils.logging_tools import LoggerManager, get_name

__all__ = ["GraphListPanel"]

#: 列表行高（两行信息：名称行 + 元信息行）
_ITEM_HEIGHT = 48
#: 按钮尺寸档（与节点列表 / 工具条一致的紧凑风格）
_BUTTON_SIZE = "sm"
#: 取词分组名（与 text/zh.xml 一致）
_GROUP = "graph_list"
#: 存档修改时间格式（service 返回）与列表短格式（栏宽 200px 内防裁断，
#: 完整时间入 tooltip）
_MODIFIED_AT_FORMAT = "%Y-%m-%d %H:%M:%S"
_MODIFIED_AT_SHORT_FORMAT = "%m-%d %H:%M"

_logger = LoggerManager()
_MODULE = get_name()


def _make_tr(i18n: Optional[ILocalizationFacade]):
    """生成取词函数；门面未注入时优雅降级返回键名（正常加载始终注入）。"""

    def tr(key: str, /, **params) -> str:
        if i18n is None:
            return key
        return i18n.tr(_GROUP, key, **params)

    return tr


class _GraphRow(QWidget):
    """存档行控件：名称（第一行，加粗）+ 元信息（第二行，次级色）。

    自身与子标签设置 ``WA_TransparentForMouseEvents``，点击穿透到
    列表视口（同 NodeListPanel 的 _NodeRow 变通，SPEC §3.2）。
    """

    def __init__(self, meta: Dict[str, Any], parent: QWidget = None,
                 i18n: Optional[ILocalizationFacade] = None) -> None:
        """按存档元信息构建两行布局（meta 为 ``list_graphs`` 单项）。"""
        super().__init__(parent)
        name_label = QLabel(str(meta.get("name", "")))
        info_label = QLabel(self._info_text(meta, i18n))
        info_label.setToolTip(str(meta.get("modified_at", "")))
        self._build_layout(name_label, info_label)

    def _build_layout(self, name_label: QLabel, info_label: QLabel) -> None:
        """装配两行垂直布局并设置鼠标透明（点击穿透到列表视口）。"""
        name_font = name_label.font()
        name_font.setBold(True)
        name_label.setFont(name_font)
        set_property(info_label, "role", "tertiary")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(0)
        layout.addWidget(name_label)
        layout.addWidget(info_label)
        transparent = Qt.WidgetAttribute.WA_TransparentForMouseEvents
        for widget in (self, name_label, info_label):
            widget.setAttribute(transparent)

    @staticmethod
    def _info_text(meta: Dict[str, Any],
                   i18n: Optional[ILocalizationFacade]) -> str:
        """元信息行文案（节点数未知时按 row.unknown_count 占位）。"""
        tr = _make_tr(i18n)
        node_count = meta.get("node_count")
        count = str(node_count) if node_count is not None else tr(
            "row.unknown_count")
        return tr("row.info", count=count, time=_GraphRow._short_time(meta))

    @staticmethod
    def _short_time(meta: Dict[str, Any]) -> str:
        """完整时间转短格式显示（解析失败原样返回，防御性格式兜底）。"""
        raw = str(meta.get("modified_at", ""))
        try:
            stamp = datetime.strptime(raw, _MODIFIED_AT_FORMAT)
            return stamp.strftime(_MODIFIED_AT_SHORT_FORMAT)
        except ValueError:
            return raw


class GraphListPanel(QWidget):
    """蓝图存档列表面板：存档清单 + 另存为 / 加载 / 重命名 / 删除。

    参数:
        service: ``BlueprintOpenCVService`` 实例（存档枚举 / 重命名 /
            删除的数据源）。
        parent: 父控件。
        i18n: 插件取词门面（可选，未注入时显示键名兜底）。

    信号:
        load_requested(str): 请求加载指定存档（双击或「加载」按钮）；
        save_as_requested(): 请求把当前画布另存为命名存档。

    公开方法:
        ``refresh()``：重新枚举存档并重建列表（保留同名选中态）；
        ``retranslate_ui()``：语言切换后重设静态文案并重建列表行；
        ``current_graph_name()``：选中行的存档名（无选中为 None）；
        ``row_count()``：当前行数（测试断言用）。
    """

    load_requested = Signal(str)
    save_as_requested = Signal()

    def __init__(self, service, parent: QWidget = None,
                 i18n: Optional[ILocalizationFacade] = None) -> None:
        super().__init__(parent)
        self._service = service
        self._i18n = i18n
        self._tr = _make_tr(i18n)
        self._list = ListWidget(item_height=_ITEM_HEIGHT)
        self._empty_hint = QLabel(self._tr("empty"))
        self._build_buttons()
        self._build_layout()
        self._connect_signals()
        self.refresh()

    def _build_buttons(self) -> None:
        """创建四个存档操作按钮（文案经 i18n 取词）。"""
        self._save_as_button = Button(self._tr("save_as"), size=_BUTTON_SIZE)
        self._load_button = Button(self._tr("load"), size=_BUTTON_SIZE)
        self._rename_button = Button(self._tr("rename"), size=_BUTTON_SIZE)
        self._delete_button = Button(self._tr("delete"), size=_BUTTON_SIZE)

    def retranslate_ui(self) -> None:
        """语言切换后重设按钮 / 空态文案并重建列表行（行文案随 refresh）。"""
        self._save_as_button.setText(self._tr("save_as"))
        self._load_button.setText(self._tr("load"))
        self._rename_button.setText(self._tr("rename"))
        self._delete_button.setText(self._tr("delete"))
        self._empty_hint.setText(self._tr("empty"))
        self.refresh()

    # ------------------------------------------------------------------ 对外
    def refresh(self) -> None:
        """重新枚举存档并重建列表（保留同名选中态）。"""
        selected = self.current_graph_name()
        self._list.clear()
        result = self._service.list_graphs()
        if not result.get("success"):
            _logger.error(_MODULE, f"枚举图存档失败：{result.get('error')}")
        for meta in result.get("data", {}).get("graphs", []):
            self._add_row(meta)
        self._restore_selection(selected)
        self._sync_empty_state()
        self._update_action_state()

    def current_graph_name(self) -> Optional[str]:
        """选中行的存档名（存于 item ``UserRole``），无选中为 None。"""
        item = self._list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def row_count(self) -> int:
        """当前列表行数。"""
        return self._list.count()

    # ------------------------------------------------------------------ 组装
    def _build_layout(self) -> None:
        """装配布局：占位标签 / 列表（互斥显隐）+ 两行操作按钮。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self._empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        set_property(self._empty_hint, "role", "tertiary")
        self._empty_hint.hide()
        layout.addWidget(self._empty_hint, 1)
        layout.addWidget(self._list, 1)
        layout.addLayout(self._button_row(self._save_as_button, self._load_button))
        layout.addLayout(self._button_row(self._rename_button, self._delete_button))

    @staticmethod
    def _button_row(*buttons) -> QHBoxLayout:
        """组装一行等宽按钮。"""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        for button in buttons:
            row.addWidget(button)
        return row

    def _connect_signals(self) -> None:
        """连接列表 / 按钮信号到对应槽。"""
        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._list.currentRowChanged.connect(self._update_action_state)
        self._save_as_button.clicked.connect(self.save_as_requested)
        self._load_button.clicked.connect(self._load_current)
        self._rename_button.clicked.connect(self._rename_current)
        self._delete_button.clicked.connect(self._delete_current)

    # ------------------------------------------------------------------ 行构建与选中
    def _add_row(self, meta: Dict[str, Any]) -> None:
        """追加一行存档（名称存 item ``UserRole``，行文案随当前语言）。"""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, str(meta.get("name", "")))
        self._list.addItem(item)
        self._list.setItemWidget(item, _GraphRow(meta, i18n=self._i18n))

    def _restore_selection(self, name: Optional[str]) -> None:
        """刷新后恢复同名行的选中态（不存在则保持未选中）。"""
        if name is None:
            return
        for row in range(self._list.count()):
            item = self._list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == name:
                self._list.setCurrentRow(row)
                return

    # ------------------------------------------------------------------ 操作按钮（槽 ≤5 行委托）
    def _load_current(self) -> None:
        """加载：发 ``load_requested``（MainWidget 恢复画布）。"""
        name = self.current_graph_name()
        if name:
            self.load_requested.emit(name)

    def _on_double_click(self, item: QListWidgetItem) -> None:
        """双击条目等效「加载」。"""
        self.load_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _rename_current(self) -> None:
        """重命名：对话框输入新名，委托 service 并自刷。"""
        name = self.current_graph_name()
        if name:
            self._prompt_rename(name)

    def _delete_current(self) -> None:
        """删除：确认对话框后委托 service 并自刷。"""
        name = self.current_graph_name()
        if name:
            self._confirm_delete(name)

    # ------------------------------------------------------------------ 内部
    def _prompt_rename(self, name: str) -> None:
        """重命名流程：输入新名 → service.rename_graph → 刷新 / 报错。"""
        new_name, ok = QInputDialog.getText(
            self, self._tr("dialog.rename_title"),
            self._tr("dialog.rename_label"), text=name)
        if not ok or not new_name.strip() or new_name.strip() == name:
            return
        result = self._service.rename_graph(name, new_name.strip())
        if not result.get("success"):
            self._report_error(self._tr("fail.rename"), result.get("error"))
            return
        self.refresh()

    def _confirm_delete(self, name: str) -> None:
        """删除流程：确认 → service.delete_graph → 刷新 / 报错。"""
        answer = QMessageBox.question(
            self, self._tr("dialog.delete_title"),
            self._tr("dialog.delete_text", name=name))
        if answer != QMessageBox.StandardButton.Yes:
            return
        result = self._service.delete_graph(name)
        if not result.get("success"):
            self._report_error(self._tr("fail.delete"), result.get("error"))
            return
        self.refresh()

    def _report_error(self, title: str, message: Any) -> None:
        """操作失败：中文弹窗告知 + ERROR 日志（两者都要）。"""
        _logger.error(_MODULE, f"{title}：{message}")
        QMessageBox.warning(self, title, str(message))

    def _sync_empty_state(self) -> None:
        """空态占位与列表互斥显隐。"""
        empty = self._list.count() == 0
        self._empty_hint.setVisible(empty)
        self._list.setVisible(not empty)

    def _update_action_state(self, *_args) -> None:
        """按是否有选中行启用依赖选中的按钮（另存为始终可用）。"""
        enabled = self.current_graph_name() is not None
        for button in (self._load_button, self._rename_button,
                       self._delete_button):
            button.setEnabled(enabled)
