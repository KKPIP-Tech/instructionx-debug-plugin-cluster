# -*- coding: utf-8 -*-
"""蓝图 Demo 页（BP_SPEC §7）。

展示 ``InstructionX_UIKit.blueprint`` 节点图组件的完整用法：

- 顶部工具条：运行 / 单步 / 重置 / 适应视图 / 保存 JSON / 加载 JSON +
  状态标签；
- 中央 ``BlueprintCanvas``：预置「开始→加载图像→预处理→模型推理→
  后处理→保存结果」流水线（exec 链 + image/tensor 数据引脚混排）；
- 右侧属性面板：选中节点时显示其类型 / 标题 / 状态，并用
  ``playground.ParamForm`` 编辑属性（写回 ``node.properties``）。

**纯模拟说明**：本页的「运行 / 单步」只驱动 ``ExecutionController``
的 UI 状态指示（running / done / 耗时徽标 / 路径高亮），不执行任何
真实业务逻辑（不读图、不跑模型）。

节点体说明：``body_builder`` 注入的属性编辑控件在画布内被画布置为
鼠标透明（避免与节点拖拽冲突），仅作展示；实际编辑请用右侧属性面板，
两者写回的都是同一份 ``node.properties``。

文案经 ``bind_tr`` 按 ``blueprint`` 分组取词：节点类型元数据在注册期
取词（注册表存字符串，无法事后翻译）；``PROPERTY_SCHEMAS`` 第 3 元素为
标签键，属性面板渲染时取词。
"""

import json
import os
import random
import time
from enum import Enum
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.blueprint import (
    BlueprintCanvas,
    BlueprintGraph,
    register_node_type,
)
from InstructionX_UIKit.blueprint.viewport import gl_available
from InstructionX_UIKit.components import Button
from InstructionX_UIKit.components.combo_box import ComboBox
from InstructionX_UIKit.components.slider import Slider
from InstructionX_UIKit.components.spin_box import SpinBox
from InstructionX_UIKit.theme import set_property

from core.interfaces import ILocalizationFacade

from .common import bind_tr, code_label, hint_label, title_label
from .playground import ParamForm

__all__ = ["create_page", "register_demo_node_types", "PROPERTY_SCHEMAS",
           "REGISTRY_OWNER"]

#: offscreen 下降级读写的 JSON 文件名（不弹文件对话框）
FALLBACK_JSON = "blueprint_demo.json"

#: offscreen 降级文件的存放目录（框架根 temp/ 下，避免污染仓库根目录；
#: 框架 .gitignore 已排除该目录）
_OFFSCREEN_FALLBACK_DIR = "temp"


class _RunState(Enum):
    """运行模拟状态机：空闲 / 连续运行中（QTimer 推进）/ 单步推进中。

    「单步」在 RUNNING 期间被忽略，防止与 QTimer 回调交错推进 ``_idx``
    导致节点状态 / 耗时徽标错乱；「运行」随时可重新开始。
    """
    IDLE = "idle"
    RUNNING = "running"
    STEPPING = "stepping"

# ---------------------------------------------------------------------------
# 节点属性 schema（右侧属性面板用；第 3 元素为取词键，渲染时翻译）
#   ("int",    key, 标签键, 默认, 最小, 最大)
#   ("float",  key, 标签键, 默认, 最小, 最大)
#   ("choice", key, 标签键, 默认, options)
#   ("text",   key, 标签键, 默认)
#   ("bool",   key, 标签键, 默认)
# ---------------------------------------------------------------------------
PROPERTY_SCHEMAS = {
    "load_image": [
        ("text", "path", "prop.file_path", "demo/input.png"),
        ("choice", "mode", "prop.mode", "RGB", ["RGB", "RGBA", "L"]),
    ],
    "noise": [
        ("int", "seed", "prop.seed", 42, 0, 99999),
        ("text", "shape", "prop.shape", "1x3x224x224"),
    ],
    "resize": [
        ("int", "width", "prop.width", 640, 16, 4096),
        ("int", "height", "prop.height", 480, 16, 4096),
        ("choice", "interpolation", "prop.interpolation", "bilinear",
         ["nearest", "bilinear", "bicubic", "lanczos"]),
    ],
    "normalize": [
        ("float", "mean", "prop.mean", 0.5, 0.0, 1.0),
        ("float", "std", "prop.std", 0.5, 0.01, 1.0),
    ],
    "gaussian_blur": [
        ("int", "radius", "prop.radius", 5, 0, 50),
    ],
    "edge_detect": [
        ("choice", "method", "prop.method", "sobel",
         ["sobel", "canny", "laplacian"]),
        ("int", "threshold", "prop.threshold", 128, 0, 255),
    ],
    "cnn": [
        ("int", "layers", "prop.layers", 18, 1, 200),
        ("int", "channels", "prop.channels", 64, 8, 1024),
    ],
    "transformer": [
        ("int", "layers", "prop.layers", 6, 1, 48),
        ("int", "heads", "prop.heads", 8, 1, 32),
    ],
    "fusion": [
        ("float", "weight", "prop.weight", 0.5, 0.0, 1.0),
    ],
    "save_result": [
        ("text", "path", "prop.output_path", "output/result.png"),
        ("choice", "format", "prop.format", "png", ["png", "jpg", "npy"]),
    ],
    "log_output": [
        ("choice", "level", "prop.level", "info",
         ["debug", "info", "warning", "error"]),
    ],
    "perf_probe": [
        ("int", "warn_ms", "prop.warn_ms", 500, 0, 100000),
        ("bool", "enabled", "prop.enabled", True),
    ],
}

#: 属性表单行构建分发表：kind → 向 ParamForm 追加对应控件
#: （参数：form, 标签, 当前值, spec 元组, 回调, 属性键）
_PROP_ADDERS = {
    "int": lambda f, lb, v, s, cb, k: f.add_int(lb, int(v), s[4], s[5],
                                                cb, key=k),
    "float": lambda f, lb, v, s, cb, k: f.add_float(lb, float(v), s[4], s[5],
                                                    cb, key=k),
    "choice": lambda f, lb, v, s, cb, k: f.add_choice(lb, list(s[4]), v,
                                                      cb, key=k),
    "bool": lambda f, lb, v, s, cb, k: f.add_bool(lb, bool(v), cb, key=k),
    "text": lambda f, lb, v, s, cb, k: f.add_text(lb, str(v), cb, key=k),
}


def _defaults(type_name: str) -> dict:
    """取某节点类型的属性默认值字典。"""
    return {spec[1]: spec[3] for spec in PROPERTY_SCHEMAS.get(type_name, [])}


def apply_defaults(node) -> None:
    """把 schema 默认属性以 setdefault 方式写入 ``node.properties``。"""
    for key, value in _defaults(node.type_name).items():
        node.properties.setdefault(key, value)


# ---------------------------------------------------------------------------
# body_builder：节点体内嵌属性编辑控件（写回 node.properties）
# 注：画布将节点体置为鼠标透明（避免与拖拽冲突），此处控件作展示用；
# 交互编辑由右侧属性面板完成。
# 行内标签在注册期取词：build_xxx_body(tr) 返回捕获 tr 的构建闭包。
# ---------------------------------------------------------------------------

def _mini_label(text: str) -> QLabel:
    lab = QLabel(text)
    set_property(lab, "role", "tertiary")
    return lab


def _body_row(container, label, widget) -> None:
    row = QWidget()
    row.setAttribute(Qt.WA_TransparentForMouseEvents, False)
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lay.addWidget(_mini_label(label))
    lay.addWidget(widget, 1)
    container.layout().addWidget(row)
    # sm 控件实际绘制约 24–26px 高；NodeWidget 依容器 sizeHint 计算
    # 节点体区高度，构造期 sizeHint 偏小会导致行重叠，故显式保底
    row.setMinimumHeight(26)


def _spin_row(node, container, label, key, lo, hi) -> None:
    """节点体内单行 SpinBox（写回 node.properties[key]）。"""
    spin = SpinBox(lo, hi, int(node.properties[key]), size="sm")
    spin.valueChanged.connect(lambda v: node.properties.__setitem__(key, int(v)))
    _body_row(container, label, spin)


def build_resize_body(tr):
    """Resize 节点体工厂：宽 / 高 SpinBox + 插值 ComboBox。"""

    def _build(node, container) -> None:
        apply_defaults(node)
        _spin_row(node, container, tr("body.width"), "width", 16, 4096)
        _spin_row(node, container, tr("body.height"), "height", 16, 4096)
        combo = ComboBox(size="sm")
        for item in ("nearest", "bilinear", "bicubic", "lanczos"):
            combo.addItem(item, item)
        combo.setCurrentIndex(
            max(0, combo.findData(node.properties["interpolation"])))
        combo.currentIndexChanged.connect(
            lambda i: node.properties.__setitem__("interpolation",
                                                  combo.itemData(i)))
        _body_row(container, tr("body.interpolation"), combo)
    return _build


def build_cnn_body(tr):
    """CNN 节点体工厂：层数 / 通道数 SpinBox。"""

    def _build(node, container) -> None:
        apply_defaults(node)
        _spin_row(node, container, tr("body.layers"), "layers", 1, 200)
        _spin_row(node, container, tr("body.channels"), "channels", 8, 1024)
    return _build


def build_blur_body(tr):
    """高斯模糊节点体工厂：半径 Slider。"""

    def _build(node, container) -> None:
        apply_defaults(node)
        slider = Slider(minimum=0, maximum=50,
                        value=int(node.properties["radius"]))
        slider.set_tip_enabled(False)
        slider.valueChanged.connect(
            lambda v: node.properties.__setitem__("radius", int(v)))
        _body_row(container, tr("body.radius"), slider)
    return _build


def build_transformer_body(tr):
    """Transformer 节点体工厂：层数 / 注意力头 SpinBox。"""

    def _build(node, container) -> None:
        apply_defaults(node)
        _spin_row(node, container, tr("body.layers"), "layers", 1, 48)
        _spin_row(node, container, tr("body.heads"), "heads", 1, 32)
    return _build


# ---------------------------------------------------------------------------
# 节点类型注册（owner 命名空间内覆盖式注册；注册时机在 create_page 内，
# 语言切换重建页面时以新语言重新注册即完成刷新）
# ---------------------------------------------------------------------------

#: 注册表命名空间标识（UIKit NodeRegistry owner）：本页节点类型注册 /
#: 画布创建均限定该空间，与其他插件（如 blueprint_opencv）同名类型
#: 互不覆盖
REGISTRY_OWNER = "ui-demo"


# 引脚名为节点定义的内部标识（NodeRegistry._same_definition 以引脚定义
# 比对判定重复注册），固定中文原名、不参与翻译——否则语言切换重注册时
# 引脚定义变化会触发「重复注册且引脚定义不同」的覆盖 WARNING
def _exec_in() -> dict:
    return {"id": "in", "name": "进入", "data_type": "exec"}


def _exec_out() -> dict:
    return {"id": "out", "name": "退出", "data_type": "exec"}


def _register_input_types(tr) -> None:
    """注册输入类节点类型（加载图像 / 随机噪声）。"""
    img = {"id": "img", "name": "图像", "data_type": "image"}
    register_node_type(
        "load_image", tr("node.load_image.name"), tr("node.cat.input"),
        inputs=[_exec_in()],
        outputs=[_exec_out(), dict(img)],
        accent="primary", description=tr("node.load_image.desc"),
        owner=REGISTRY_OWNER,
    )
    register_node_type(
        "noise", tr("node.noise.name"), tr("node.cat.input"),
        inputs=[_exec_in()],
        outputs=[_exec_out(),
                 {"id": "tensor", "name": "噪声",
                  "data_type": "tensor"}],
        accent="primary", description=tr("node.noise.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_geometry_types(tr) -> None:
    """注册几何 / 像素预处理节点类型（resize / 归一化）。"""
    img = {"id": "img", "name": "图像", "data_type": "image"}
    tensor = {"id": "tensor", "name": "张量", "data_type": "tensor"}
    register_node_type(
        "resize", tr("node.resize.name"), tr("node.cat.process"),
        inputs=[_exec_in(), dict(img)],
        outputs=[_exec_out(), dict(img)],
        accent="warning", body_builder=build_resize_body(tr),
        description=tr("node.resize.desc"),
        owner=REGISTRY_OWNER,
    )
    register_node_type(
        "normalize", tr("node.normalize.name"), tr("node.cat.process"),
        inputs=[_exec_in(), dict(img)],
        outputs=[_exec_out(), dict(tensor)],
        accent="warning", description=tr("node.normalize.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_filter_types(tr) -> None:
    """注册滤波类处理节点类型（高斯模糊 / 边缘检测）。"""
    img = {"id": "img", "name": "图像", "data_type": "image"}
    tensor = {"id": "tensor", "name": "张量", "data_type": "tensor"}
    register_node_type(
        "gaussian_blur", tr("node.gaussian_blur.name"), tr("node.cat.process"),
        inputs=[_exec_in(), dict(img)],
        outputs=[_exec_out(), dict(img)],
        accent="warning", body_builder=build_blur_body(tr),
        description=tr("node.gaussian_blur.desc"),
        owner=REGISTRY_OWNER,
    )
    register_node_type(
        "edge_detect", tr("node.edge_detect.name"), tr("node.cat.process"),
        inputs=[_exec_in(), dict(tensor)],
        outputs=[_exec_out(),
                 {"id": "img", "name": "边缘图", "data_type": "image"}],
        accent="warning", description=tr("node.edge_detect.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_backbone_type(tr, type_name, body_builder) -> None:
    """注册单个骨干模型节点类型（执行 + tensor 进、tensor 特征出）。"""
    tensor = {"id": "tensor", "name": "张量", "data_type": "tensor"}
    feature = {"id": "tensor", "name": "特征",
               "data_type": "tensor"}
    register_node_type(
        type_name, tr(f"node.{type_name}.name"), tr("node.cat.model"),
        inputs=[_exec_in(), tensor],
        outputs=[_exec_out(), feature],
        accent="danger", body_builder=body_builder,
        description=tr(f"node.{type_name}.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_backbone_types(tr) -> None:
    """注册骨干模型节点类型（CNN / Transformer，带属性编辑体）。"""
    _register_backbone_type(tr, "cnn", build_cnn_body(tr))
    _register_backbone_type(tr, "transformer", build_transformer_body(tr))


def _register_fusion_type(tr) -> None:
    """注册融合模型节点类型（两路 tensor 加权融合）。"""
    tensor_a = {"id": "tensor_a", "name": "张量 A",
                "data_type": "tensor"}
    tensor_b = {"id": "tensor_b", "name": "张量 B",
                "data_type": "tensor"}
    fused = {"id": "tensor", "name": "融合", "data_type": "tensor"}
    register_node_type(
        "fusion", tr("node.fusion.name"), tr("node.cat.model"),
        inputs=[_exec_in(), tensor_a, tensor_b],
        outputs=[_exec_out(), fused],
        accent="danger", description=tr("node.fusion.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_sink_types(tr) -> None:
    """注册输出汇节点类型（保存结果 / 日志输出）。"""
    img = {"id": "img", "name": "图像", "data_type": "image"}
    register_node_type(
        "save_result", tr("node.save_result.name"), tr("node.cat.output"),
        inputs=[_exec_in(), dict(img)],
        accent="success", description=tr("node.save_result.desc"),
        owner=REGISTRY_OWNER,
    )
    register_node_type(
        "log_output", tr("node.log_output.name"), tr("node.cat.output"),
        inputs=[_exec_in(),
                {"id": "msg", "name": "消息", "data_type": "any",
                 "multi": True}],
        accent="success", description=tr("node.log_output.desc"),
        owner=REGISTRY_OWNER,
    )


def _register_probe_type(tr) -> None:
    """注册工具节点类型（性能探针：观测透传）。"""
    any_in = {"id": "any_in", "name": "观测", "data_type": "any",
              "multi": True}
    any_out = {"id": "any_out", "name": "透传",
               "data_type": "any"}
    register_node_type(
        "perf_probe", tr("node.perf_probe.name"), tr("node.cat.util"),
        inputs=[_exec_in(), any_in],
        outputs=[_exec_out(), any_out],
        accent="#7A6FC0", description=tr("node.perf_probe.desc"),
        owner=REGISTRY_OWNER,
    )


def register_demo_node_types(tr=None) -> None:
    """注册 Demo 全部节点类型（分类：输入 / 处理 / 模型 / 输出 / 工具）。

    库内置 ``start``（流程）之外注册 12 种；其中 resize / cnn /
    gaussian_blur / transformer 带 ``body_builder`` 属性编辑体。
    全部注册在 ``REGISTRY_OWNER`` 命名空间内。

    参数:
        tr: 取词闭包（``bind_tr(i18n, "blueprint")``）；None 时按全局降级
            语义注册键名（供无取词门面的测试调用）。
    """
    if tr is None:
        tr = bind_tr(None, "blueprint")
    _register_input_types(tr)
    _register_geometry_types(tr)
    _register_filter_types(tr)
    _register_backbone_types(tr)
    _register_fusion_type(tr)
    _register_sink_types(tr)
    _register_probe_type(tr)


# ---------------------------------------------------------------------------
# exec 链拓扑排序
# ---------------------------------------------------------------------------

def _collect_exec_edges(graph: BlueprintGraph) -> list:
    """收集目标引脚为 ``exec`` 类型的边。"""
    exec_edges = []
    for edge in graph.edges():
        node = graph.node(edge.to_node)
        if node is None:
            continue
        pin = next((p for p in node.inputs if p.id == edge.to_pin), None)
        if pin is not None and pin.data_type == "exec":
            exec_edges.append(edge)
    return exec_edges


def _kahn_order(involved, indeg, adj) -> list:
    """Kahn 算法出队序列（入度 0 先入队，保持插入序稳定）。"""
    queue = [nid for nid in involved if indeg[nid] == 0]
    order = []
    while queue:
        nid = queue.pop(0)
        order.append(nid)
        for nxt in adj[nid]:
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                queue.append(nxt)
    return order


def _topo_sort(exec_edges) -> list:
    """对 exec 边涉及的节点做拓扑排序；有环时剩余按插入序兜底。"""
    involved = []
    for edge in exec_edges:
        for nid in (edge.from_node, edge.to_node):
            if nid not in involved:
                involved.append(nid)
    indeg = {nid: 0 for nid in involved}
    adj = {nid: [] for nid in involved}
    for edge in exec_edges:
        indeg[edge.to_node] += 1
        adj[edge.from_node].append(edge.to_node)
    order = _kahn_order(involved, indeg, adj)
    if len(order) != len(involved):  # 有环：剩余按插入序兜底
        order.extend(nid for nid in involved if nid not in order)
    return order


def exec_order(graph: BlueprintGraph) -> list:
    """按 exec 引脚连线做拓扑排序，返回节点 id 执行序列。

    只考虑目标引脚为 ``exec`` 类型的边；图中无 exec 边时回退为
    全部节点的插入序（保证「运行」总有可视反馈）。
    """
    exec_edges = _collect_exec_edges(graph)
    if not exec_edges:
        return [n.id for n in graph.nodes()]
    return _topo_sort(exec_edges)


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------

class BlueprintDemoPage(QWidget):
    """蓝图演示页：工具条 + 画布 + 右侧属性面板。

    公开属性（供测试 / 外部集成）：
        ``graph`` / ``canvas`` / ``status_label`` / ``panel_form``；
        ``delay_range``：运行模拟每节点随机耗时区间（ms），测试可置
        ``(0, 0)`` 加速。
    """

    def __init__(self, parent=None,
                 i18n: Optional[ILocalizationFacade] = None):
        super().__init__(parent)
        self._tr = bind_tr(i18n, "blueprint")
        self._init_run_state()
        self._init_graph_canvas()
        self._build_root_layout()
        self._init_timer_and_signals()
        self._build_preset()
        self._on_selection([])

    def _init_run_state(self) -> None:
        """初始化运行模拟状态（世代号用于 reset 后失效旧定时器回调）。"""
        self.delay_range = (200, 800)
        self._order = []
        self._idx = 0
        self._t0 = 0.0
        self._gen = 0          # 运行世代：reset 后使旧定时器回调失效
        self._step_total = 0.0
        self._state = _RunState.IDLE  # 运行模拟状态机（工具条按钮随其联动）

    def _init_graph_canvas(self) -> None:
        """构建图与画布；先接默认属性槽保证 NodeWidget 构建时 properties 已就位。"""
        self.graph = BlueprintGraph()
        self.graph.node_added.connect(apply_defaults)
        self.canvas = BlueprintCanvas(self.graph, self, owner=REGISTRY_OWNER)

    def _build_root_layout(self) -> None:
        """构建根布局：标题 / 提示 / 代码示例 / 工具条 / 后端状态行 / 主体。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(8)
        root.addWidget(title_label(self._tr("title")))
        root.addWidget(hint_label(self._tr("hint")))
        root.addWidget(code_label(
            'canvas = BlueprintCanvas(BlueprintGraph()); '
            'canvas.add_node_at("resize", QPointF(100, 80))'))
        root.addLayout(self._build_toolbar())
        root.addWidget(self._build_backend_label())
        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self.canvas, 1)
        body.addWidget(self._build_panel(), 0)
        root.addLayout(body, 1)

    def _init_timer_and_signals(self) -> None:
        """构建节点完成定时器并接线画布选中信号。"""
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._complete_node)
        self.canvas.selection_changed.connect(self._on_selection)

    # ------------------------------------------------------------------ 工具条
    def _build_toolbar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(8)
        defs = [("run_button", "toolbar.run", self.run_all, "primary"),
                ("step_button", "toolbar.step", self.step_once, None),
                ("reset_button", "toolbar.reset", self.reset_run, None),
                ("fit_button", "toolbar.fit", self.canvas.fit_view, None),
                ("save_button", "toolbar.save", self.save_json, None),
                ("load_button", "toolbar.load", self.load_json, None)]
        for attr, key, handler, variant in defs:
            kwargs = {"size": "sm"}
            if variant:
                kwargs["variant"] = variant
            btn = Button(self._tr(key), **kwargs)
            btn.clicked.connect(handler)
            setattr(self, attr, btn)
            bar.addWidget(btn)
        self.status_label = QLabel(self._tr("status.ready"))
        set_property(self.status_label, "role", "secondary")
        bar.addWidget(self.status_label, 1)
        return bar

    def _build_backend_label(self) -> QLabel:
        """渲染后端状态行：展示蓝图画布当前视口后端（GL / 软件）。

        与 ``create_viewport`` 的实际选择一致（同源 ``gl_available()``，
        模块级缓存只探测一次）；offscreen / 无 GL 驱动环境显示软件渲染。
        """
        backend_key = "backend.gl" if gl_available() else "backend.software"
        text = self._tr("backend.label", backend=self._tr(backend_key))
        self.backend_label = hint_label(text, role="tertiary")
        return self.backend_label

    # ------------------------------------------------------------------ 属性面板
    def _build_panel(self) -> QFrame:
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setFixedWidth(300)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(8)
        head = QLabel(self._tr("panel.title"))
        head_font = head.font()
        head_font.setBold(True)
        head.setFont(head_font)
        lay.addWidget(head)
        self._panel_host = QWidget()
        host_lay = QVBoxLayout(self._panel_host)
        host_lay.setContentsMargins(0, 0, 0, 0)
        host_lay.setSpacing(6)
        lay.addWidget(self._panel_host, 1)
        return panel

    def _clear_panel(self) -> None:
        lay = self._panel_host.layout()
        while lay.count():
            item = lay.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self.panel_form = None

    def _on_selection(self, node_ids) -> None:
        """选中变化 → 重建右侧属性面板（单选展示 + ParamForm 编辑）。"""
        self._clear_panel()
        lay = self._panel_host.layout()
        node = self.graph.node(node_ids[0]) if len(node_ids) == 1 else None
        if node is None:
            hint = hint_label(self._tr("panel.empty_hint"), role="tertiary")
            lay.addWidget(hint)
            lay.addStretch(1)
            return
        apply_defaults(node)
        self._fill_node_info(lay, node)

    def _fill_node_info(self, lay, node) -> None:
        """填充节点信息行 + 属性编辑表单。"""
        self._info(lay, self._tr("info.title", title=node.title))
        self._info(lay, self._tr("info.type", type=node.type_name, id=node.id),
                   role="tertiary")
        status = self._tr("info.status", status=node.status)
        if node.elapsed_ms is not None:
            # 前导空格为行内分隔，语言文件不保存首尾空白，故在代码中拼接
            status += "    " + self._tr("info.status_elapsed",
                                        ms=f"{node.elapsed_ms:.0f}")
        self._info(lay, status, role="tertiary")
        schema = PROPERTY_SCHEMAS.get(node.type_name)
        if not schema:
            self._info(lay, self._tr("panel.no_props"), role="tertiary")
            lay.addStretch(1)
            return
        lay.addWidget(self._build_prop_form(node, schema))
        lay.addStretch(1)

    def _info(self, lay, text, role="secondary") -> None:
        lab = QLabel(text)
        lab.setWordWrap(True)
        set_property(lab, "role", role)
        lay.addWidget(lab)

    def _build_prop_form(self, node, schema) -> ParamForm:
        """按 schema 构建属性编辑表单（标签键在此取词），写回 properties。"""
        form = ParamForm()
        for spec in schema:
            self._add_prop_row(form, node, spec)
        self.panel_form = form
        return form

    def _add_prop_row(self, form, node, spec) -> None:
        """按 spec 元组向表单追加一行属性控件（kind 经 _PROP_ADDERS 分发）。"""
        kind, key, label_key, default = spec[:4]
        value = node.properties.get(key, default)
        cb = (lambda v, n=node, k=key: self._set_prop(n, k, v))
        _PROP_ADDERS[kind](form, self._tr(label_key), value, spec, cb, key)

    def _set_prop(self, node, key, value) -> None:
        """属性面板写回 ``node.properties`` 并刷新节点外观。"""
        node.properties[key] = value
        node.changed.emit()

    # ------------------------------------------------------------------ 预置图
    def _build_preset(self) -> None:
        """开始→加载图像→预处理(归一化)→模型推理(CNN)→后处理(边缘检测)→保存。"""
        nodes = self._add_preset_nodes()
        self._link_preset_exec(nodes)
        self._link_preset_data(nodes)
        self.preset_ids = [n.id for n in nodes]

    def _add_preset_nodes(self) -> list:
        """按预置流水线位次创建 6 个节点，返回 [start, load, pre, cnn, post, save]。"""
        n_start = self.canvas.add_node_at("start", QPointF(40, 180))
        n_load = self.canvas.add_node_at("load_image", QPointF(300, 180))
        n_pre = self.canvas.add_node_at("normalize", QPointF(560, 180))
        n_pre.title = self._tr("preset.pre")
        n_cnn = self.canvas.add_node_at("cnn", QPointF(840, 180))
        n_cnn.title = self._tr("preset.infer")
        n_post = self.canvas.add_node_at("edge_detect", QPointF(1140, 180))
        n_post.title = self._tr("preset.post")
        n_save = self.canvas.add_node_at("save_result", QPointF(1440, 180))
        return [n_start, n_load, n_pre, n_cnn, n_post, n_save]

    def _link_preset_exec(self, nodes) -> None:
        """连接 exec 链（start→load→pre→cnn→post→save）。"""
        g = self.graph
        n_start, n_load, n_pre, n_cnn, n_post, n_save = nodes
        g.add_edge(n_start.id, "out", n_load.id, "in")
        g.add_edge(n_load.id, "out", n_pre.id, "in")
        g.add_edge(n_pre.id, "out", n_cnn.id, "in")
        g.add_edge(n_cnn.id, "out", n_post.id, "in")
        g.add_edge(n_post.id, "out", n_save.id, "in")

    def _link_preset_data(self, nodes) -> None:
        """连接数据引脚（image / tensor 混排）。"""
        g = self.graph
        _start, n_load, n_pre, n_cnn, n_post, n_save = nodes
        g.add_edge(n_load.id, "img", n_pre.id, "img")
        g.add_edge(n_pre.id, "tensor", n_cnn.id, "tensor")
        g.add_edge(n_cnn.id, "tensor", n_post.id, "tensor")
        g.add_edge(n_post.id, "img", n_save.id, "img")

    # ------------------------------------------------------------------ 运行模拟
    def _set_state(self, state: _RunState) -> None:
        """切换运行状态并联动工具条：连续运行进行中禁用「单步」。"""
        self._state = state
        self.step_button.setEnabled(state is not _RunState.RUNNING)

    def run_all(self) -> None:
        """「运行」：按 exec 链拓扑序，QTimer 逐节点模拟 200–800ms 随机耗时。"""
        self._set_state(_RunState.RUNNING)
        self._prepare_run()
        self._begin_node()

    def step_once(self) -> None:
        """「单步」：每次点击推进一个节点（立即完成，耗时取随机模拟值）。

        连续运行进行中忽略本次点击（按钮同步置灰），防止与 QTimer 回调
        交错推进 ``_idx`` 导致节点状态 / 耗时徽标错乱。
        """
        if self._state is _RunState.RUNNING:
            return
        if not self._order or self._idx >= len(self._order):
            self._set_state(_RunState.STEPPING)
            self._prepare_run()
            self._step_total = 0.0
        ex = self.canvas.execution()
        nid = self._order[self._idx]
        ms = float(random.randint(*self.delay_range))
        ex.start(nid)
        ex.finish(nid, ms)
        self._step_total += ms
        self._idx += 1
        self._after_node(ms)
        if self._idx >= len(self._order):
            self._set_state(_RunState.IDLE)

    def reset_run(self) -> None:
        """「重置」：中断进行中的模拟，全部节点回 idle。"""
        self._set_state(_RunState.IDLE)
        self._gen += 1
        self._timer.stop()
        self._order = []
        self._idx = 0
        self.canvas.execution().reset()
        self.status_label.setText(self._tr("status.ready"))

    def _prepare_run(self) -> None:
        self._gen += 1
        self.canvas.execution().reset()
        self._order = exec_order(self.graph)
        self._idx = 0
        self._t0 = time.perf_counter()
        self.canvas.execution().set_path(self._order)

    def _begin_node(self) -> None:
        if self._idx >= len(self._order):
            return
        nid = self._order[self._idx]
        self.canvas.execution().start(nid)
        gen = self._gen
        delay = random.randint(*self.delay_range)
        self.status_label.setText(
            self._tr("status.running", cur=self._idx + 1,
                     total=len(self._order)))
        self._timer.start(delay)
        self._timer.setProperty("gen", gen)

    def _complete_node(self) -> None:
        if self._timer.property("gen") != self._gen:
            return  # 已被重置 / 新一轮取代
        nid = self._order[self._idx]
        self.canvas.execution().finish(nid)  # 缺省自动计时
        self._idx += 1
        node = self.graph.node(nid)
        self._after_node(node.elapsed_ms if node is not None else 0.0)
        if self._idx < len(self._order):
            self._begin_node()
        else:
            self._set_state(_RunState.IDLE)

    def _after_node(self, _ms: float) -> None:
        if self._idx >= len(self._order) and self._order:
            if self._state is _RunState.STEPPING:
                total = self._step_total  # 单步：累计模拟耗时
            else:
                total = (time.perf_counter() - self._t0) * 1000.0
            self.status_label.setText(
                self._tr("status.done", count=len(self._order),
                         ms=f"{total:.0f}"))
        if self.canvas.selected_nodes():
            self._on_selection(self.canvas.selected_nodes())

    # ------------------------------------------------------------------ 序列化
    def _json_path(self, save: bool) -> str:
        """取 JSON 路径：offscreen 降级为框架根 temp/ 下固定文件，否则弹文件对话框。"""
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            # 仅 offscreen 自动化测试路径触发（真实运行弹文件对话框）；
            # 写 temp/ 而非 cwd，避免在框架根目录散落演示产物
            fallback_dir = Path.cwd() / _OFFSCREEN_FALLBACK_DIR
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return str(fallback_dir / FALLBACK_JSON)
        if save:
            path, _ = QFileDialog.getSaveFileName(
                self, self._tr("dlg.save"), FALLBACK_JSON, self._tr("dlg.filter"))
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, self._tr("dlg.load"), "", self._tr("dlg.filter"))
        return path

    def save_json(self) -> None:
        """保存整张图（含位置与 zoom/offset）到 JSON。"""
        path = self._json_path(save=True)
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self.canvas.to_dict(), fh,
                          ensure_ascii=False, indent=2)
        except OSError as exc:
            self.status_label.setText(self._tr("status.save_fail", error=exc))
            return
        self.status_label.setText(self._tr("status.saved", path=path))

    def load_json(self) -> None:
        """从 JSON 恢复整张图（节点 / 边 / 视图状态）。"""
        path = self._json_path(save=False)
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            self.status_label.setText(self._tr("status.load_fail", error=exc))
            return
        self.reset_run()
        self.canvas.from_dict(data)
        self.canvas.fit_view()
        self.status_label.setText(
            self._tr("status.loaded", path=path,
                     nodes=len(self.graph.nodes()),
                     edges=len(self.graph.edges())))


def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """页面工厂：以当前语言注册节点类型并返回蓝图演示页。"""
    register_demo_node_types(bind_tr(i18n, "blueprint"))
    return BlueprintDemoPage(i18n=i18n)
