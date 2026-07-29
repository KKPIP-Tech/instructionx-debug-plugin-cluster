# -*- coding: utf-8 -*-
"""单位转换插件主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/LineEdit/ComboBox/Message）
与 T() 令牌，随全局主题自动换肤。
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
from InstructionX_UIKit.components import Button, ComboBox, LineEdit, Message

#: 转换组定义：标题、单位列表、Service 方法名、结果文本格式
_GROUP_SPECS = (
    ("长度转换", ["m", "km", "cm", "mm", "inch", "ft"],
     "length_converter", "结果: {result:.4f} {unit}"),
    ("温度转换", ["C", "F", "K"],
     "temperature_converter", "结果: {result:.2f}°{unit}"),
    ("重量转换", ["kg", "g", "mg", "lb", "oz"],
     "weight_converter", "结果: {result:.4f} {unit}"),
)


class MainWidget(QWidget):
    """单位转换插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()

    def _setup_ui(self):
        """构建 UI：滚动区 + 内容控件"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        scroll_area.setWidget(self._create_content_widget())
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域"""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setFrameShape(QFrame.Shape.NoFrame)
        return area

    def _create_content_widget(self) -> QWidget:
        """创建内容控件：标题 + 各转换组"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._create_title())
        for spec in _GROUP_SPECS:
            layout.addWidget(self._create_conversion_group(*spec))
        layout.addStretch()
        return content

    def _create_title(self) -> QLabel:
        """创建标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("单位转换工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        return title

    def _create_conversion_group(
            self, title: str, units: list, method_name: str, fmt: str) -> QGroupBox:
        """创建单个转换组：输入框 + 单位选择 + 转换按钮 + 结果标签"""
        group = QGroupBox(title)
        layout = QVBoxLayout()
        layout.setSpacing(12)
        input_field = LineEdit(placeholder="请输入数值", clearable=True)
        from_combo = ComboBox(units)
        to_combo = ComboBox(units)
        to_combo.setCurrentIndex(1)
        result_label = self._create_result_label()
        layout.addWidget(QLabel("数值:"))
        layout.addWidget(input_field)
        layout.addLayout(self._create_unit_row(from_combo, to_combo))
        self._add_convert_button(
            layout, input_field, from_combo, to_combo, method_name, fmt, result_label)
        layout.addWidget(result_label)
        group.setLayout(layout)
        return group

    def _create_result_label(self) -> QLabel:
        """创建结果展示标签（粗体，字号取 UIKit 令牌）"""
        label = QLabel("结果: ")
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        label.setFont(font)
        return label

    def _create_unit_row(self, from_combo: ComboBox, to_combo: ComboBox) -> QVBoxLayout:
        """创建「从/到」单位选择行"""
        row = QVBoxLayout()
        row.addWidget(QLabel("从:"))
        row.addWidget(from_combo)
        row.addWidget(QLabel("到:"))
        row.addWidget(to_combo)
        return row

    def _add_convert_button(
            self, layout, input_field, from_combo, to_combo,
            method_name, fmt, result_label):
        """创建主操作按钮并连接点击信号"""
        button = Button("转换", variant="primary")
        button.clicked.connect(
            lambda: self._on_convert_clicked(
                input_field, from_combo, to_combo, method_name, fmt, result_label))
        layout.addWidget(button)

    def _on_convert_clicked(
            self, input_field, from_combo, to_combo,
            method_name, fmt, result_label):
        """转换按钮点击：解析输入、调用 Service、刷新结果"""
        try:
            value = float(input_field.text())
        except ValueError:
            Message.warning(self, "请输入有效的数值！")
            return
        converter = getattr(self._service, method_name)
        result = converter(value, from_combo.currentText(), to_combo.currentText())
        result_label.setText(fmt.format(result=result, unit=to_combo.currentText()))
