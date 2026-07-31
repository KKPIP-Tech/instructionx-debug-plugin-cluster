# -*- coding: utf-8 -*-
"""管线控制器：运行会话状态持有者（function 层，无 Qt）。

职责（SPEC §5）：

- 持有当前图快照（``update_graph``，由 service 在运行前从画布取）；
- 管理运行级状态机（idle → running → stopping → done/error，SPEC §6.1）；
- 持有协作式停止标志（``threading.Event``）并转发给执行引擎；
- 记录最近一次运行汇总与 preview 结果元信息（``last_result_info``）。

``start_run`` 为同步阻塞调用：service 层负责把它提交到
BackgroundTaskManager 工作线程；本类自身不做线程调度，只用锁保护
状态字段，可被 UI / MCP 线程安全调用 ``request_stop`` 等轻量方法。
"""

import threading
from typing import Any, Callable, Dict, Optional

from utils.logging_tools import LoggerManager, get_name

from .constants import (DEFAULT_MAX_NODES, RUN_STATUS_DONE, RUN_STATUS_ERROR,
                        RUN_STATUS_IDLE, RUN_STATUS_RUNNING,
                        RUN_STATUS_STOPPING, NodeExecutionError)
from .executor import ExecutorCallbacks, PipelineExecutor
from .node_catalog import NodeDefinition, defs_by_type


class PipelineController:
    """管线运行会话控制器（状态机 + 停止标志 + 最近结果）。

    参数:
        node_defs: 节点定义表（缺省取 node_catalog 全量定义）。
        max_nodes: 单次运行节点数防御性上限（SPEC §8 graph.max_nodes）。
    """

    def __init__(self, node_defs: Optional[Dict[str, NodeDefinition]] = None,
                 max_nodes: int = DEFAULT_MAX_NODES):
        self._executor = PipelineExecutor(node_defs or defs_by_type())
        self._max_nodes = int(max_nodes)
        self._graph: Optional[dict] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._status = RUN_STATUS_IDLE
        self._last_summary: Optional[dict] = None
        self._last_preview: Optional[dict] = None
        self._logger = LoggerManager()

    # ------------------------------------------------------------------
    # 图快照
    # ------------------------------------------------------------------

    def update_graph(self, graph_dict: dict) -> None:
        """更新当前图快照（运行前由 service 从画布 ``to_dict()`` 取）。"""
        with self._lock:
            self._graph = graph_dict

    # ------------------------------------------------------------------
    # 运行控制
    # ------------------------------------------------------------------

    def start_run(self, callbacks: ExecutorCallbacks) -> bool:
        """启动一轮运行（同步阻塞，调用方需在工作线程执行）。

        返回:
            True 表示本轮已执行完毕；False 表示已有运行在进行中。

        异常:
            NodeExecutionError: 图未设置 / 校验失败（无 start、成环、
            超节点上限），此时状态回 idle。
        """
        graph = self._prepare_run()
        if graph is None:
            return False
        self._execute(graph, callbacks)
        return True

    def submit_run(self, callbacks: ExecutorCallbacks,
                   submit: Callable[[Callable[[], None]], None]) -> bool:
        """校验通过后把执行经 ``submit`` 提交到工作线程（SPEC §1.3）。

        ``submit`` 为线程调度注入（service 层封装 BackgroundTaskManager），
        保持本层不依赖框架任务系统。返回 True 表示已提交、False 表示已有
        运行在进行中；校验失败抛 ``NodeExecutionError``（状态回 idle），
        submit 自身抛出的异常同样回 idle 后原样上抛。
        """
        graph = self._prepare_run()
        if graph is None:
            return False
        try:
            submit(lambda: self._execute(graph, callbacks))
        except Exception:
            with self._lock:
                self._status = RUN_STATUS_IDLE  # 提交失败回 idle，避免卡死 running
            raise
        return True

    def _prepare_run(self) -> Optional[dict]:
        """进入 running 状态并完成运行前校验；已有运行时返回 None。"""
        graph = self._begin_run()
        if graph is None:
            return None
        self._pre_validate(graph)
        return graph

    def _execute(self, graph: dict, callbacks: ExecutorCallbacks) -> None:
        """对已完成校验的图执行一轮管线并落状态（同步，工作线程调用）。

        工作线程中的非预期异常必须兜底：转为 error 汇总并经
        on_run_finished 上报，避免 UI 永久停留在「运行中」。
        """
        try:
            summary = self._executor.run(graph, self._stop_event,
                                         self._wrap_callbacks(callbacks))
        except Exception as exc:
            summary = self._unexpected_summary(exc)
            callbacks.on_run_finished(summary)  # 异常路径也要通知运行结束
        with self._lock:
            self._last_summary = summary
            self._status = summary["status"]
        self._logger.info(
            get_name(),
            f"管线运行结束: status={summary['status']}, "
            f"total_ms={summary['total_ms']:.1f}, nodes={summary['node_count']}")

    @staticmethod
    def _unexpected_summary(exc: Exception) -> dict:
        """把执行期非预期异常转为 error 汇总并补发 on_run_finished。"""
        return {
            "status": RUN_STATUS_ERROR,
            "total_ms": 0.0,
            "node_count": 0,
            "errors": [{"node_id": "", "message": f"管线执行异常: {exc}"}],
        }

    def request_stop(self) -> None:
        """请求停止当前运行（协作式：当前节点执行完后中断）。"""
        with self._lock:
            if self._status != RUN_STATUS_RUNNING:
                return
            self._status = RUN_STATUS_STOPPING
            self._stop_event.set()
        self._logger.info(get_name(), "已请求停止管线运行（协作式）")

    def reset(self) -> None:
        """重置运行级状态为 idle（SPEC §6.1：done/error → idle）。"""
        with self._lock:
            if self._status in (RUN_STATUS_RUNNING, RUN_STATUS_STOPPING):
                return  # 运行中不允许重置，避免状态错乱
            self._status = RUN_STATUS_IDLE

    def _begin_run(self) -> Optional[dict]:
        """尝试进入 running 状态并取图快照；不可启动返回 None。"""
        with self._lock:
            if self._status in (RUN_STATUS_RUNNING, RUN_STATUS_STOPPING):
                return None
            if self._graph is None:
                raise NodeExecutionError("尚未设置图快照，无法运行")
            self._status = RUN_STATUS_RUNNING
            self._stop_event.clear()
            self._last_preview = None
            return self._graph

    def _pre_validate(self, graph: dict) -> None:
        """运行前校验：节点数上限 + start 存在 + exec 链无环。"""
        try:
            normalized = PipelineExecutor.normalize_graph(graph)
            node_count = len(normalized.get("nodes", []))
            if node_count > self._max_nodes:
                raise NodeExecutionError(
                    f"节点数量 {node_count} 超过上限 {self._max_nodes}，无法运行")
            self._executor.validate_graph(graph)
        except NodeExecutionError:
            with self._lock:
                self._status = RUN_STATUS_IDLE  # SPEC §6.1：校验失败回 idle
            self._logger.error(get_name(), "管线运行前校验失败")
            raise

    # ------------------------------------------------------------------
    # 结果查询
    # ------------------------------------------------------------------

    @property
    def status(self) -> str:
        """当前运行级状态（idle / running / stopping / done / error）。"""
        with self._lock:
            return self._status

    @property
    def last_result_info(self) -> Dict[str, Any]:
        """最近运行汇总 + preview 元信息（service_api 契约，SPEC §7）。"""
        with self._lock:
            summary = self._last_summary or {}
            return {
                "status": self._status,
                "total_ms": summary.get("total_ms", 0.0),
                "node_count": summary.get("node_count", 0),
                "errors": list(summary.get("errors", [])),
                "preview": self._last_preview,
            }

    # ------------------------------------------------------------------
    # 回调包装（捕获 preview 元信息）
    # ------------------------------------------------------------------

    def _wrap_callbacks(self, callbacks: ExecutorCallbacks) -> ExecutorCallbacks:
        """包装回调：透传原回调，同时记录 preview 元信息供结果查询。"""
        return ExecutorCallbacks(
            on_node_status=callbacks.on_node_status,
            on_preview=self._make_preview_hook(callbacks.on_preview),
            on_run_finished=callbacks.on_run_finished,
        )

    def _make_preview_hook(
            self, original: Callable[[str, bytes, dict], None]
    ) -> Callable[[str, bytes, dict], None]:
        """生成 on_preview 包装：先记录 info（多 preview 时保留最后者），再透传。"""
        def hook(node_id: str, png_bytes: bytes, info: dict) -> None:
            with self._lock:
                self._last_preview = dict(info)
            original(node_id, png_bytes, info)
        return hook
