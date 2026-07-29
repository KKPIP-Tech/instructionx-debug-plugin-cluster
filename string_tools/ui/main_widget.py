# -*- coding: utf-8 -*-
"""字符串工具插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/TextArea）与 T() 令牌，
随全局主题自动换肤。
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import Button, TextArea

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"
_DEFAULT_MARGINS = [16, 16, 16, 16]
_DEFAULT_SPACING = 16
_DEFAULT_GRID_SPACING = 8
_TEXT_MIN_HEIGHT = 80


class MainWidget(QWidget):
    """字符串工具插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        cfg = self._load_config().get("ui", {})
        self._margins = cfg.get("margins", _DEFAULT_MARGINS)
        self._spacing = cfg.get("spacing", _DEFAULT_SPACING)
        self._grid_spacing = cfg.get("grid_spacing", _DEFAULT_GRID_SPACING)
        self.input_text: TextArea = None
        self.output_text: TextArea = None
        self.stats_label = QLabel()
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
        layout.setContentsMargins(*self._margins)
        layout.setSpacing(self._spacing)

        self._add_title(layout)
        layout.addWidget(self._create_input_group())
        layout.addWidget(self._create_buttons_group())
        layout.addWidget(self._create_output_group())
        layout.addWidget(self.stats_label)
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
        title = QLabel("字符串处理工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _create_input_group(self) -> QGroupBox:
        """创建输入文本分组"""
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(self._spacing)
        self.input_text = TextArea(placeholder="在此输入要处理的文本...")
        self.input_text.setMinimumHeight(_TEXT_MIN_HEIGHT)
        input_layout.addWidget(self.input_text)
        input_group.setLayout(input_layout)
        return input_group

    def _create_buttons_group(self) -> QGroupBox:
        """创建操作按钮分组（文本变换为主操作，使用 primary 变体）"""
        buttons_group = QGroupBox("操作")
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(self._grid_spacing)
        self._add_button(buttons_layout, "转大写", self._on_upper, 0, 0)
        self._add_button(buttons_layout, "转小写", self._on_lower, 0, 1)
        self._add_button(buttons_layout, "反转文本", self._on_reverse, 0, 2)
        self._add_button(buttons_layout, "首字母大写", self._on_capitalize, 1, 0)
        self._add_button(buttons_layout, "移除空白", self._on_remove_whitespace, 1, 1)
        self._add_button(buttons_layout, "统计信息", self._on_stats, 1, 2, "default")
        buttons_group.setLayout(buttons_layout)
        return buttons_group

    def _add_button(self, layout: QGridLayout, text: str, handler,
                    row: int, col: int, variant: str = "primary"):
        """向网格布局添加一个操作按钮"""
        btn = Button(text, variant=variant)
        btn.clicked.connect(handler)
        layout.addWidget(btn, row, col)

    def _create_output_group(self) -> QGroupBox:
        """创建输出结果分组（等宽字体便于查看处理结果）"""
        output_group = QGroupBox("输出结果")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(self._spacing)
        self.output_text = TextArea()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(_TEXT_MIN_HEIGHT)
        self.output_text.setFont(QFont(MONO_FAMILY))
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        return output_group

    def _get_input(self) -> str:
        """获取输入文本"""
        return self.input_text.toPlainText()

    def _set_output(self, text: str):
        """设置输出文本"""
        self.output_text.setText(text)

    def _run_transform(self, transform):
        """执行一个文本变换并输出结果（空输入时提示）"""
        text = self._get_input()
        self._set_output(transform(text) if text else "请输入文本")

    def _on_upper(self):
        """转大写"""
        self._run_transform(self._service.to_uppercase)

    def _on_lower(self):
        """转小写"""
        self._run_transform(self._service.to_lowercase)

    def _on_reverse(self):
        """反转文本"""
        self._run_transform(self._service.reverse_text)

    def _on_capitalize(self):
        """首字母大写"""
        self._run_transform(self._service.capitalize_words)

    def _on_remove_whitespace(self):
        """移除空白"""
        self._run_transform(self._service.remove_whitespace)

    def _on_stats(self):
        """统计单词与字符数量并展示在统计标签上"""
        text = self._get_input()
        if not text:
            self.stats_label.setText("请输入文本")
            return
        words = self._service.count_words(text)
        chars_with = self._service.count_chars(text, True)
        chars_without = self._service.count_chars(text, False)
        self.stats_label.setText(
            f"单词数: {words} | 字符数(含空格): {chars_with} | "
            f"字符数(不含空格): {chars_without}"
        )
