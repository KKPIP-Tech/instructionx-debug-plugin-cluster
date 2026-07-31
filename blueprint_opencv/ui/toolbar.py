# -*- coding: utf-8 -*-
"""工具条（ui 层）。

运行 / 停止 / 另存为 / 适应视图按钮与状态标签的纯视图组件：
只负责展示与转发点击事件（Qt 信号），不含任何业务逻辑，
具体动作由 ``MainWidget`` 连接后委托 service 完成。

存档加载由左侧「蓝图」列表承担（SPEC-graph-list §3.4），
工具条不再提供「加载图」按钮。
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from InstructionX_UIKit.components import Button
from InstructionX_UIKit.theme import set_property

__all__ = ["ToolBar"]

#: 按钮统一尺寸档（工具条紧凑风格）
_BUTTON_SIZE = "sm"
#: 初始状态文案
_STATUS_READY = "就绪"


class ToolBar(QWidget):
    """蓝图编辑器工具条。

    信号:
        run_requested: 点击「运行」。
        stop_requested: 点击「停止」。
        save_requested: 点击「另存为」。
        fit_requested: 点击「适应视图」。
    """

    run_requested = Signal()
    stop_requested = Signal()
    save_requested = Signal()
    fit_requested = Signal()

    def __init__(self, parent: QWidget = None) -> None:
        """构建工具条按钮与状态标签。

        参数:
            parent: 父控件。
        """
        super().__init__(parent)
        self._run_button = Button("运行", variant="primary", size=_BUTTON_SIZE)
        self._stop_button = Button("停止", size=_BUTTON_SIZE)
        self._save_button = Button("另存为", size=_BUTTON_SIZE)
        self._fit_button = Button("适应视图", size=_BUTTON_SIZE)
        self._status_label = QLabel(_STATUS_READY)
        self._build_layout()
        self._connect_buttons()
        self.set_running(False)

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
        for button in (self._run_button, self._stop_button, self._save_button,
                       self._fit_button):
            layout.addWidget(button)
        set_property(self._status_label, "role", "secondary")
        layout.addWidget(self._status_label, 1)

    def _connect_buttons(self) -> None:
        """把按钮点击一对一转发为工具条信号。"""
        self._run_button.clicked.connect(self.run_requested)
        self._stop_button.clicked.connect(self.stop_requested)
        self._save_button.clicked.connect(self.save_requested)
        self._fit_button.clicked.connect(self.fit_requested)
