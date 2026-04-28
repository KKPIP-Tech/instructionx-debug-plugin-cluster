"""
代码格式化插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox,
    QTextEdit, QComboBox, QMessageBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


class MainWidget(QWidget):
    """代码格式化插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("code-formatter-main")
        self._service = service
        self._setup_ui()
        self._load_plugin_style()

    def _load_plugin_style(self):
        style_dir = Path(__file__).parent.parent / "style"
        if not style_dir.exists():
            return
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))
        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            self.setStyleSheet(self._qss_content)
            self.destroyed.connect(self._unload_plugin_style)

    def _unload_plugin_style(self):
        """卸载插件样式，防止样式残留"""
        self.setStyleSheet("")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
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
        return scroll_area

    def _create_title(self):
        title = QLabel("代码格式化工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_input_section(self):
        cfg = self._load_config()
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText(
            cfg.get("ui", {}).get("input_placeholder", "粘贴代码..."))
        input_layout = QVBoxLayout()
        inner_spacing = cfg.get("ui", {}).get("inner_spacing", 12)
        input_layout.setSpacing(inner_spacing)
        input_layout.addWidget(self.input_text)
        group = QGroupBox("输入代码")
        group.setLayout(input_layout)
        return group

    def _create_actions_section(self):
        actions_layout = QVBoxLayout()
        cfg = self._load_config()
        inner_spacing = cfg.get("ui", {}).get("inner_spacing", 12)
        actions_layout.setSpacing(inner_spacing)
        actions_layout.addWidget(self._create_json_button())
        actions_layout.addLayout(self._create_lang_selector())
        actions_layout.addWidget(self._create_comment_button())
        actions_layout.addWidget(self._create_compress_button())
        group = QGroupBox("操作")
        group.setLayout(actions_layout)
        return group

    def _create_json_button(self):
        btn = QPushButton("格式化 JSON")
        btn.clicked.connect(self._format_json)
        return btn

    def _create_lang_selector(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("选择语言:"))
        self.lang_combo = QComboBox()
        languages = self._load_languages()
        self.lang_combo.addItems(languages)
        layout.addWidget(self.lang_combo)
        return layout

    def _load_languages(self):
        """从配置文件读取语言列表"""
        cfg = self._load_config()
        return cfg.get("languages", ["python", "javascript"])

    def _load_config(self):
        """加载插件配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "default.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _create_comment_button(self):
        btn = QPushButton("移除注释")
        btn.clicked.connect(self._remove_comments)
        return btn

    def _create_compress_button(self):
        btn = QPushButton("压缩代码")
        btn.clicked.connect(self._compress_code)
        return btn

    def _format_json(self):
        code = self.input_text.toPlainText()
        if not code:
            QMessageBox.warning(None, "警告", "请输入JSON代码！")
            return
        result = self._service.format_json(code)
        self.input_text.setText(result)

    def _remove_comments(self):
        code = self.input_text.toPlainText()
        if not code:
            QMessageBox.warning(None, "警告", "请输入代码！")
            return
        language = self.lang_combo.currentText()
        result = self._service.remove_comments(code, language)
        self.input_text.setText(result)

    def _compress_code(self):
        code = self.input_text.toPlainText()
        if not code:
            QMessageBox.warning(None, "警告", "请输入代码！")
            return
        result = self._service.compress_code(code)
        self.input_text.setText(result)

    def hideEvent(self, event):
        self._unload_plugin_style()
        super().hideEvent(event)
