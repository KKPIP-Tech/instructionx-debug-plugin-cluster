# -*- coding: utf-8 -*-
"""文本格式化插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/LineEdit）与 T() 令牌，
随全局主题自动换肤。
"""

import json
from pathlib import Path

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


_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"


class MainWidget(QWidget):
    """文本格式化插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._cfg = self._load_config()
        self._spacing = self._cfg.get("ui", {}).get("spacing", 16)
        self._setup_ui()

    def _load_config(self) -> dict:
        """读取插件默认配置（UI 间距与边距参数）"""
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = QWidget()
        layout = QVBoxLayout(content)
        margins = self._cfg.get("ui", {}).get("margins", [16, 16, 16, 16])
        layout.setContentsMargins(*margins)
        layout.setSpacing(self._spacing)

        self._add_title(layout)
        self._add_case_group(layout, "转换为大写", self._service.to_uppercase)
        self._add_case_group(layout, "转换为小写", self._service.to_lowercase)

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
        title = QLabel("文本格式化工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _add_case_group(self, layout: QVBoxLayout, title: str, convert):
        """添加一组大小写转换组件（输入框 + 转换按钮）"""
        group = QGroupBox(title)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(self._spacing)

        input_field = LineEdit(placeholder="输入文本...", clearable=True)
        group_layout.addWidget(input_field)

        btn = Button(title, variant="primary")
        btn.clicked.connect(lambda: input_field.setText(convert(input_field.text())))
        group_layout.addWidget(btn)

        group.setLayout(group_layout)
        layout.addWidget(group)
