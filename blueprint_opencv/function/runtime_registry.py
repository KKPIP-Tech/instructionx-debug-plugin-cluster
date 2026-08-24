# -*- coding: utf-8 -*-
"""管线共享运行实例注册表（function 层，无 Qt）。

为什么需要本模块：框架的跨插件 API 自动注册机制会**自行实例化**第二个
``BlueprintOpenCVService``（``core/plugin/manager.py`` 的
``_auto_register_plugin_api`` → ``_instantiate_service``），与插件
entrance 为 UI 创建的实例并存。若每个实例各自持有 PipelineController
与图快照，跨插件 / MCP 调用将操作一份与 UI 完全脱节的运行态——
``run_pipeline`` 永远跑空图、``save_graph`` 会以空图覆盖用户存档
（数据损坏）。

本模块以 ``plugin_id`` 为键提供进程内唯一的 :class:`PipelineRuntime`
（PipelineController + 当前图快照），同一插件的全部 Service 实例共享
同一运行实例；插件卸载时由 entrance 调用 :func:`drop_pipeline_runtime`
显式清理，热重载后可干净重建。
"""

import threading
from typing import Any, Dict

from .pipeline_controller import PipelineController

# 空图结构（与 BlueprintCanvas.to_dict 格式一致）：尚无快照时的初始值，
# 也是预置示例图缺失时的最终回退
EMPTY_GRAPH: Dict[str, Any] = {
    "graph": {"nodes": [], "edges": []},
    "view": {"zoom": 1.0, "offset": [0.0, 0.0]},
}


class PipelineRuntime:
    """单插件进程内唯一的管线运行态（PipelineController + 当前图快照）。

    图快照为 ``canvas.to_dict`` 格式字典：UI 在图变更后（含 load_graph
    恢复）经 ``update_graph`` 同步，保存 / 运行以此为数据源；快照读写
    由锁保护，可被 UI / MCP 线程安全调用。
    """

    def __init__(self) -> None:
        self.controller = PipelineController()
        self._snapshot: Dict[str, Any] = dict(EMPTY_GRAPH)
        self._snapshot_lock = threading.Lock()

    def update_graph(self, graph_dict: Dict[str, Any]) -> None:
        """同步最新图快照并更新控制器（运行 / 保存以此为数据源）。"""
        with self._snapshot_lock:
            self._snapshot = graph_dict
        self.controller.update_graph(graph_dict)

    @property
    def current_graph(self) -> Dict[str, Any]:
        """当前图快照（UI 在 load_graph 后读取并 canvas.from_dict 恢复画布）。"""
        with self._snapshot_lock:
            return self._snapshot


_RUNTIMES: Dict[str, PipelineRuntime] = {}
_RUNTIMES_LOCK = threading.Lock()


def get_pipeline_runtime(plugin_id: str) -> PipelineRuntime:
    """取指定插件的共享运行实例（不存在则惰性创建）。

    参数:
        plugin_id: 插件 UUID（DataProvider / 注册表使用的同一标识）。
    """
    with _RUNTIMES_LOCK:
        runtime = _RUNTIMES.get(plugin_id)
        if runtime is None:
            runtime = PipelineRuntime()
            _RUNTIMES[plugin_id] = runtime
        return runtime


def drop_pipeline_runtime(plugin_id: str) -> None:
    """卸载插件时清理共享运行实例（先协作式请求停止运行中的管线）。"""
    with _RUNTIMES_LOCK:
        runtime = _RUNTIMES.pop(plugin_id, None)
    if runtime is not None:
        runtime.controller.request_stop()


__all__ = [
    "EMPTY_GRAPH",
    "PipelineRuntime",
    "get_pipeline_runtime",
    "drop_pipeline_runtime",
]
