# -*- coding: utf-8 -*-
"""代码格式化插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/ComboBox/TextArea/Message）
与 T() 令牌，随全局主题自动换肤。
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

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import Button, ComboBox, Message, TextArea


class MainWidget(QWidget):
    """代码格式化插件主控件"""

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
        cfg = self._load_config()
        margins = cfg.get("ui", {}).get("margins", [16, 16, 16, 16])
        spacing = cfg.get("ui", {}).get("spacing", 16)
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)

        layout.addWidget(self._create_title())
        layout.addWidget(self._create_input_section())
        layout.addWidget(self._create_actions_section())
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

    def _create_title(self) -> QLabel:
        """创建标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("代码格式化工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        return title

    def _create_input_section(self) -> QGroupBox:
        """创建代码输入区（等宽字体便于代码阅读）"""
        cfg = self._load_config()
        placeholder = cfg.get("ui", {}).get("input_placeholder", "粘贴代码...")
        self.input_text = TextArea(placeholder=placeholder)
        self.input_text.setFont(QFont(MONO_FAMILY))

        input_layout = QVBoxLayout()
        input_layout.setSpacing(cfg.get("ui", {}).get("inner_spacing", 12))
        input_layout.addWidget(self.input_text)
        group = QGroupBox("输入代码")
        group.setLayout(input_layout)
        return group

    def _create_actions_section(self) -> QGroupBox:
        """创建操作区（格式化 / 移除注释 / 压缩）"""
        actions_layout = QVBoxLayout()
        cfg = self._load_config()
        actions_layout.setSpacing(cfg.get("ui", {}).get("inner_spacing", 12))
        actions_layout.addWidget(self._create_json_button())
        actions_layout.addLayout(self._create_lang_selector())
        actions_layout.addWidget(self._create_comment_button())
        actions_layout.addWidget(self._create_compress_button())
        group = QGroupBox("操作")
        group.setLayout(actions_layout)
        return group

    def _create_json_button(self) -> Button:
        """创建 JSON 格式化按钮（主操作使用 primary 变体）"""
        btn = Button("格式化 JSON", variant="primary")
        btn.clicked.connect(self._format_json)
        return btn

    def _create_lang_selector(self) -> QVBoxLayout:
        """创建语言选择下拉框"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择语言:"))
        self.lang_combo = ComboBox(self._load_languages())
        layout.addWidget(self.lang_combo)
        return layout

    def _create_comment_button(self) -> Button:
        """创建移除注释按钮"""
        btn = Button("移除注释")
        btn.clicked.connect(self._remove_comments)
        return btn

    def _create_compress_button(self) -> Button:
        """创建压缩代码按钮"""
        btn = Button("压缩代码")
        btn.clicked.connect(self._compress_code)
        return btn

    def _load_languages(self) -> list:
        """从配置文件读取语言列表"""
        cfg = self._load_config()
        return cfg.get("languages", ["python", "javascript"])

    def _load_config(self) -> dict:
        """加载插件配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "default.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _format_json(self):
        """格式化输入区中的 JSON 代码"""
        code = self.input_text.toPlainText()
        if not code:
            Message.warning(self, "请输入JSON代码！")
            return
        self.input_text.setText(self._service.format_json(code))

    def _remove_comments(self):
        """按所选语言移除输入区代码的注释"""
        code = self.input_text.toPlainText()
        if not code:
            Message.warning(self, "请输入代码！")
            return
        language = self.lang_combo.currentText()
        self.input_text.setText(self._service.remove_comments(code, language))

    def _compress_code(self):
        """压缩输入区代码（移除空白字符）"""
        code = self.input_text.toPlainText()
        if not code:
            Message.warning(self, "请输入代码！")
            return
        self.input_text.setText(self._service.compress_code(code))
