# -*- coding: utf-8 -*-
"""参数面板（ui 层）。

监听画布选中（由 ``MainWidget`` 转发），选中单个节点时按其
``param_schema``（来自 ``function.node_catalog``，经 node_bootstrap
查询）重建表单；修改即时写回 ``node.properties[key]`` 并
``node.changed.emit()``，属性随 ``canvas.to_dict()`` 序列化无损保存。

仅做视图与事件分发：不感知 cv2 / 执行引擎，写回语义与
SPEC §1.2 的外部属性面板方案一致。
"""

from typing import Any, Dict

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.components import Button, ColorPicker, ComboBox, LineEdit
from InstructionX_UIKit.components.spin_box import DoubleSpinBox, SpinBox
from InstructionX_UIKit.theme import set_property

from .node_bootstrap import param_schema_of

__all__ = ["PropertyPanel"]

#: 表单控件统一尺寸档
_CONTROL_SIZE = "sm"
#: int / float 字段缺省 min/max 时的兜底范围（防御性，正常 schema 必带）
_FALLBACK_INT_RANGE = (0, 9999)
_FALLBACK_FLOAT_RANGE = (0.0, 9999.0)
#: file_path 字段浏览按钮文案与对话框过滤
_BROWSE_TEXT = "浏览…"
_IMAGE_FILE_FILTER = "图片文件 (*.png *.jpg *.jpeg *.bmp);;所有文件 (*)"
#: 需要「保存」语义文件对话框的节点类型（其余按「打开」语义）
_SAVE_DIALOG_TYPES = frozenset({"save_image"})
#: 未选中提示
_HINT_TEXT = "在画布中选中一个节点，查看 / 编辑其参数。"


class PropertyPanel(QScrollArea):
    """节点参数面板：schema 驱动的自动表单。

    公开方法:
        ``bind_node(node)``：绑定并展示某节点的参数表单；
        ``clear()``：清空回提示态。
    """

    def __init__(self, parent: QWidget = None) -> None:
        """初始化滚动容器与空态提示。

        参数:
            parent: 父控件。
        """
        super().__init__(parent)
        self._bound_node = None
        self._status_info = None
        self.setWidgetResizable(True)
        self._host = QWidget()
        self._host_layout = QVBoxLayout(self._host)
        self._host_layout.setContentsMargins(0, 0, 0, 0)
        self._host_layout.setSpacing(6)
        self.setWidget(self._host)
        self.clear()

    def bind_node(self, node) -> None:
        """绑定节点：展示标题 / 类型 / 状态，并按 schema 重建参数表单。

        参数:
            node: ``BlueprintNode``；``None`` 等价于 ``clear()``。
        """
        self._clear_content()
        if node is None:
            self._add_hint(_HINT_TEXT)
            self._host_layout.addStretch(1)
            return
        self._bound_node = node
        self._build_header(node)
        self._build_form(node)
        node.status_changed.connect(self._on_node_status_changed)
        self._host_layout.addStretch(1)

    def clear(self) -> None:
        """解除绑定并清空内容，回退到未选中提示。"""
        self._clear_content()
        self._add_hint(_HINT_TEXT)
        self._host_layout.addStretch(1)

    # ------------------------------------------------------------------ 内部
    def _clear_content(self) -> None:
        """解除绑定并移除全部内容控件（不补提示）。

        先 hide 再 deleteLater：deleteLater 在事件循环处理 DeferredDelete
        后才真正销毁，期间控件虽已脱离布局仍会按旧几何残留绘制
        （select_nodes 会连发空选 / 单选两次 selection_changed，残留
        肉眼可见），hide 立即消除该视觉残留。
        """
        self._unbind_node()
        while self._host_layout.count():
            item = self._host_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().hide()
                item.widget().deleteLater()

    def _unbind_node(self) -> None:
        """断开旧节点的状态信号（未连接时忽略 Qt 抛出的异常）。"""
        if self._bound_node is not None:
            try:
                self._bound_node.status_changed.disconnect(
                    self._on_node_status_changed)
            except (TypeError, RuntimeError):
                pass  # 信号本未连接（如重复 clear），无需处理
        self._bound_node = None

    def _build_header(self, node) -> None:
        """头部信息：标题（加粗）+ 类型 / ID + 运行状态行。"""
        title = QLabel(node.title)
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        self._host_layout.addWidget(title)
        self._add_hint(f"类型：{node.type_name}    ID：{node.id}")
        self._status_info = QLabel()
        set_property(self._status_info, "role", "tertiary")
        self._host_layout.addWidget(self._status_info)
        self._refresh_status(node)

    def _build_form(self, node) -> None:
        """按 schema 逐字段生成表单行；无 schema 时给出说明。"""
        schema = param_schema_of(node.type_name)
        if not schema:
            self._add_hint("该节点无可编辑参数。")
            return
        for field in schema:
            self._add_field(node, field)

    def _add_field(self, node, field: Dict[str, Any]) -> None:
        """按字段类型分发到对应构建器（查表替代 if-elif 长链）。"""
        builders = {
            "int": self._add_int, "float": self._add_float,
            "str": self._add_text, "choice": self._add_choice,
            "file_path": self._add_file_path, "color": self._add_color,
        }
        builder = builders.get(field.get("type"))
        if builder is None:
            self._add_hint(f"未知参数类型：{field.get('type')}（{field.get('key')}）")
            return
        self._host_layout.addWidget(QLabel(str(field.get("label", ""))))
        builder(node, field)

    def _add_int(self, node, field: Dict[str, Any]) -> None:
        """整数字段：SpinBox；schema 标 ``odd`` 时步进 2 保持奇数。"""
        minimum, maximum = field.get("min", _FALLBACK_INT_RANGE[0]), field.get(
            "max", _FALLBACK_INT_RANGE[1])
        step = 2 if field.get("odd") else 1
        value = int(node.properties.get(field["key"], field.get("default", minimum)))
        spin = SpinBox(minimum, maximum, value, step=step, size=_CONTROL_SIZE)
        spin.valueChanged.connect(
            lambda v, n=node, k=field["key"]: self._write_back(n, k, int(v)))
        self._host_layout.addWidget(spin)

    def _add_float(self, node, field: Dict[str, Any]) -> None:
        """浮点字段：DoubleSpinBox（两位小数）。"""
        minimum = float(field.get("min", _FALLBACK_FLOAT_RANGE[0]))
        maximum = float(field.get("max", _FALLBACK_FLOAT_RANGE[1]))
        value = float(node.properties.get(field["key"], field.get("default", minimum)))
        spin = DoubleSpinBox(minimum, maximum, value, size=_CONTROL_SIZE)
        spin.valueChanged.connect(
            lambda v, n=node, k=field["key"]: self._write_back(n, k, float(v)))
        self._host_layout.addWidget(spin)

    def _add_text(self, node, field: Dict[str, Any]) -> None:
        """字符串字段：单行输入框。"""
        value = str(node.properties.get(field["key"], field.get("default", "")))
        edit = LineEdit(value, size=_CONTROL_SIZE)
        edit.textChanged.connect(
            lambda t, n=node, k=field["key"]: self._write_back(n, k, str(t)))
        self._host_layout.addWidget(edit)

    def _add_choice(self, node, field: Dict[str, Any]) -> None:
        """枚举字段：下拉框，options 来自 schema。"""
        options = [str(o) for o in field.get("options", [])]
        combo = ComboBox(options, size=_CONTROL_SIZE)
        value = str(node.properties.get(field["key"], field.get("default", "")))
        combo.setCurrentText(value)
        combo.currentTextChanged.connect(
            lambda t, n=node, k=field["key"]: self._write_back(n, k, str(t)))
        self._host_layout.addWidget(combo)

    def _add_color(self, node, field: Dict[str, Any]) -> None:
        """颜色字段：ColorPicker，写回 ``#rrggbb`` 字符串。"""
        value = str(node.properties.get(field["key"], field.get("default", "#000000")))
        picker = ColorPicker(value, size=_CONTROL_SIZE)
        picker.colorChanged.connect(
            lambda c, n=node, k=field["key"]: self._write_back(n, k, c.name()))
        self._host_layout.addWidget(picker)

    def _add_file_path(self, node, field: Dict[str, Any]) -> None:
        """文件路径字段：输入框 + 浏览按钮（save_image 用保存对话框）。"""
        value = str(node.properties.get(field["key"], field.get("default", "")))
        edit = LineEdit(value, size=_CONTROL_SIZE)
        edit.textChanged.connect(
            lambda t, n=node, k=field["key"]: self._write_back(n, k, str(t)))
        browse = Button(_BROWSE_TEXT, size=_CONTROL_SIZE)
        browse.clicked.connect(
            lambda _=False, n=node, e=edit: self._browse_file(n, e))
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(edit, 1)
        row_layout.addWidget(browse)
        self._host_layout.addWidget(row)

    def _browse_file(self, node, edit: LineEdit) -> None:
        """弹文件对话框并把选中路径写入输入框（触发 textChanged 写回）。"""
        if node.type_name in _SAVE_DIALOG_TYPES:
            path, _ = QFileDialog.getSaveFileName(self, "选择保存路径", "", _IMAGE_FILE_FILTER)
        else:
            path, _ = QFileDialog.getOpenFileName(self, "选择图片文件", "", _IMAGE_FILE_FILTER)
        if path:
            edit.setText(path)

    def _write_back(self, node, key: str, value: Any) -> None:
        """写回 ``node.properties`` 并刷新节点外观（SPEC §1.2 契约）。"""
        node.properties[key] = value
        node.changed.emit()

    def _on_node_status_changed(self, _status: str) -> None:
        """节点运行状态变化 → 刷新状态行文案。"""
        if self._bound_node is not None:
            self._refresh_status(self._bound_node)

    def _refresh_status(self, node) -> None:
        """状态行：运行状态 + 耗时（若有）。"""
        text = f"状态：{node.status}"
        if node.elapsed_ms is not None:
            text += f"    耗时：{node.elapsed_ms:.0f} ms"
        self._status_info.setText(text)

    def _add_hint(self, text: str) -> None:
        """添加一条自动换行的次级说明文字。"""
        label = QLabel(text)
        label.setWordWrap(True)
        set_property(label, "role", "tertiary")
        self._host_layout.addWidget(label)
