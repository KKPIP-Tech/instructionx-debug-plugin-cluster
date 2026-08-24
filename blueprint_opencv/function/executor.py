# -*- coding: utf-8 -*-
"""管线执行引擎：exec 链拓扑排序 + 数据流求值 + 状态回调（无 Qt）。

契约见 SPEC §4：

- 输入是图 dict（``canvas.to_dict()`` 结果或内层 ``{"nodes","edges"}``）、
  停止标志（``threading.Event``）与回调集合；输出经回调上报；
- 从内置 ``start`` 节点沿 exec 边拓扑排序得到执行序列；
- 执行节点时沿 ``image_in`` 边按需递归求值上游，结果按节点缓存
  （一轮运行内每个节点只求值一次）；
- preview 节点求值完成后编码 PNG 字节并触发 ``on_preview``；
- 单节点失败标 error 并中断当前 exec 分支（本版单链即整体中断）。

本模块仅在工作线程活动，不知道 Qt、不知道 DataProvider。
"""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from utils.logging_tools import LoggerManager, get_name

from .constants import (INFO_ELAPSED_MS, NODE_STATUS_DONE, NODE_STATUS_ERROR,
                        NODE_STATUS_RUNNING, PIN_DATA_TYPE_EXEC,
                        PIN_DATA_TYPE_IMAGE, PIN_EXEC_IN, PIN_IMAGE_OUT,
                        PREVIEW_TYPE_NAME, RUN_STATUS_DONE, RUN_STATUS_ERROR,
                        START_TYPE_NAME, NodeExecutionError)
from .image_codec import encode_png, image_info
from .node_catalog import NodeDefinition
from .param_schema import resolve_props

#: 毫秒换算系数（perf_counter 秒 → 毫秒）
_MS_PER_SECOND = 1000.0

#: 三色标记 DFS 的节点标记（判环用）：灰 = 当前 DFS 路径上（重复到达即成环），
#: 黑 = 已完成（菱形汇聚时从多条路径重复到达属正常，直接跳过）
_MARK_GRAY = "gray"
_MARK_BLACK = "black"


def _noop(*args: Any, **kwargs: Any) -> None:
    """空回调（ExecutorCallbacks 缺省值）。"""


@dataclass
class ExecutorCallbacks:
    """执行引擎回调集合（SPEC §4.3 契约，全部可缺省为空操作）。

    参数:
        on_node_status: ``(node_id, status, elapsed_ms, message)``，
            status ∈ running / done / error。
        on_preview: ``(node_id, png_bytes, info)``，info 含
            ``{"width","height","channels","elapsed_ms"}``。
        on_run_finished: ``(summary)``，summary 含
            ``{"status","total_ms","node_count","errors"}``。
    """

    on_node_status: Callable[[str, str, float, str], None] = _noop
    on_preview: Callable[[str, bytes, dict], None] = _noop
    on_run_finished: Callable[[dict], None] = _noop


@dataclass
class _RunContext:
    """单轮运行的内部上下文（图索引、求值缓存、回调、停止标志）。"""

    nodes: Dict[str, dict]
    edges: List[dict]
    #: node_id -> {输出引脚 id: data_type}（判定 exec 边用）
    output_types: Dict[str, Dict[str, str]]
    #: node_id -> 图像输入引脚 dict 列表
    image_inputs: Dict[str, List[dict]]
    #: node_id -> {输出引脚 id: np.ndarray}（本轮求值缓存）
    cache: Dict[str, Dict[str, np.ndarray]] = field(default_factory=dict)
    callbacks: ExecutorCallbacks = field(default_factory=ExecutorCallbacks)
    stop_event: threading.Event = field(default_factory=threading.Event)


class PipelineExecutor:
    """管线执行引擎：对一张图快照执行一轮求值。

    用法::

        executor = PipelineExecutor(defs_by_type())
        executor.validate_graph(graph)            # 预校验（可选）
        summary = executor.run(graph, stop_event, callbacks)

    ``run`` 为同步阻塞调用，应由调用方提交到工作线程执行。
    """

    def __init__(self, node_defs: Dict[str, NodeDefinition]):
        self._defs = node_defs
        self._logger = LoggerManager()

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------

    @staticmethod
    def normalize_graph(graph: dict) -> dict:
        """把 ``canvas.to_dict()`` 结果归一为内层 ``{"nodes","edges"}``。"""
        if "nodes" in graph:
            return graph
        return dict(graph.get("graph", {}))

    def validate_graph(self, graph: dict) -> None:
        """预校验：存在唯一 start、exec 链无环；失败抛中文错误。"""
        ctx = self._build_context(self.normalize_graph(graph),
                                  ExecutorCallbacks(), threading.Event())
        self._exec_order(ctx)

    def run(self, graph: dict, stop_event: threading.Event,
            callbacks: ExecutorCallbacks) -> dict:
        """执行一轮管线（同步），返回运行汇总 summary。

        节点级错误经 ``on_node_status`` 上报并记入 summary["errors"]，
        不向上抛出；图校验错误（无 start / 成环）抛 NodeExecutionError。
        """
        ctx = self._build_context(self.normalize_graph(graph),
                                  callbacks, stop_event)
        order = self._exec_order(ctx)
        summary = self._run_sequence(ctx, order)
        callbacks.on_run_finished(summary)
        return summary

    # ------------------------------------------------------------------
    # 运行主循环
    # ------------------------------------------------------------------

    def _run_sequence(self, ctx: _RunContext, order: List[str]) -> dict:
        """按 exec 序列逐节点执行，汇总结果（SPEC §4.2 错误隔离）。"""
        started = time.perf_counter()
        errors: List[dict] = []
        for node_id in order:
            if ctx.stop_event.is_set():
                break  # 协作式停止：当前节点完成后中断（SPEC §4.1）
            error = self._execute_one(ctx, node_id)
            if error is not None:
                errors.append(error)
                break  # 单链语义：分支中断即整体中断
        return self._build_summary(order, errors, started)

    def _execute_one(self, ctx: _RunContext, node_id: str) -> Optional[dict]:
        """执行单个节点并上报状态；返回错误 dict 或 None。"""
        ctx.callbacks.on_node_status(node_id, NODE_STATUS_RUNNING, 0.0, "")
        started = time.perf_counter()
        try:
            self._evaluate(ctx, node_id)
        except NodeExecutionError as exc:
            return self._fail_node(ctx, node_id, started, str(exc))
        except Exception as exc:  # 兜底：非预期异常统一转为节点错误
            self._logger.error(get_name(),
                               f"节点执行出现非预期异常: node={node_id}, {exc!r}")
            return self._fail_node(ctx, node_id, started, f"节点执行异常: {exc}")
        elapsed = self._elapsed_ms(started)
        ctx.callbacks.on_node_status(node_id, NODE_STATUS_DONE, elapsed, "")
        return None

    def _fail_node(self, ctx: _RunContext, node_id: str, started: float,
                   message: str) -> dict:
        """把节点标记为 error：回调上报 + ERROR 日志 + 返回错误记录。"""
        elapsed = self._elapsed_ms(started)
        ctx.callbacks.on_node_status(node_id, NODE_STATUS_ERROR, elapsed, message)
        self._logger.error(get_name(),
                           f"节点执行失败: node={node_id}, 原因={message}")
        return {"node_id": node_id, "message": message}

    @staticmethod
    def _build_summary(order: List[str], errors: List[dict],
                       started: float) -> dict:
        """组装运行汇总（SPEC §4.3 summary 契约）。"""
        status = RUN_STATUS_ERROR if errors else RUN_STATUS_DONE
        return {
            "status": status,
            "total_ms": (time.perf_counter() - started) * _MS_PER_SECOND,
            "node_count": len(order),
            "errors": errors,
        }

    # ------------------------------------------------------------------
    # exec 链拓扑排序
    # ------------------------------------------------------------------

    def _exec_order(self, ctx: _RunContext) -> List[str]:
        """从 start 沿 exec 边 DFS 得到执行序列（不含 start 本身）。

        判环采用三色标记法：「重复到达黑节点」是菱形汇聚（如 A→C、B→C
        的 C 从两条路径到达）属正常拓扑，只有重复到达当前路径上的
        灰节点才是真正的环——原 visited 出栈检查会把前者误报为环。
        """
        start_id = self._find_start(ctx)
        order: List[str] = []
        marks: Dict[str, str] = {}
        for successor in self._exec_successors(ctx, start_id):
            self._visit_exec(ctx, successor, marks, order)
        return order

    def _visit_exec(self, ctx: _RunContext, node_id: str,
                    marks: Dict[str, str], order: List[str]) -> None:
        """三色标记 DFS：灰节点重复到达抛环，黑节点跳过，白节点前序入列。"""
        mark = marks.get(node_id)
        if mark == _MARK_GRAY:
            raise NodeExecutionError("exec 链存在环路，无法运行")
        if mark == _MARK_BLACK:
            return  # 菱形汇聚：已完成节点从另一路径到达，非环
        marks[node_id] = _MARK_GRAY
        order.append(node_id)
        for successor in self._exec_successors(ctx, node_id):
            self._visit_exec(ctx, successor, marks, order)
        marks[node_id] = _MARK_BLACK

    def _find_start(self, ctx: _RunContext) -> str:
        """定位唯一 start 节点；缺失 / 多个均拒绝运行。"""
        starts = [nid for nid, node in ctx.nodes.items()
                  if node.get("type_name") == START_TYPE_NAME]
        if not starts:
            raise NodeExecutionError("无 start 节点，无法运行")
        if len(starts) > 1:
            raise NodeExecutionError("存在多个 start 节点，无法运行")
        return starts[0]

    def _exec_successors(self, ctx: _RunContext, node_id: str) -> List[str]:
        """取某节点的全部 exec 后继（exec_out 可分出多条边）。"""
        return [edge["to_node"] for edge in ctx.edges
                if edge.get("from_node") == node_id
                and self._is_exec_edge(ctx, edge)]

    @staticmethod
    def _is_exec_edge(ctx: _RunContext, edge: dict) -> bool:
        """判定边是否为 exec 边（按输出引脚 data_type，to_pin 兜底）。"""
        pin_types = ctx.output_types.get(edge.get("from_node"), {})
        if pin_types.get(edge.get("from_pin")) == PIN_DATA_TYPE_EXEC:
            return True
        return edge.get("to_pin") == PIN_EXEC_IN

    # ------------------------------------------------------------------
    # 数据流求值
    # ------------------------------------------------------------------

    def _evaluate(self, ctx: _RunContext,
                  node_id: str) -> Dict[str, np.ndarray]:
        """求值单个节点（带缓存）：解析输入 → 校验参数 → 调 op。"""
        if node_id in ctx.cache:
            return ctx.cache[node_id]
        node = ctx.nodes.get(node_id)
        if node is None:
            raise NodeExecutionError(f"图中缺少节点: {node_id}")
        definition = self._defs.get(node.get("type_name"))
        if definition is None:
            raise NodeExecutionError(f"未知节点类型: {node.get('type_name')}")
        started = time.perf_counter()
        inputs = self._collect_inputs(ctx, node)
        props = resolve_props(definition.param_schema,
                              node.get("properties", {}))
        outputs = definition.op(inputs, props) or {}
        ctx.cache[node_id] = outputs
        self._maybe_emit_preview(ctx, node, outputs, started)
        return outputs

    def _collect_inputs(self, ctx: _RunContext,
                        node: dict) -> Dict[str, np.ndarray]:
        """沿 image_in 边收集输入图像（单连接语义，未连接报错）。"""
        inputs: Dict[str, np.ndarray] = {}
        for pin in ctx.image_inputs.get(node.get("id"), []):
            edge = self._find_image_edge(ctx, node.get("id"), pin["id"])
            if edge is None:
                title = node.get("title", node.get("id"))
                pin_name = pin.get("name", pin["id"])
                raise NodeExecutionError(f"节点「{title}」的输入「{pin_name}」未连接")
            inputs[pin["id"]] = self._upstream_value(ctx, edge)
        return inputs

    @staticmethod
    def _find_image_edge(ctx: _RunContext, node_id: str,
                         pin_id: str) -> Optional[dict]:
        """找某图像输入引脚的入边（单连接，取第一条）。"""
        for edge in ctx.edges:
            if edge.get("to_node") == node_id and edge.get("to_pin") == pin_id:
                return edge
        return None

    def _upstream_value(self, ctx: _RunContext, edge: dict) -> np.ndarray:
        """递归求值上游节点并取对应输出引脚的值。"""
        outputs = self._evaluate(ctx, edge["from_node"])
        value = outputs.get(edge.get("from_pin"))
        if value is None:
            raise NodeExecutionError(
                f"上游节点缺少输出引脚「{edge.get('from_pin')}」的图像数据")
        return value

    def _maybe_emit_preview(self, ctx: _RunContext, node: dict,
                            outputs: Dict[str, np.ndarray],
                            started: float) -> None:
        """preview 节点求值完成后编码 PNG 字节并触发 on_preview。"""
        if node.get("type_name") != PREVIEW_TYPE_NAME:
            return
        img = outputs.get(PIN_IMAGE_OUT)
        if img is None:
            return
        info = image_info(img)
        info[INFO_ELAPSED_MS] = self._elapsed_ms(started)
        ctx.callbacks.on_preview(node.get("id"), encode_png(img), info)

    # ------------------------------------------------------------------
    # 上下文构建与工具
    # ------------------------------------------------------------------

    def _build_context(self, graph: dict, callbacks: ExecutorCallbacks,
                       stop_event: threading.Event) -> _RunContext:
        """把图 dict 索引化为运行上下文。"""
        nodes = {node["id"]: node for node in graph.get("nodes", [])}
        return _RunContext(
            nodes=nodes,
            edges=list(graph.get("edges", [])),
            output_types={nid: self._output_types(n) for nid, n in nodes.items()},
            image_inputs={nid: self._image_input_pins(n)
                          for nid, n in nodes.items()},
            callbacks=callbacks,
            stop_event=stop_event,
        )

    @staticmethod
    def _output_types(node: dict) -> Dict[str, str]:
        """取节点输出引脚 id → data_type 映射。"""
        return {pin["id"]: pin.get("data_type", "any")
                for pin in node.get("outputs", [])}

    @staticmethod
    def _image_input_pins(node: dict) -> List[dict]:
        """取节点的图像输入引脚列表（data_type == image）。"""
        return [pin for pin in node.get("inputs", [])
                if pin.get("data_type") == PIN_DATA_TYPE_IMAGE]

    @staticmethod
    def _elapsed_ms(started: float) -> float:
        """计算从 started 起的耗时（毫秒）。"""
        return (time.perf_counter() - started) * _MS_PER_SECOND
