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

from core.i18n import get_language_manager
from core.interfaces import ILocalizationFacade
from utils.logging_tools import LoggerManager, get_name

from . import plugin_config
from .graph_list_panel import GraphListPanel
from .node_bootstrap import (
    REGISTRY_OWNER,
    apply_catalog_defaults,
    ensure_node_types_registered,
)
from .node_list_panel import NodeListPanel
from .preview_panel import PreviewPanel
from .property_panel import PropertyPanel
from .toolbar import ToolBar

__all__ = ["MainWidget"]

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
#: 预置图中 load_image 节点的文件路径参数键
_FILE_PATH_KEY = "file_path"
#: 启动自动加载的默认存档名（与 service.load_graph 的缺省 name 一致）
_DEFAULT_GRAPH_NAME = "default"
#: 取词分组名（与 text/zh.xml 一致）
_GROUP_MAIN = "main"
_GROUP_PANEL = "panel"
_GROUP_TOOLBAR = "toolbar"

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
        i18n: 插件取词门面（可选；未注入时界面显示键名兜底，
            正常加载路径框架始终注入）。
        plugin_id: 插件 UUID（可选；用于比对 plugin_language_changed
            信号，缺省时框架语言切换仍可刷新）。

    公开属性 / 方法:
        ``graph`` / ``canvas``：数据图与画布（供 entrance / 测试访问）；
        ``node_list_panel`` / ``graph_list_panel``：左侧节点 / 存档列表
            面板（测试断言用）；
        ``graph_snapshot()``：当前图序列化 dict（service 取快照用）；
        ``restore_graph(data)``：把图 dict 恢复到画布；
        ``build_preset_graph()``：构建预置示例图。
    """

    def __init__(self, service, parent: QWidget = None,
                 i18n: Optional[ILocalizationFacade] = None,
                 plugin_id: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BlueprintOpenCVWidget")
        self._service = service
        self._i18n = i18n
        self._plugin_id = plugin_id
        # 配置透传：graph.max_nodes → 共享运行实例（service 内部方法）
        self._service.set_max_nodes(plugin_config.graph_max_nodes())
        self._run_order: List[str] = []
        #: 面板分区小标题（panel 组键 → 标签，语言切换时统一重设）
        self._section_labels: Dict[str, QLabel] = {}
        #: 当前蓝图对应的存档名（未保存过的新图 / 预置图为 None，
        #: 「保存」按钮据此决定覆盖写入还是退化为另存为）
        self._current_graph_name: Optional[str] = None
        self.graph = BlueprintGraph()
        self.graph.node_added.connect(apply_catalog_defaults)
        self.canvas = BlueprintCanvas(self.graph, self, owner=REGISTRY_OWNER)
        self._build_panels()
        self._build_layout()
        self._connect_signals()
        self._load_initial_graph()

    def _build_panels(self) -> None:
        """创建工具条与四个子面板（i18n 门面逐级下传）。"""
        self._toolbar = ToolBar(self, i18n=self._i18n)
        self.graph_list_panel = GraphListPanel(self._service, i18n=self._i18n)
        self.node_list_panel = NodeListPanel(self.graph, self.canvas,
                                             i18n=self._i18n)
        self._property_panel = PropertyPanel(i18n=self._i18n)
        self._preview_panel = PreviewPanel(i18n=self._i18n)

    def _tr(self, group: str, key: str, /, **params) -> str:
        """取插件文案；门面未注入时优雅降级返回键名（正常加载始终注入）。"""
        if self._i18n is None:
            return key
        return self._i18n.tr(group, key, **params)

    # ------------------------------------------------------------------ 对外
    def showEvent(self, event) -> None:
        """控件可见时重新断言节点注册（幂等，见 node_bootstrap 模块 docstring）。

        节点注册已限定本插件 owner 命名空间，跨插件同名类型不再互相
        覆盖；此处重复断言仅作同空间防御（自身旧版注册 / 异常写入），
        保证随后经创建菜单新增的节点引脚契约正确。同时触发节点体区
        重排（见 _refresh_node_bodies）。注册按当前语言取词，使首次
        显示即为有效语言。
        """
        super().showEvent(event)
        ensure_node_types_registered(self._i18n)
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
        nodes[1].properties[_FILE_PATH_KEY] = str(
            plugin_config.sample_image_path())
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
        # 画布最小宽（panel.min_canvas_width 配置，防压缩至不可操作）
        self.canvas.setMinimumWidth(plugin_config.min_canvas_width())
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
        layout.addWidget(self._section_title("section.graphs"))
        layout.addWidget(self.graph_list_panel, 2)
        layout.addWidget(self._section_title("section.nodes"))
        layout.addWidget(self.node_list_panel, 3)
        return panel

    def _build_right_panel(self) -> QFrame:
        """右侧固定宽面板：上参数面板、下预览区（含小标题）。"""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        panel.setFixedWidth(plugin_config.right_panel_width())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        layout.addWidget(self._section_title("section.params"))
        layout.addWidget(self._property_panel, 3)
        layout.addWidget(self._section_title("section.preview"))
        layout.addWidget(self._preview_panel, 2)
        return panel

    def _section_title(self, key: str) -> QLabel:
        """面板分区小标题（加粗）；按 panel 组键取词并登记供重翻译。"""
        label = QLabel(self._tr(_GROUP_PANEL, key))
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        self._section_labels[key] = label
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
        self._connect_language_signals()

    def _connect_language_signals(self) -> None:
        """连接框架语言信号：框架语言变化与本插件语言覆盖变化均触发重翻译。"""
        manager = get_language_manager()
        manager.language_changed.connect(self._retranslate_ui)
        manager.plugin_language_changed.connect(
            self._on_plugin_language_changed)

    def _on_plugin_language_changed(self, plugin_id: str, _lang: str) -> None:
        """插件级语言覆盖变化：仅当目标是本插件时重翻译。"""
        if self._plugin_id is not None and plugin_id != self._plugin_id:
            return
        self._retranslate_ui()

    def _retranslate_ui(self, *_args) -> None:
        """语言切换后集中重翻译：分区标题、各子面板、节点类型注册。

        节点类型按新语言重注册（同名异定义纠正机制，新建节点与创建
        菜单立即生效）；画布既有节点标题属实例数据（用户可重命名），
        不回溯改写；状态栏等动态文案在下次事件生成时自然更新。
        """
        for key, label in self._section_labels.items():
            label.setText(self._tr(_GROUP_PANEL, key))
        self._toolbar.retranslate_ui()
        self.graph_list_panel.retranslate_ui()
        self.node_list_panel.retranslate_ui()
        self._property_panel.retranslate_ui()
        self._preview_panel.retranslate_ui()
        ensure_node_types_registered(self._i18n)

    # ------------------------------------------------------------------ 工具条动作（委托 service）
    def _run_pipeline(self) -> None:
        """运行：先推图快照给 service，再触发异步运行（工作线程执行）。"""
        self._push_graph_snapshot()
        result = self._service.run_pipeline()
        if not result.get("success"):
            self._report_failure(self._tr(_GROUP_MAIN, "fail.run"), result)
            return
        self.canvas.execution().reset()
        self._run_order = []
        self._toolbar.set_running(True)
        self._toolbar.set_status(self._tr(_GROUP_TOOLBAR, "status.running"))

    def _stop_pipeline(self) -> None:
        """停止：协作式中断请求，结果由 run_finished 汇总上报。"""
        result = self._service.stop_pipeline()
        if result.get("success"):
            self._toolbar.set_status(self._tr(_GROUP_TOOLBAR,
                                              "status.stopping"))

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
            self._report_failure(self._tr(_GROUP_MAIN, "fail.save"), result)
            return False
        self.graph_list_panel.refresh()
        count = result.get("data", {}).get("node_count", len(self.graph.nodes()))
        self._toolbar.set_status(self._tr(_GROUP_MAIN, "status.saved",
                                          name=name, count=count))
        return True

    def _prompt_graph_name(self) -> Optional[str]:
        """弹存档命名对话框；取消或空名返回 None。"""
        name, ok = QInputDialog.getText(
            self, self._tr(_GROUP_MAIN, "dialog.save_as_title"),
            self._tr(_GROUP_MAIN, "dialog.save_as_label"))
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
            self, self._tr(_GROUP_MAIN, "dialog.overwrite_title"),
            self._tr(_GROUP_MAIN, "dialog.overwrite_text", name=name))
        return answer == QMessageBox.StandardButton.Yes

    def _load_graph_by_name(self, name: str) -> None:
        """加载指定存档：委托 service 恢复，成功后取回图 dict 刷新画布。"""
        result = self._service.load_graph(name)
        if not result.get("success"):
            self._report_failure(self._tr(_GROUP_MAIN, "fail.load"), result)
            return
        data = self._pull_graph_snapshot()
        if data is None:
            self._toolbar.set_status(self._tr(_GROUP_MAIN,
                                              "status.load_no_data"))
            return
        self.restore_graph(data)
        fallback = bool(result.get("data", {}).get("fallback"))
        self._current_graph_name = None if fallback else name
        suffix = (self._tr(_GROUP_MAIN, "status.load_fallback_suffix")
                  if fallback else "")
        self._toolbar.set_status(self._tr(_GROUP_MAIN, "status.loaded",
                                          name=name, suffix=suffix))

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
            self._toolbar.set_status(self._tr(
                _GROUP_MAIN, "status.run_done", count=count,
                ms=f"{total_ms:.0f}"))
            return
        errors = summary.get("errors") or []
        reason = self._first_error_reason(errors) or self._tr(_GROUP_MAIN,
                                                              "error.unknown")
        _logger.error(_MODULE, f"管线运行失败：{reason}")
        self._toolbar.set_status(self._tr(_GROUP_MAIN,
                                          "status.run_interrupted",
                                          reason=reason))

    @staticmethod
    def _first_error_reason(errors: List[Any]) -> Optional[str]:
        """取首个错误的用户可读信息；errors 元素为 {"node_id","message"} 字典"""
        if not errors:
            return None
        first = errors[0]
        if isinstance(first, dict):
            return str(first.get("message") or first)
        return str(first)

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
        """操作失败：弹窗告知 + ERROR 日志（面向用户的错误两者都要）。"""
        reason = result.get("error", self._tr(_GROUP_MAIN, "error.unknown"))
        _logger.error(_MODULE, f"{title}：{reason}")
        QMessageBox.warning(self, title, str(reason))
        self._toolbar.set_status(f"{title}：{reason}")
