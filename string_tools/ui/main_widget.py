"""
字符串工具插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel,
    QPushButton, QGroupBox,
    QTextEdit, QGridLayout, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


class MainWidget(QWidget):
    """字符串工具插件主控件"""

    _config_cache: dict = {}

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("StringToolsWidget")
        self._service = service
        self.output_text: QTextEdit = None
        self.input_text: QTextEdit = None
        self.stats_label = QLabel()
        self.stats_label.setProperty("muted", "true")
        self.stats_label.setContentsMargins(0, 4, 0, 4)
        self._load_config()
        self._setup_ui()
        self._load_plugin_style()
        self.destroyed.connect(self._on_destroyed)

    def _load_config(self):
        """从配置文件加载 UI 参数"""
        if not self._config_cache:
            config_path = Path(__file__).parent.parent / "config" / "default.json"
            if config_path.exists():
                self._config_cache = json.loads(config_path.read_text(encoding="utf-8"))
            else:
                self._config_cache = {"ui": {"margins": [16, 16, 16, 16], "spacing": 16}}
        ui_cfg = self._config_cache.get("ui", {})
        self._margins = ui_cfg.get("margins", [16, 16, 16, 16])
        self._spacing = ui_cfg.get("spacing", 16)
        self._grid_spacing = ui_cfg.get("grid_spacing", 8)

    def _load_plugin_style(self):
        """加载插件目录下的 style/*.qss"""
        style_dir = Path(__file__).parent.parent / "style"
        if not style_dir.exists():
            return
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))
        if qss_parts:
            self.setStyleSheet("\n".join(qss_parts))

    def _on_destroyed(self):
        """widget 销毁时卸载 QSS 样式"""
        self.setStyleSheet("")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = self._create_content_widget()
        main_layout.addWidget(scroll_area)
        scroll_area.setWidget(content)

    def _create_scroll_area(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        return scroll_area

    def _create_content_widget(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(*self._margins)
        layout.setSpacing(self._spacing)
        layout.addWidget(self._create_title())
        layout.addWidget(self._create_input_group())
        layout.addWidget(self._create_buttons_group())
        layout.addWidget(self._create_output_group())
        layout.addWidget(self.stats_label)
        layout.addStretch()
        return content

    def _create_title(self) -> QLabel:
        title = QLabel("字符串处理工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_input_group(self) -> QGroupBox:
        input_group = QGroupBox("输入文本")
        input_layout = QVBoxLayout()
        input_layout.setSpacing(self._spacing)
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("在此输入要处理的文本...")
        self.input_text.setMinimumHeight(80)
        input_layout.addWidget(self.input_text)
        input_group.setLayout(input_layout)
        return input_group

    def _create_buttons_group(self) -> QGroupBox:
        buttons_group = QGroupBox("操作")
        buttons_layout = QGridLayout()
        buttons_layout.setSpacing(self._grid_spacing)
        self._add_button(buttons_layout, "转大写", self._on_upper, 0, 0)
        self._add_button(buttons_layout, "转小写", self._on_lower, 0, 1)
        self._add_button(buttons_layout, "反转文本", self._on_reverse, 0, 2)
        self._add_button(buttons_layout, "首字母大写", self._on_capitalize, 1, 0)
        self._add_button(buttons_layout, "移除空白", self._on_remove_whitespace, 1, 1)
        self._add_button(buttons_layout, "统计信息", self._on_stats, 1, 2)
        buttons_group.setLayout(buttons_layout)
        return buttons_group

    def _add_button(self, layout, text, handler, row, col):
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        layout.addWidget(btn, row, col)

    def _create_output_group(self) -> QGroupBox:
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(80)
        output_group = QGroupBox("输出结果")
        output_layout = QVBoxLayout()
        output_layout.setSpacing(self._spacing)
        output_layout.addWidget(self.output_text)
        output_group.setLayout(output_layout)
        return output_group

    def _get_input(self) -> str:
        return self.input_text.toPlainText()

    def _set_output(self, text: str):
        self.output_text.setText(text)

    def _on_upper(self):
        text = self._get_input()
        self._set_output(self._service.to_uppercase(text) if text else "请输入文本")

    def _on_lower(self):
        text = self._get_input()
        self._set_output(self._service.to_lowercase(text) if text else "请输入文本")

    def _on_reverse(self):
        text = self._get_input()
        self._set_output(self._service.reverse_text(text) if text else "请输入文本")

    def _on_capitalize(self):
        text = self._get_input()
        self._set_output(self._service.capitalize_words(text) if text else "请输入文本")

    def _on_remove_whitespace(self):
        text = self._get_input()
        self._set_output(self._service.remove_whitespace(text) if text else "请输入文本")

    def _on_stats(self):
        text = self._get_input()
        if text:
            words = self._service.count_words(text)
            chars_with = self._service.count_chars(text, True)
            chars_without = self._service.count_chars(text, False)
            self.stats_label.setText(
                f"单词数: {words} | 字符数(含空格): {chars_with} | 字符数(不含空格): {chars_without}"
            )
        else:
            self.stats_label.setText("请输入文本")
