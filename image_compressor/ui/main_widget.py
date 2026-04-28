"""
图片压缩插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox,
    QSlider, QLineEdit, QMessageBox, QScrollArea, QFrame,
    QFileDialog
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


def _load_config() -> dict:
    config_path = Path(__file__).parent.parent / "config" / "default.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


class MainWidget(QWidget):
    """图片压缩插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("ImageCompressorWidget")
        self._service = service
        self._config = _load_config()
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
            self.destroyed.connect(self._unload_style)

    def _unload_style(self):
        self.setStyleSheet("")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = self._create_content_layout()
        content.setLayout(content_layout)
        scroll_area.setWidget(content)
        return scroll_area

    def _create_content_layout(self) -> QVBoxLayout:
        ui_cfg = self._config.get("ui", {})
        margins = ui_cfg.get("content_margins", [16, 16, 16, 16])
        spacing = ui_cfg.get("content_spacing", 16)
        layout = QVBoxLayout()
        layout.setContentsMargins(*margins)
        layout.setSpacing(spacing)
        layout.addWidget(self._create_title())
        layout.addWidget(self._create_file_group())
        layout.addWidget(self._create_quality_group())
        layout.addWidget(self._create_compress_button())
        layout.addStretch()
        return layout

    def _create_title(self) -> QLabel:
        title = QLabel("图片压缩工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_file_group(self) -> QGroupBox:
        ui_cfg = self._config.get("ui", {})
        group_spacing = ui_cfg.get("group_spacing", 12)
        file_group = QGroupBox("选择图片")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(group_spacing)
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("选择图片文件...")
        file_layout.addWidget(self.file_input)
        browse_btn = QPushButton("浏览...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        file_group.setLayout(file_layout)
        return file_group

    def _create_quality_group(self) -> QGroupBox:
        group_spacing = self._config.get("ui", {}).get("group_spacing", 12)
        quality_group = QGroupBox("压缩质量")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(group_spacing)
        quality_layout.addWidget(self._create_quality_label())
        quality_layout.addWidget(self._create_quality_slider())
        quality_group.setLayout(quality_layout)
        return quality_group

    def _create_quality_label(self) -> QLabel:
        default_quality = self._config.get("compression", {}).get("default_quality", 85)
        self.quality_label = QLabel(f"质量: {default_quality}%")
        return self.quality_label

    def _create_quality_slider(self) -> QSlider:
        comp_cfg = self._config.get("compression", {})
        min_quality = comp_cfg.get("min_quality", 1)
        max_quality = comp_cfg.get("max_quality", 100)
        default_quality = comp_cfg.get("default_quality", 85)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setMinimum(min_quality)
        self.quality_slider.setMaximum(max_quality)
        self.quality_slider.setValue(default_quality)
        self.quality_slider.valueChanged.connect(
            lambda v: self.quality_label.setText(f"质量: {v}%")
        )
        return self.quality_slider

    def _create_compress_button(self) -> QPushButton:
        compress_btn = QPushButton("压缩图片")
        compress_btn.setProperty("class", "primary")
        compress_btn.clicked.connect(self._compress)
        return compress_btn

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.file_input.setText(file_path)

    def _compress(self):
        file_path = self.file_input.text()
        if not file_path:
            QMessageBox.warning(None, "警告", "请先选择图片文件！")
            return
        quality = self.quality_slider.value()
        success = self._service.compress_image(file_path, quality)
        if success:
            QMessageBox.information(None, "成功", f"图片已压缩！质量: {quality}%")
        else:
            QMessageBox.critical(None, "错误", "图片压缩失败！")
