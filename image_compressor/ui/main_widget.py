# -*- coding: utf-8 -*-
"""图片压缩插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/LineEdit/Slider/Message）
与 T() 令牌，随全局主题自动换肤。
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import T
from InstructionX_UIKit.components import Button, LineEdit, Message, Slider


def _load_config() -> dict:
    """读取插件默认配置（config/default.json），不存在时返回空字典。"""
    config_path = Path(__file__).parent.parent / "config" / "default.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


class MainWidget(QWidget):
    """图片压缩插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._config = _load_config()
        self._setup_ui()

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = QWidget()
        layout = QVBoxLayout(content)
        ui_cfg = self._config.get("ui", {})
        layout.setContentsMargins(*ui_cfg.get("content_margins", [16, 16, 16, 16]))
        layout.setSpacing(ui_cfg.get("content_spacing", 16))

        self._add_title(layout)
        layout.addWidget(self._create_file_group())
        layout.addWidget(self._create_quality_group())
        layout.addWidget(self._create_compress_button())

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
        title = QLabel("图片压缩工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _create_file_group(self) -> QGroupBox:
        """创建图片选择分组"""
        group_spacing = self._config.get("ui", {}).get("group_spacing", 12)
        file_group = QGroupBox("选择图片")
        file_layout = QVBoxLayout()
        file_layout.setSpacing(group_spacing)
        self.file_input = LineEdit(placeholder="选择图片文件...", clearable=True)
        file_layout.addWidget(self.file_input)
        browse_btn = Button("浏览...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        file_group.setLayout(file_layout)
        return file_group

    def _create_quality_group(self) -> QGroupBox:
        """创建压缩质量分组"""
        group_spacing = self._config.get("ui", {}).get("group_spacing", 12)
        quality_group = QGroupBox("压缩质量")
        quality_layout = QVBoxLayout()
        quality_layout.setSpacing(group_spacing)
        quality_layout.addWidget(self._create_quality_label())
        quality_layout.addWidget(self._create_quality_slider())
        quality_group.setLayout(quality_layout)
        return quality_group

    def _create_quality_label(self) -> QLabel:
        """创建质量数值标签"""
        default_quality = self._config.get("compression", {}).get("default_quality", 85)
        self.quality_label = QLabel(f"质量: {default_quality}%")
        return self.quality_label

    def _create_quality_slider(self) -> Slider:
        """创建质量滑块（UIKit Slider，范围与默认值取配置）"""
        comp_cfg = self._config.get("compression", {})
        self.quality_slider = Slider(
            orientation=Qt.Orientation.Horizontal,
            minimum=comp_cfg.get("min_quality", 1),
            maximum=comp_cfg.get("max_quality", 100),
            value=comp_cfg.get("default_quality", 85),
        )
        self.quality_slider.valueChanged.connect(self._on_quality_changed)
        return self.quality_slider

    def _on_quality_changed(self, value: int):
        """滑块值变化时同步质量标签"""
        self.quality_label.setText(f"质量: {value}%")

    def _create_compress_button(self) -> Button:
        """创建压缩主操作按钮"""
        compress_btn = Button("压缩图片", variant="primary")
        compress_btn.clicked.connect(self._compress)
        return compress_btn

    def _browse_file(self):
        """打开系统文件对话框选择图片"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.file_input.setText(file_path)

    def _compress(self):
        """触发压缩并反馈结果"""
        file_path = self.file_input.text()
        if not file_path:
            Message.warning(self, "请先选择图片文件！")
            return
        quality = self.quality_slider.value()
        success = self._service.compress_image(file_path, quality)
        if success:
            Message.success(self, f"图片已压缩！质量: {quality}%")
        else:
            Message.error(self, "图片压缩失败！")
