# -*- coding: utf-8 -*-
"""主界面组装（ui 层）。

``MainWidget`` = 工具条 + 左侧固定宽面板（上：蓝图存档列表；下：节点列表）
+ ``BlueprintCanvas`` + 右侧固定宽面板（上：参数面板；下：ImageView 预览区
+ 结果信息标签）。

职责边界：
- 只做视图组装与事件分发，业务动作全部委托 ``BlueprintOpenCVService``
  （run/stop/save/load/存档管理，签名见 SPEC §7 与 SPEC-graph-list §3.1），
  槽函数直接转发、≤5 行；
- service 的 Qt 信号（``preview_ready`` / ``node_status_changed`` /
  ``run_finished``）由工作线程自动排队到 UI 线程的槽中执行，
  QPixmap 只在预览面板的 UI 线程槽里创建（SPEC §1.3）；
- ``node_status_changed`` 驱动 ``canvas.execution()`` 的
  start / finish / fail，并按已执行节点序列 ``set_path`` 高亮路径；
- 启动加载：存在 default 存档则恢复它，否则构建预置示例图
  （start→load_image→gaussian_blur→canny→preview，SPEC-graph-list §1.5）。
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.blueprint import BlueprintCanvas, BlueprintGraph
from InstructionX_UIKit.theme import set_property

from utils.logging_tools import LoggerManager, get_name

from .graph_list_panel import GraphListPanel
from .node_bootstrap import apply_catalog_defaults, ensure_node_types_registered
from .node_list_panel import NodeListPanel
from .preview_panel import PreviewPanel
from .property_panel import PropertyPanel
from .toolbar import ToolBar

__all__ = ["MainWidget"]

#: 右侧固定面板宽兜底值（SPEC §8 panel.right_panel_width = 320；
#: 实际取值优先读 config/default.json，配置缺失 / 损坏时回退本常量）
_FALLBACK_RIGHT_PANEL_WIDTH = 320
#: 插件默认配置文件路径（panel.right_panel_width 等，SPEC §8）
_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.json"
#: 左侧节点列表面板固定宽（SPEC-node-list-panel §3.3；与右侧 320px 面板对称）
_LEFT_PANEL_WIDTH = 200
#: 预置示例图节点（type_name, 场景坐标）：start→加载→高斯→Canny→预览
#: （load_image 节点体展示长文件路径会明显变宽，其后预留 700 间距不重叠）
_PRESET_NODES = (
    ("start", (40.0, 180.0)),
    ("load_image", (440.0, 180.0)),
    ("gaussian_blur", (1140.0, 180.0)),
    ("canny", (1540.0, 180.0)),
    ("preview", (1940.0, 180.0)),
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
#: 另存为命名对话框文案
_SAVE_AS_TITLE = "另存为蓝图"
_SAVE_AS_LABEL = "存档名称："
#: 重名覆盖确认对话框文案
_OVERWRITE_TITLE = "覆盖存档"
_OVERWRITE_TEXT = "已存在同名存档「{name}」，确定覆盖吗？"
#: 启动自动加载的默认存档名（与 service.load_graph 的缺省 name 一致）
_DEFAULT_GRAPH_NAME = "default"

_logger = LoggerManager()
_MODULE = get_name()


def _load_right_panel_width() -> int:
    """读取 config/default.json 的 panel.right_panel_width（SPEC §8 配置为准）。

    配置缺失 / 损坏 / 键不存在时记 WARNING 并回退 320（SPEC 约定值）。
    """
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            return int(json.load(f)["panel"]["right_panel_width"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        _logger.warning(
            _MODULE,
            f"读取面板宽度配置失败（回退 {_FALLBACK_RIGHT_PANEL_WIDTH}px）: {e}")
        return _FALLBACK_RIGHT_PANEL_WIDTH


#: 右侧固定面板宽（配置层接管，见 _load_right_panel_width）
_RIGHT_PANEL_WIDTH = _load_right_panel_width()

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
        ``node_list_panel`` / ``graph_list_panel``：左侧节点 / 存档列表
            面板（测试断言用）；
        ``graph_snapshot()``：当前图序列化 dict（service 取快照用）；
        ``restore_graph(data)``：把图 dict 恢复到画布；
        ``build_preset_graph()``：构建预置示例图。
    """

    def __init__(self, service, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlueprintOpenCVWidget")
        self._service = service
        self._run_order: List[str] = []
        #: 当前蓝图对应的存档名（未保存过的新图 / 预置图为 None，
        #: 「保存」按钮据此决定覆盖写入还是退化为另存为）
        self._current_graph_name: Optional[str] = None
        self.graph = BlueprintGraph()
        self.graph.node_added.connect(apply_catalog_defaults)
        self.canvas = BlueprintCanvas(self.graph, self)
        self._toolbar = ToolBar(self)
        self.graph_list_panel = GraphListPanel(service)
        self.node_list_panel = NodeListPanel(self.graph, self.canvas)
        self._property_panel = PropertyPanel()
        self._preview_panel = PreviewPanel()
        self._build_layout()
        self._connect_signals()
        self._load_initial_graph()

    # ------------------------------------------------------------------ 对外
    def showEvent(self, event) -> None:
        """控件可见时重新断言节点注册（幂等，见 node_bootstrap 模块 docstring）。

        NodeRegistry 是全局单例，用户切换到其他插件页面（如 ui_demo
        蓝图演示页）可能覆盖同名类型；本控件再次可见时纠正注册，
        保证随后经创建菜单新增的节点引脚契约正确。同时触发节点体区
        重排（见 _refresh_node_bodies）。
        """
        super().showEvent(event)
        ensure_node_types_registered()
        self._refresh_node_bodies()

    def _refresh_node_bodies(self) -> None:
        """触发全部节点重排，修正体区（body_builder 控件）初始错位。

        NodeWidget 在父控件未显示时 isVisible() 为 False，构造期的
        _relayout 不会给体区控件落位（几何停在 (0,0)，叠在标题栏上）；
        控件显示后借 node.changed 触发一次重排即可纠正。对无体区的
        节点这只是无害的重绘。
        """
        for node in self.graph.nodes():
            node.changed.emit()

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
        """根布局：顶部工具条，主体左侧面板（蓝图+节点）+ 画布 + 右侧面板。"""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(self._toolbar)
        body = QHBoxLayout()
        body.setSpacing(8)
        body.addWidget(self._build_left_panel())
        body.addWidget(self.canvas, 1)
        body.addWidget(self._build_right_panel())
        root.addLayout(body, 1)

    def _build_left_panel(self) -> QFrame:
        """左侧固定宽面板：上「蓝图」存档列表、下「节点」节点列表（2:3）。"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setFixedWidth(_LEFT_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(self._section_title("蓝图"))
        layout.addWidget(self.graph_list_panel, 2)
        layout.addWidget(self._section_title("节点"))
        layout.addWidget(self.node_list_panel, 3)
        return panel

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
        """连接工具条 / 画布 / 存档列表 / service 信号到对应槽（全部 UI 线程）。"""
        self._toolbar.run_requested.connect(self._run_pipeline)
        self._toolbar.stop_requested.connect(self._stop_pipeline)
        self._toolbar.save_current_requested.connect(self._save_graph)
        self._toolbar.save_requested.connect(self._save_graph_as)
        self._toolbar.fit_requested.connect(self.canvas.fit_view)
        self.graph_list_panel.save_as_requested.connect(self._save_graph_as)
        self.graph_list_panel.load_requested.connect(self._load_graph_by_name)
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
        """保存：覆盖写入当前存档；无当前存档（新图/预置图）退化为另存为。"""
        if self._current_graph_name is None:
            self._save_graph_as()
            return
        self._persist_graph(self._current_graph_name)

    def _save_graph_as(self) -> None:
        """另存为：命名对话框 → 重名覆盖确认 → 委托 service 持久化。"""
        name = self._prompt_graph_name()
        if name is None or not self._confirm_overwrite(name):
            return
        if self._persist_graph(name):
            self._current_graph_name = name

    def _persist_graph(self, name: str) -> bool:
        """推快照并委托 service 保存，成功刷新列表与状态；返回是否成功。"""
        self._push_graph_snapshot()
        result = self._service.save_graph(name)
        if not result.get("success"):
            self._report_failure("保存失败", result)
            return False
        self.graph_list_panel.refresh()
        count = result.get("data", {}).get("node_count", len(self.graph.nodes()))
        self._toolbar.set_status(f"已保存「{name}」（{count} 个节点）")
        return True

    def _prompt_graph_name(self) -> Optional[str]:
        """弹存档命名对话框；取消或空名返回 None。"""
        name, ok = QInputDialog.getText(self, _SAVE_AS_TITLE, _SAVE_AS_LABEL)
        if not ok or not name.strip():
            return None
        return name.strip()

    def _confirm_overwrite(self, name: str) -> bool:
        """重名时弹覆盖确认；不重名或用户确认返回 True。"""
        result = self._service.list_graphs()
        names = {meta.get("name")
                 for meta in result.get("data", {}).get("graphs", [])}
        if name not in names:
            return True
        answer = QMessageBox.question(
            self, _OVERWRITE_TITLE, _OVERWRITE_TEXT.format(name=name))
        return answer == QMessageBox.StandardButton.Yes

    def _load_graph_by_name(self, name: str) -> None:
        """加载指定存档：委托 service 恢复，成功后取回图 dict 刷新画布。"""
        result = self._service.load_graph(name)
        if not result.get("success"):
            self._report_failure("加载失败", result)
            return
        data = self._pull_graph_snapshot()
        if data is None:
            self._toolbar.set_status("加载成功，但未能取回图数据（见日志）")
            return
        self.restore_graph(data)
        fallback = bool(result.get("data", {}).get("fallback"))
        self._current_graph_name = None if fallback else name
        suffix = "（存档缺失 / 损坏，已回退示例图）" if fallback else ""
        self._toolbar.set_status(f"已加载「{name}」{suffix}")

    def _load_initial_graph(self) -> None:
        """启动加载：存在 default 存档则恢复，否则构建预置示例图（既有回退）。"""
        result = self._service.load_graph()
        loaded = result.get("success") and not result.get(
            "data", {}).get("fallback")
        if loaded:
            self.restore_graph(self._service.current_graph)
            self._current_graph_name = _DEFAULT_GRAPH_NAME
            return
        self.build_preset_graph()

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
        """把当前图快照推给 service（``update_graph``，service 层补充接口）。

        SPEC §7 的 service_api 未含图快照入参，而 §4.1 要求运行前取
        ``canvas.to_dict()`` 快照；service.update_graph 同步快照到
        service 与 PipelineController，保存 / 运行以此为数据源。
        """
        self._service.update_graph(self.graph_snapshot())

    def _pull_graph_snapshot(self) -> Optional[Dict[str, Any]]:
        """从 service 取回已加载的图 dict（``current_graph`` 属性）。"""
        graph = getattr(self._service, "current_graph", None)
        if not isinstance(graph, dict):
            _logger.warning(_MODULE, "service 缺少 current_graph 属性，无法取回图数据")
            return None
        return graph

    def _report_failure(self, title: str, result: Dict[str, Any]) -> None:
        """操作失败：中文弹窗告知 + ERROR 日志（面向用户的错误两者都要）。"""
        reason = result.get("error", "未知错误")
        _logger.error(_MODULE, f"{title}：{reason}")
        QMessageBox.warning(self, title, str(reason))
        self._toolbar.set_status(f"{title}：{reason}")
