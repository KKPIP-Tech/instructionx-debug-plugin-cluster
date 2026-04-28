"""
文本格式化插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

import json
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"


class MainWidget(QWidget):
    """文本格式化插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("TextFormattingWidget")
        self._service = service
        self._cfg = self._load_config()
        self._spacing = self._cfg.get("ui", {}).get("spacing", 16)
        self._qss_content = ""
        self._setup_ui()
        self._load_plugin_style()
        self.destroyed.connect(self._on_destroyed)

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
            self._qss_content = "\n".join(qss_parts)
            self.setStyleSheet(self._qss_content)

    def _on_destroyed(self):
        """Widget 销毁时清理 QSS 样式"""
        self.setStyleSheet("")
        self._qss_content = ""

    def _load_config(self):
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = self._build_scroll_container()
        main_layout.addWidget(scroll_area)

    def _build_scroll_container(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        margins = self._cfg.get("ui", {}).get("margins", [16, 16, 16, 16])
        layout.setContentsMargins(*margins)
        layout.setSpacing(self._spacing)
        layout.addWidget(self._build_title())
        layout.addWidget(self._build_uppercase_group())
        layout.addWidget(self._build_lowercase_group())
        layout.addStretch()
        scroll_area.setWidget(content)
        return scroll_area

    def _build_title(self):
        title = QLabel("文本格式化工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _build_uppercase_group(self):
        group = QGroupBox("转换为大写")
        layout = QVBoxLayout()
        layout.setSpacing(self._spacing)
        input_field = QLineEdit()
        input_field.setPlaceholderText("输入文本...")
        layout.addWidget(input_field)
        btn = QPushButton("转换为大写")
        btn.clicked.connect(
            lambda: input_field.setText(self._service.to_uppercase(input_field.text()))
        )
        layout.addWidget(btn)
        group.setLayout(layout)
        return group

    def _build_lowercase_group(self):
        group = QGroupBox("转换为小写")
        layout = QVBoxLayout()
        layout.setSpacing(self._spacing)
        input_field = QLineEdit()
        input_field.setPlaceholderText("输入文本...")
        layout.addWidget(input_field)
        btn = QPushButton("转换为小写")
        btn.clicked.connect(
            lambda: input_field.setText(self._service.to_lowercase(input_field.text()))
        )
        layout.addWidget(btn)
        group.setLayout(layout)
        return group
