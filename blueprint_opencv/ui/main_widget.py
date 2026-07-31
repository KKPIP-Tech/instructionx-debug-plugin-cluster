# -*- coding: utf-8 -*-
"""主界面组装（ui 层）。

``MainWidget`` = 工具条 + ``BlueprintCanvas`` + 右侧固定宽面板
（上：参数面板；下：ImageView 预览区 + 结果信息标签）。

职责边界：
- 只做视图组装与事件分发，业务动作全部委托 ``BlueprintOpenCVService``
  （run/stop/save/load，签名见 SPEC §7），槽函数直接转发、≤5 行；
- service 的 Qt 信号（``preview_ready`` / ``node_status_changed`` /
  ``run_finished``）由工作线程自动排队到 UI 线程的槽中执行，
  QPixmap 只在预览面板的 UI 线程槽里创建（SPEC §1.3）；
- ``node_status_changed`` 驱动 ``canvas.execution()`` 的
  start / finish / fail，并按已执行节点序列 ``set_path`` 高亮路径；
- 预置示例图：start→load_image→gaussian_blur→canny→preview
  （exec 链 + image 链），图加载 / 恢复前的开箱内容。
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.blueprint import BlueprintCanvas, BlueprintGraph
from InstructionX_UIKit.theme import set_property

from utils.logging_tools import LoggerManager, get_name

from .node_bootstrap import apply_catalog_defaults, ensure_node_types_registered
from .preview_panel import PreviewPanel
from .property_panel import PropertyPanel
from .toolbar import ToolBar

__all__ = ["MainWidget"]

#: 右侧固定面板宽（本插件分工契约 300px；SPEC §8 配置 320 由配置层接管后覆盖）
_RIGHT_PANEL_WIDTH = 300
#: 预置示例图节点（type_name, 场景坐标）：start→加载→高斯→Canny→预览
_PRESET_NODES = (
    ("start", (40.0, 180.0)),
    ("load_image", (300.0, 180.0)),
    ("gaussian_blur", (560.0, 180.0)),
    ("canny", (840.0, 180.0)),
    ("preview", (1120.0, 180.0)),
)
#: 库内置 start 节点的 exec 输出引脚 id 为 "out"（见 UIKit blueprint/registry.py），
#: 其余节点按 SPEC §3.0 约定为 exec_in / exec_out、image_in / image_out
_START_EXEC_OUT_PIN = "out"
_EXEC_IN_PIN = "exec_in"
_EXEC_OUT_PIN = "exec_out"
_IMAGE_IN_PIN = "image_in"
_IMAGE_OUT_PIN = "image_out"
#: 预置示例输入图（load_image 节点默认 file_path；资产由 B6 批次提供）
_SAMPLE_IMAGE_PATH = Path(__file__).resolve().parents[1] / "assets" / "sample.png"
#: 预置图中 load_image 节点的文件路径参数键
_FILE_PATH_KEY = "file_path"
#: 状态标签文案
_STATUS_READY = "就绪"
_STATUS_STOPPING = "正在停止（当前节点执行完后中断）…"

_logger = LoggerManager()
_MODULE = get_name()

# 模块级幂等注册：把 function.node_catalog 的节点定义注册进 UIKit
# （先查后注册，热重载重复 import 不产生重复项，SPEC §1.5）
ensure_node_types_registered()


class MainWidget(QWidget):
    """Blueprint OpenCV 插件主控件。

    参数:
        service: ``BlueprintOpenCVService`` 实例（SPEC §7 契约：
            run_pipeline / stop_pipeline / save_graph / load_graph
            及 preview_ready / node_status_changed / run_finished 信号）。
        parent: 父控件。

    公开属性 / 方法:
        ``graph`` / ``canvas``：数据图与画布（供 entrance / 测试访问）；
        ``graph_snapshot()``：当前图序列化 dict（service 取快照用）；
        ``restore_graph(data)``：把图 dict 恢复到画布；
        ``build_preset_graph()``：构建预置示例图。
    """

    def __init__(self, service, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlueprintOpenCVWidget")
        self._service = service
        self._run_order: List[str] = []
        self.graph = BlueprintGraph()
        self.graph.node_added.connect(apply_catalog_defaults)
        self.canvas = BlueprintCanvas(self.graph, self)
        self._toolbar = ToolBar(self)
        self._property_panel = PropertyPanel()
        self._preview_panel = PreviewPanel()
        self._build_layout()
        self._connect_signals()
        if not self.graph.nodes():
            self.build_preset_graph()

    # ------------------------------------------------------------------ 对外
    def graph_snapshot(self) -> Dict[str, Any]:
        """当前图快照（``canvas.to_dict()``，含节点属性 / 边 / 视图状态）。"""
        return self.canvas.to_dict()

    def restore_graph(self, data: Dict[str, Any]) -> None:
        """把序列化图恢复到画布：复位运行指示、重建节点 / 边并适应视图。"""
        self.canvas.execution().reset()
        self.canvas.from_dict(data)
        self.canvas.fit_view()
        self._property_panel.clear()
        self._preview_panel.show_empty()

    def build_preset_graph(self) -> None:
        """构建预置示例图：exec 链与 image 链双线连接（SPEC 分工契约）。"""
        nodes = [self.canvas.add_node_at(t, QPointF(x, y))
                 for t, (x, y) in _PRESET_NODES]
        for upstream, downstream in zip(nodes, nodes[1:]):
            out_pin = (_START_EXEC_OUT_PIN if upstream.type_name == "start"
                       else _EXEC_OUT_PIN)
            self.graph.add_edge(upstream.id, out_pin, downstream.id, _EXEC_IN_PIN)
        for upstream, downstream in zip(nodes[1:], nodes[2:]):
            self.graph.add_edge(upstream.id, _IMAGE_OUT_PIN,
                                downstream.id, _IMAGE_IN_PIN)
        nodes[1].properties[_FILE_PATH_KEY] = str(_SAMPLE_IMAGE_PATH)
        nodes[1].changed.emit()

    # ------------------------------------------------------------------ 组装
    def _build_layout(self) -> None:
        """根布局：顶部工具条，主体左画布 + 右侧固定宽面板。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._toolbar)
        body = QHBoxLayout()
        body.setSpacing(8)
        body.addWidget(self.canvas, 1)
        body.addWidget(self._build_right_panel())
        root.addLayout(body, 1)

    def _build_right_panel(self) -> QFrame:
        """右侧固定宽面板：上参数面板、下预览区（含小标题）。"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setFixedWidth(_RIGHT_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(self._section_title("参数"))
        layout.addWidget(self._property_panel, 3)
        layout.addWidget(self._section_title("预览"))
        layout.addWidget(self._preview_panel, 2)
        return panel

    def _section_title(self, text: str) -> QLabel:
        """面板分区小标题（加粗）。"""
        label = QLabel(text)
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        return label

    def _connect_signals(self) -> None:
        """连接工具条 / 画布 / service 信号到对应槽（全部 UI 线程）。"""
        self._toolbar.run_requested.connect(self._run_pipeline)
        self._toolbar.stop_requested.connect(self._stop_pipeline)
        self._toolbar.save_requested.connect(self._save_graph)
        self._toolbar.load_requested.connect(self._load_graph)
        self._toolbar.fit_requested.connect(self.canvas.fit_view)
        self.canvas.selection_changed.connect(self._on_selection_changed)
        self._service.preview_ready.connect(self._on_preview_ready)
        self._service.node_status_changed.connect(self._on_node_status)
        self._service.run_finished.connect(self._on_run_finished)

    # ------------------------------------------------------------------ 工具条动作（委托 service）
    def _run_pipeline(self) -> None:
        """运行：先推图快照给 service，再触发异步运行（工作线程执行）。"""
        self._push_graph_snapshot()
        result = self._service.run_pipeline()
        if not result.get("success"):
            self._report_failure("运行失败", result)
            return
        self.canvas.execution().reset()
        self._run_order = []
        self._toolbar.set_running(True)
        self._toolbar.set_status("运行中…")

    def _stop_pipeline(self) -> None:
        """停止：协作式中断请求，结果由 run_finished 汇总上报。"""
        result = self._service.stop_pipeline()
        if result.get("success"):
            self._toolbar.set_status(_STATUS_STOPPING)

    def _save_graph(self) -> None:
        """保存图：推快照后委托 service 持久化（DataProvider）。"""
        self._push_graph_snapshot()
        result = self._service.save_graph()
        if not result.get("success"):
            self._report_failure("保存失败", result)
            return
        count = result.get("data", {}).get("node_count", len(self.graph.nodes()))
        self._toolbar.set_status(f"已保存（{count} 个节点）")

    def _load_graph(self) -> None:
        """加载图：委托 service 恢复，成功后取回图 dict 刷新画布。"""
        result = self._service.load_graph()
        if not result.get("success"):
            self._report_failure("加载失败", result)
            return
        data = self._pull_graph_snapshot()
        if data is None:
            self._toolbar.set_status("加载成功，但未能取回图数据（见日志）")
            return
        self.restore_graph(data)
        suffix = "（存档缺失 / 损坏，已回退示例图）" if result.get(
            "data", {}).get("fallback") else ""
        self._toolbar.set_status(f"已加载{suffix}")

    # ------------------------------------------------------------------ service 信号槽
    def _on_preview_ready(self, png_bytes: bytes, info: Dict[str, Any]) -> None:
        """preview 节点结果（UI 线程槽）：交给预览面板解码显示。"""
        self._preview_panel.show_result(png_bytes, info)

    def _on_node_status(self, node_id: str, status: str,
                        elapsed_ms: float, message: str) -> None:
        """节点状态 → 画布运行指示：start / finish / fail + 路径高亮。"""
        execution = self.canvas.execution()
        if status == "running":
            self._run_order.append(node_id)
            execution.set_path(list(self._run_order))
            execution.start(node_id)
        elif status == "done":
            execution.finish(node_id, elapsed_ms)
        elif status == "error":
            execution.fail(node_id, message)

    def _on_run_finished(self, summary: Dict[str, Any]) -> None:
        """运行汇总 → 状态标签（节点数 / 总耗时 / 错误摘要）并恢复按钮态。"""
        self._toolbar.set_running(False)
        status = summary.get("status", "done")
        total_ms = float(summary.get("total_ms", 0.0))
        count = int(summary.get("node_count", 0))
        if status == "done":
            self._toolbar.set_status(f"运行完成：{count} 个节点 · 总耗时 {total_ms:.0f} ms")
            return
        errors = summary.get("errors") or []
        reason = errors[0] if errors else "未知错误"
        _logger.error(_MODULE, f"管线运行失败：{reason}")
        self._toolbar.set_status(f"运行中断：{reason}")

    def _on_selection_changed(self, node_ids: List[str]) -> None:
        """选中变化 → 参数面板：单选绑定节点，否则回提示态。"""
        node = self.graph.node(node_ids[0]) if len(node_ids) == 1 else None
        self._property_panel.bind_node(node)

    # ------------------------------------------------------------------ 内部
    def _push_graph_snapshot(self) -> None:
        """把当前图快照推给 service（``update_graph`` 为 service 层补充接口）。

        SPEC §7 的 service_api 未含图快照入参，而 §4.1 要求运行前取
        ``canvas.to_dict()`` 快照；此处按 service 层的 ``update_graph``
        补充方法对接，缺失时记 WARNING（service 层落地后自然生效）。
        """
        updater = getattr(self._service, "update_graph", None)
        if callable(updater):
            updater(self.graph_snapshot())
        else:
            _logger.warning(_MODULE, "service 缺少 update_graph 方法，图快照未同步")

    def _pull_graph_snapshot(self) -> Optional[Dict[str, Any]]:
        """从 service 取回已加载的图 dict（``get_graph_dict`` 补充接口）。"""
        getter = getattr(self._service, "get_graph_dict", None)
        if callable(getter):
            return getter()
        _logger.warning(_MODULE, "service 缺少 get_graph_dict 方法，无法取回图数据")
        return None

    def _report_failure(self, title: str, result: Dict[str, Any]) -> None:
        """操作失败：中文弹窗告知 + ERROR 日志（面向用户的错误两者都要）。"""
        reason = result.get("error", "未知错误")
        _logger.error(_MODULE, f"{title}：{reason}")
        QMessageBox.warning(self, title, str(reason))
        self._toolbar.set_status(f"{title}：{reason}")
