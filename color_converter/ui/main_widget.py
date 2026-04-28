"""
颜色转换插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QGroupBox, QLineEdit, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


class MainWidget(QWidget):
    """颜色转换插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._qss_content = ""
        self._setup_ui()
        self._load_plugin_style()
        self.destroyed.connect(self._on_destroyed)

    def _load_plugin_style(self):
        """加载插件目录下的 style/*.qss，支持 {variable} 变量替换"""
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
        """添加标题"""
        title = QLabel("颜色格式转换工具")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setProperty("heading", "true")
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

    def _create_hex_input(self) -> QLineEdit:
        """创建 HEX 输入框"""
        hex_input = QLineEdit()
        hex_input.setPlaceholderText("输入 HEX 颜色 (如 #FF5733)")
        return hex_input

    def _create_rgb_output(self) -> QLineEdit:
        """创建 RGB 输出框"""
        rgb_output = QLineEdit()
        rgb_output.setReadOnly(True)
        rgb_output.setPlaceholderText("RGB 结果")
        return rgb_output

    def _connect_convert_button(self, hex_input: QLineEdit, rgb_output: QLineEdit):
        """连接转换按钮"""
        self._convert_btn = QPushButton("转换")
        self._convert_btn.clicked.connect(
            lambda: rgb_output.setText(self._service.hex_to_rgb(hex_input.text().strip()))
        )
