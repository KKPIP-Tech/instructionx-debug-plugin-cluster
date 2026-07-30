# -*- coding: utf-8 -*-
"""ui/tabs 包公共基座：BaseTab。

提供各演示 Tab 共享的滚动容器构建、结果回调与日志回调访问能力。
结果展示与日志记录由 main_widget 的公共面板统一承载，
各 Tab 通过构造注入的回调进行调用，保持行为与拆分前一致。
"""

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget


class BaseTab:
    """演示 Tab 基类

    职责：持有演示服务实例与 main_widget 注入的结果/日志回调，
    提供带滚动区域的 Tab 内容容器构建辅助。
    子类负责各自演示主题的控件构建与事件处理（槽函数仅取输入、
    调服务、显示结果的委托模式）。
    """

    def __init__(self, display_result: Callable, append_log: Callable):
        """初始化 Tab 基座

        参数:
            display_result: 结果显示回调，签名 (title, content, is_error=False)
            append_log: 日志追加回调，签名 (message)
        """
        self._display_result = display_result
        self._append_log = append_log
        # Message 弹窗的父控件：create_tab 时指向本 Tab 的滚动容器
        self._message_parent: QWidget | None = None

    def _make_scroll_tab(self) -> tuple[QScrollArea, QVBoxLayout]:
        """创建带滚动区域的 Tab 内容容器"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll.setWidget(widget)
        return scroll, layout

    def _log(self, message: str):
        """添加日志到主控件日志面板"""
        self._append_log(message)
