# -*- coding: utf-8 -*-
"""颜色转换插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/LineEdit）与 T() 令牌，
随全局主题自动换肤。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import T
from InstructionX_UIKit.components import Button, LineEdit


class MainWidget(QWidget):
    """颜色转换插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        self._add_title(layout)
        self._add_hex_converter(layout)

        layout.addStretch()
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        return scroll_area

    def _add_title(self, layout: QVBoxLayout):
        """添加标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("颜色格式转换工具")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _add_hex_converter(self, layout: QVBoxLayout):
        """添加 HEX 转 RGB 组件"""
        hex_group = QGroupBox("HEX 转 RGB")
        hex_layout = QVBoxLayout()
        hex_layout.setSpacing(12)

        hex_input = self._create_hex_input()
        hex_layout.addWidget(hex_input)

        rgb_output = self._create_rgb_output()
        hex_layout.addWidget(rgb_output)

        self._connect_convert_button(hex_input, rgb_output)
        hex_layout.addWidget(self._convert_btn)

        hex_group.setLayout(hex_layout)
        layout.addWidget(hex_group)

    def _create_hex_input(self) -> LineEdit:
        """创建 HEX 输入框"""
        return LineEdit(placeholder="输入 HEX 颜色 (如 #FF5733)", clearable=True)

    def _create_rgb_output(self) -> LineEdit:
        """创建 RGB 输出框"""
        rgb_output = LineEdit(placeholder="RGB 结果")
        rgb_output.setReadOnly(True)
        return rgb_output

    def _connect_convert_button(self, hex_input: LineEdit, rgb_output: LineEdit):
        """连接转换按钮"""
        self._convert_btn = Button("转换", variant="primary")
        self._convert_btn.clicked.connect(
            lambda: rgb_output.setText(self._service.hex_to_rgb(hex_input.text().strip()))
        )
