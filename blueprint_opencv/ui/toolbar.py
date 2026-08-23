# -*- coding: utf-8 -*-
"""工具条（ui 层）。

运行 / 停止 / 保存 / 另存为 / 适应视图按钮与状态标签的纯视图组件：
只负责展示与转发点击事件（Qt 信号），不含任何业务逻辑，
具体动作由 ``MainWidget`` 连接后委托 service 完成。

「保存」覆盖写入当前蓝图存档（无当前存档时退化为另存为）；
存档加载由左侧「蓝图」列表承担（SPEC-graph-list §3.4），
工具条不再提供「加载图」按钮。
"""

from typing import Optional

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from InstructionX_UIKit.components import Button
from InstructionX_UIKit.theme import set_property

from core.interfaces import ILocalizationFacade

__all__ = ["ToolBar"]

#: 按钮统一尺寸档（工具条紧凑风格）
_BUTTON_SIZE = "sm"
#: 取词分组名（与 text/zh.xml 一致）
_GROUP = "toolbar"


class ToolBar(QWidget):
    """蓝图编辑器工具条。

    参数:
        parent: 父控件。
        i18n: 插件取词门面（可选，未注入时显示键名兜底）。

    信号:
        run_requested: 点击「运行」。
        stop_requested: 点击「停止」。
        save_current_requested: 点击「保存」（覆盖当前存档）。
        save_requested: 点击「另存为」。
        fit_requested: 点击「适应视图」。
    """

    run_requested = Signal()
    stop_requested = Signal()
    save_current_requested = Signal()
    save_requested = Signal()
    fit_requested = Signal()

    def __init__(self, parent: QWidget = None,
                 i18n: Optional[ILocalizationFacade] = None) -> None:
        """构建工具条按钮与状态标签（文案经 i18n 取词）。"""
        super().__init__(parent)
        self._i18n = i18n
        self._run_button = Button(self._tr("run"), variant="primary",
                                  size=_BUTTON_SIZE)
        self._stop_button = Button(self._tr("stop"), size=_BUTTON_SIZE)
        self._save_current_button = Button(self._tr("save"), size=_BUTTON_SIZE)
        self._save_button = Button(self._tr("save_as"), size=_BUTTON_SIZE)
        self._fit_button = Button(self._tr("fit"), size=_BUTTON_SIZE)
        self._status_label = QLabel(self._tr("status.ready"))
        self._build_layout()
        self._connect_buttons()
        self.set_running(False)

    def _tr(self, key: str, /, **params) -> str:
        """取插件文案；门面未注入时优雅降级返回键名。"""
        if self._i18n is None:
            return key
        return self._i18n.tr(_GROUP, key, **params)

    def retranslate_ui(self) -> None:
        """语言切换后重设按钮与就绪状态文案（运行中状态由运行事件刷新）。"""
        self._run_button.setText(self._tr("run"))
        self._stop_button.setText(self._tr("stop"))
        self._save_current_button.setText(self._tr("save"))
        self._save_button.setText(self._tr("save_as"))
        self._fit_button.setText(self._tr("fit"))
        if not self._stop_button.isEnabled():
            self._status_label.setText(self._tr("status.ready"))

    def set_status(self, text: str) -> None:
        """更新状态标签文案（运行状态 / 耗时 / 错误摘要）。"""
        self._status_label.setText(str(text))

    def set_running(self, running: bool) -> None:
        """切换运行态：运行中禁用「运行」、启用「停止」，反之亦然。"""
        self._run_button.setEnabled(not running)
        self._stop_button.setEnabled(running)

    def _build_layout(self) -> None:
        """装配横向布局：按钮组靠左，状态标签拉伸占满右侧。"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        for button in (self._run_button, self._stop_button,
                       self._save_current_button, self._save_button,
                       self._fit_button):
            layout.addWidget(button)
        set_property(self._status_label, "role", "secondary")
        layout.addWidget(self._status_label, 1)

    def _connect_buttons(self) -> None:
        """把按钮点击一对一转发为工具条信号。"""
        self._run_button.clicked.connect(self.run_requested)
        self._stop_button.clicked.connect(self.stop_requested)
        self._save_current_button.clicked.connect(self.save_current_requested)
        self._save_button.clicked.connect(self.save_requested)
        self._fit_button.clicked.connect(self.fit_requested)
