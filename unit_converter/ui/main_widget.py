"""
单位转换插件主控件

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGroupBox,
    QComboBox, QLineEdit, QMessageBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from utils.style_qss.registry import QssRegistry


class MainWidget(QWidget):
    """单位转换插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()
        self._load_plugin_style()
        self.destroyed.connect(self._on_destroy)

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
            self.setStyleSheet("\n".join(qss_parts))

    def _on_destroy(self):
        """Widget 销毁时卸载 QSS 样式"""
        self.setStyleSheet("")

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = self._create_content_widget()
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域"""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setFrameShape(QFrame.Shape.NoFrame)
        return area

    def _create_content_widget(self) -> QWidget:
        """创建内容控件"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        layout.addWidget(self._create_title())
        self._add_conversion_groups(layout)

        layout.addStretch()
        return content

    def _add_conversion_groups(self, layout):
        """添加所有转换组"""
        groups = [
            ("长度转换", ['m', 'km', 'cm', 'mm', 'inch', 'ft'],
             self._service.length_converter, "结果: {result:.4f} {unit}"),
            ("温度转换", ['C', 'F', 'K'],
             self._service.temperature_converter, "结果: {result:.2f}°{unit}"),
            ("重量转换", ['kg', 'g', 'mg', 'lb', 'oz'],
             self._service.weight_converter, "结果: {result:.4f} {unit}"),
        ]
        for title, units, fn, fmt in groups:
            g, linp, lfrm, lto, _ = self._create_conversion_group(title, units, fn, fmt)
            layout.addWidget(g)
            if title == "长度转换":
                self.length_input, self.length_from, self.length_to = linp, lfrm, lto
            elif title == "温度转换":
                self.temp_input, self.temp_from, self.temp_to = linp, lfrm, lto
            elif title == "重量转换":
                self.weight_input, self.weight_from, self.weight_to = linp, lfrm, lto

    def _create_title(self) -> QLabel:
        """创建标题"""
        title = QLabel("单位转换工具")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_labeled_input(self, label_text: str) -> tuple:
        """创建标签和输入框"""
        label = QLabel(label_text)
        line_edit = QLineEdit()
        return label, line_edit

    def _do_conversion(self, input_field, from_combo, to_combo, converter_fn, fmt):
        """执行转换并显示结果"""
        try:
            value = float(input_field.text())
            result = converter_fn(value, from_combo.currentText(), to_combo.currentText())
            return fmt.format(result=result, unit=to_combo.currentText())
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数值！")
            return None

    def _create_conversion_group(
            self, title: str, units: list,
            converter_fn, fmt: str) -> tuple:
        """创建通用转换组"""
        group = QGroupBox(title)
        layout = QVBoxLayout()
        layout.setSpacing(12)
        label, input_field = self._create_labeled_input("数值:")
        layout.addWidget(label)
        layout.addWidget(input_field)

        from_combo = QComboBox()
        to_combo = QComboBox()
        layout.addLayout(self._create_unit_row(from_combo, to_combo, units))

        result_label = QLabel("结果: ")
        result_label.setObjectName("resultValue")
        self._connect_convert_button(
            QPushButton("转换"), input_field, from_combo, to_combo,
            converter_fn, fmt, result_label, layout)
        layout.addWidget(result_label)
        group.setLayout(layout)
        return group, input_field, from_combo, to_combo, result_label

    def _connect_convert_button(
            self, btn, input_field, from_combo, to_combo,
            converter_fn, fmt, result_label, layout):
        """连接转换按钮信号"""
        btn.clicked.connect(
            lambda r=result_label, i=input_field, f=from_combo, t=to_combo, c=converter_fn, fm=fmt:
                self._on_convert_clicked(i, f, t, c, fm, r))
        layout.addWidget(btn)

    def _on_convert_clicked(
            self, input_field, from_combo, to_combo, converter_fn, fmt, result_label):
        """转换按钮点击处理"""
        text = self._do_conversion(
            input_field, from_combo, to_combo, converter_fn, fmt)
        if text:
            result_label.setText(text)

    def _create_unit_row(self, from_combo: QComboBox, to_combo: QComboBox,
                         units: list) -> QVBoxLayout:
        """创建单位选择行"""
        row = QVBoxLayout()
        from_combo.addItems(units)
        to_combo.addItems(units)
        to_combo.setCurrentIndex(1)
        row.addWidget(QLabel("从:"))
        row.addWidget(from_combo)
        row.addWidget(QLabel("到:"))
        row.addWidget(to_combo)
        return row
