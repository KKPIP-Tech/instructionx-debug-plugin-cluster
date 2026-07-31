# -*- coding: utf-8 -*-
"""blueprint_opencv 测试套件共享 fixture 与图构建辅助。

提供：

- 确定性小尺寸测试图（``color_image`` / ``gray_image``，32×32）；
- 节点定义表（``node_defs``）与 executor/controller 测试用的图 dict
  构建辅助（``make_node`` / ``make_start`` / ``exec_edge`` /
  ``image_edge`` / ``solid_preview_graph``）；
- DataProvider 单例隔离（``provider``，指向 tmp_path）与隔离的
  ``BlueprintOpenCVService`` 实例（``service``，配合共享 conftest 的
  ``plugin_id`` fixture，不污染真实运行数据目录）。
"""

import threading
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pytest

from core.data.data_provider import DataProvider

from plugin.blueprint_opencv.function.constants import (
    PIN_DATA_TYPE_EXEC,
    PIN_DATA_TYPE_IMAGE,
    PIN_EXEC_IN,
    PIN_EXEC_OUT,
    PIN_IMAGE_IN,
    PIN_IMAGE_OUT,
    START_EXEC_OUT_PIN,
    START_TYPE_NAME,
)
from plugin.blueprint_opencv.function.node_catalog import NodeDefinition, defs_by_type
from plugin.blueprint_opencv.service import BlueprintOpenCVService

#: 测试图边长（小尺寸，保证 op 执行快速）
_TEST_IMAGE_SIZE = 32
#: 测试随机种子（确定性图像内容，断言可复现）
_TEST_SEED = 42


# ---------------------------------------------------------------------------
# 测试图 fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def color_image() -> np.ndarray:
    """确定性 32×32 BGR 三通道测试图（uint8，内容随机但可复现）。"""
    rng = np.random.default_rng(_TEST_SEED)
    return rng.integers(0, 256, (_TEST_IMAGE_SIZE, _TEST_IMAGE_SIZE, 3),
                        dtype=np.uint8)


@pytest.fixture()
def gray_image() -> np.ndarray:
    """确定性 32×32 单通道灰度测试图（uint8）。"""
    rng = np.random.default_rng(_TEST_SEED)
    return rng.integers(0, 256, (_TEST_IMAGE_SIZE, _TEST_IMAGE_SIZE),
                        dtype=np.uint8)


@pytest.fixture()
def node_defs() -> Dict[str, NodeDefinition]:
    """节点定义表（type_name -> NodeDefinition，每次调用新建映射）。"""
    return defs_by_type()


# ---------------------------------------------------------------------------
# 图 dict 构建辅助（executor / pipeline_controller 测试共用）
# ---------------------------------------------------------------------------

def make_node(defs: Dict[str, NodeDefinition], node_id: str,
              type_name: str,
              properties: Optional[Dict[str, Any]] = None) -> dict:
    """按目录定义构建图节点 dict（引脚结构拷贝自标准定义）。

    参数:
        defs: 节点定义表。
        node_id: 节点实例 id。
        type_name: 节点类型名（必须在 defs 中）。
        properties: 节点属性（可选）。

    返回:
        ``canvas.to_dict()`` 内层节点形态的 dict。
    """
    definition = defs[type_name]
    return {
        "id": node_id,
        "type_name": type_name,
        "title": definition.title,
        "properties": dict(properties or {}),
        "inputs": [dict(pin) for pin in definition.inputs],
        "outputs": [dict(pin) for pin in definition.outputs],
    }


def make_start(node_id: str = "start-1") -> dict:
    """构建内置 start 节点 dict（exec 输出引脚 id 为 ``out``）。"""
    return {
        "id": node_id,
        "type_name": START_TYPE_NAME,
        "title": "开始",
        "properties": {},
        "inputs": [],
        "outputs": [{"id": START_EXEC_OUT_PIN, "name": "执行",
                     "data_type": PIN_DATA_TYPE_EXEC}],
    }


def exec_edge(from_id: str, to_id: str, from_pin: str = PIN_EXEC_OUT) -> dict:
    """构建 exec 边（start 的 from_pin 需传 ``out``）。"""
    return {"from_node": from_id, "from_pin": from_pin,
            "to_node": to_id, "to_pin": PIN_EXEC_IN}


def image_edge(from_id: str, to_id: str, from_pin: str = PIN_IMAGE_OUT,
               to_pin: str = PIN_IMAGE_IN) -> dict:
    """构建图像数据边。"""
    return {"from_node": from_id, "from_pin": from_pin,
            "to_node": to_id, "to_pin": to_pin}


def solid_preview_graph(defs: Dict[str, NodeDefinition],
                        color: str = "#3B82F6") -> dict:
    """构建最小可运行图：start → solid_color → preview（exec + image 双线）。

    参数:
        defs: 节点定义表。
        color: solid_color 节点的颜色参数（传非法值可构造失败场景）。

    返回:
        内层 ``{"nodes","edges"}`` 图 dict。
    """
    solid_props = {"width": 16, "height": 16, "color": color}
    nodes = [make_start(),
             make_node(defs, "solid-1", "solid_color", solid_props),
             make_node(defs, "prev-1", "preview")]
    edges = [exec_edge("start-1", "solid-1", from_pin=START_EXEC_OUT_PIN),
             exec_edge("solid-1", "prev-1"),
             image_edge("solid-1", "prev-1")]
    return {"nodes": nodes, "edges": edges}


class StatusRecorder:
    """执行回调记录器：收集节点状态 / preview / 运行结束回调。"""

    def __init__(self) -> None:
        #: ``(node_id, status)`` 事件序列
        self.statuses: List[tuple] = []
        #: ``(node_id, png_bytes, info)`` 列表
        self.previews: List[tuple] = []
        #: on_run_finished 收到的 summary 列表
        self.finished: List[dict] = []

    def on_node_status(self, node_id: str, status: str,
                       elapsed_ms: float, message: str) -> None:
        """记录节点状态事件。"""
        self.statuses.append((node_id, status))

    def on_preview(self, node_id: str, png_bytes: bytes, info: dict) -> None:
        """记录 preview 回调。"""
        self.previews.append((node_id, png_bytes, info))

    def on_run_finished(self, summary: dict) -> None:
        """记录运行结束回调。"""
        self.finished.append(summary)

    def statuses_of(self, node_id: str) -> List[str]:
        """取某节点的状态序列。"""
        return [status for nid, status in self.statuses if nid == node_id]


class InlineTaskManager:
    """内联执行的假任务管理器（register_async_task 同步执行 work）。"""

    def register_async_task(self, plugin_id: str, name: str,
                            work: Callable[[], None]) -> str:
        """同步执行 work 并返回假任务 id。"""
        work()
        return "inline-task"


class PendingTaskManager:
    """挂起执行的假任务管理器（work 入队不执行，测试手动 drain）。"""

    def __init__(self) -> None:
        self.pending: List[Callable[[], None]] = []

    def register_async_task(self, plugin_id: str, name: str,
                            work: Callable[[], None]) -> str:
        """把 work 挂起入队并返回假任务 id。"""
        self.pending.append(work)
        return f"pending-task-{len(self.pending)}"

    def drain(self) -> None:
        """依次执行全部挂起的 work。"""
        while self.pending:
            self.pending.pop(0)()


# ---------------------------------------------------------------------------
# DataProvider / service 隔离 fixture
# ---------------------------------------------------------------------------

@pytest.fixture()
def provider(tmp_path) -> DataProvider:
    """指向 tmp_path 的隔离 DataProvider（重置单例，测试后还原）。"""
    DataProvider._instance = None
    instance = DataProvider(data_dir=str(tmp_path), data_filename="test.json")
    yield instance
    DataProvider._instance = None


@pytest.fixture()
def service(plugin_id: str, provider: DataProvider) -> BlueprintOpenCVService:
    """隔离的 service 实例（隔离 plugin_id + tmp_path 数据目录）。"""
    return BlueprintOpenCVService(plugin_id=plugin_id, data_provider=provider)


@pytest.fixture()
def stop_gate() -> threading.Event:
    """协作式停止测试用的门闩事件（未 set 时慢节点阻塞）。"""
    return threading.Event()
