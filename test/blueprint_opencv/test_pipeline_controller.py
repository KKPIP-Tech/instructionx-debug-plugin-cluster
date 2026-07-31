# -*- coding: utf-8 -*-
"""PipelineController 运行会话状态机的单元测试。

覆盖范围：

- 初始状态：idle，last_result_info 缺省契约；
- 正常路径：update_graph → start_run 同步执行 → done，preview 元信息
  被记录；update_graph 入口的污染引脚迁移集成；
- 状态机：运行中拒绝重复启动 / 拒绝 reset、request_stop 协作式停止
  （stopping → done）、done 后 reset 回 idle；
- 校验失败：未设置图快照 / 无 start / 超节点上限，状态回 idle；
- 兜底：执行期非预期异常转为 error 汇总并补发 on_run_finished；
- submit_run：注入调度成功 / 调度自身抛错时状态回 idle 并上抛。
"""

import threading
import time
from unittest import mock

import numpy as np
import pytest

from plugin.blueprint_opencv.function.constants import NodeExecutionError
from plugin.blueprint_opencv.function.executor import ExecutorCallbacks
from plugin.blueprint_opencv.function.node_catalog import NodeDefinition
from plugin.blueprint_opencv.function.pipeline_controller import (
    PipelineController,
)

from .conftest import (
    StatusRecorder,
    exec_edge,
    image_edge,
    make_node,
    make_start,
    solid_preview_graph,
)
from .test_executor import _recorder_callbacks

#: 等待状态迁移的轮询超时（秒）
_WAIT_TIMEOUT = 5.0
#: 轮询间隔（秒）
_POLL_INTERVAL = 0.01


def _wait_status(controller: PipelineController, expected: set) -> None:
    """轮询等待 controller 状态进入 expected 集合；超时失败。"""
    deadline = time.monotonic() + _WAIT_TIMEOUT
    while controller.status not in expected:
        if time.monotonic() > deadline:
            raise AssertionError(
                f"等待状态 {expected} 超时，当前状态: {controller.status}")
        time.sleep(_POLL_INTERVAL)


def _slow_source_def(gate: threading.Event) -> NodeDefinition:
    """构造受门闩阻塞的慢速源节点定义（协作式停止测试用）。"""
    def slow_op(inputs, props):
        gate.wait(_WAIT_TIMEOUT)
        return {"image_out": np.zeros((4, 4, 3), dtype=np.uint8)}

    return NodeDefinition(
        "slow_source", "慢速源", "输入",
        [{"id": "exec_in", "name": "执行", "data_type": "exec"}],
        [{"id": "exec_out", "name": "执行", "data_type": "exec"},
         {"id": "image_out", "name": "图像", "data_type": "image"}],
        [], slow_op, "测试用阻塞节点")


class TestInitialState:
    """初始状态与缺省契约。"""

    def test_initial_status_idle(self):
        """构造后状态为 idle。"""
        assert PipelineController().status == "idle"

    def test_initial_result_info(self):
        """未运行时 last_result_info 返回缺省契约（无错误、无 preview）。"""
        info = PipelineController().last_result_info
        assert info["status"] == "idle"
        assert info["total_ms"] == 0.0
        assert info["node_count"] == 0
        assert info["errors"] == []
        assert info["preview"] is None


class TestNormalRun:
    """正常路径：同步执行与结果记录。"""

    def test_start_run_done(self, node_defs):
        """start_run 返回 True、状态 done，summary 与 preview 元信息落库。"""
        controller = PipelineController(node_defs)
        controller.update_graph(solid_preview_graph(node_defs))
        recorder = StatusRecorder()
        assert controller.start_run(_recorder_callbacks(recorder)) is True
        assert controller.status == "done"
        info = controller.last_result_info
        assert info["status"] == "done"
        assert info["node_count"] == 2
        assert info["errors"] == []
        assert info["preview"] is not None
        assert info["preview"]["width"] == 16

    def test_update_graph_applies_migration(self, node_defs):
        """update_graph 入口迁移污染引脚：污染图也能正常运行到 done。"""
        polluted = solid_preview_graph(node_defs)
        for node in polluted["nodes"]:
            if node["type_name"] == "solid_color":
                node["outputs"] = [{"id": "out", "data_type": "exec"},
                                   {"id": "img", "data_type": "image"}]
        polluted["edges"][-1]["from_pin"] = "img"
        controller = PipelineController(node_defs)
        controller.update_graph(polluted)
        assert controller.start_run(
            _recorder_callbacks(StatusRecorder())) is True
        assert controller.status == "done"

    def test_reset_after_done(self, node_defs):
        """done 状态允许 reset 回 idle（SPEC §6.1）。"""
        controller = PipelineController(node_defs)
        controller.update_graph(solid_preview_graph(node_defs))
        controller.start_run(_recorder_callbacks(StatusRecorder()))
        assert controller.status == "done"
        controller.reset()
        assert controller.status == "idle"

    def test_request_stop_when_idle_is_noop(self):
        """idle 状态 request_stop 无副作用（状态保持 idle）。"""
        controller = PipelineController()
        controller.request_stop()
        assert controller.status == "idle"


class TestValidationFailures:
    """运行前校验失败：抛中文错误且状态回 idle。"""

    def test_run_without_graph(self):
        """未设置图快照：start_run 抛「尚未设置图快照」。"""
        controller = PipelineController()
        with pytest.raises(NodeExecutionError, match="尚未设置图快照"):
            controller.start_run(_recorder_callbacks(StatusRecorder()))
        assert controller.status == "idle"

    def test_run_without_start(self, node_defs):
        """图无 start 节点：校验失败状态回 idle。"""
        controller = PipelineController(node_defs)
        graph = {"nodes": [make_node(node_defs, "prev-1", "preview")],
                 "edges": []}
        controller.update_graph(graph)
        with pytest.raises(NodeExecutionError, match="无 start 节点"):
            controller.start_run(_recorder_callbacks(StatusRecorder()))
        assert controller.status == "idle"

    def test_node_count_limit(self, node_defs):
        """节点数超上限：抛「超过上限」且状态回 idle。"""
        controller = PipelineController(node_defs, max_nodes=2)
        controller.update_graph(solid_preview_graph(node_defs))  # 3 个节点
        with pytest.raises(NodeExecutionError, match="超过上限 2"):
            controller.start_run(_recorder_callbacks(StatusRecorder()))
        assert controller.status == "idle"


class TestConcurrencyAndStop:
    """运行中互斥与协作式停止（真实线程 + 门闩慢节点）。"""

    @pytest.fixture()
    def slow_setup(self, node_defs, stop_gate):
        """慢速源图 + controller（start → slow_source → preview）。"""
        defs = dict(node_defs)
        defs["slow_source"] = _slow_source_def(stop_gate)
        nodes = [make_start(),
                 make_node(defs, "slow-1", "slow_source"),
                 make_node(defs, "prev-1", "preview")]
        edges = [exec_edge("start-1", "slow-1", from_pin="out"),
                 exec_edge("slow-1", "prev-1"),
                 image_edge("slow-1", "prev-1")]
        controller = PipelineController(defs)
        controller.update_graph({"nodes": nodes, "edges": edges})
        return controller

    def test_concurrent_run_rejected(self, slow_setup, stop_gate):
        """运行中再次 start_run 返回 False；reset 被拒绝；停止后 done。"""
        controller = slow_setup
        recorder = StatusRecorder()
        thread = threading.Thread(
            target=controller.start_run,
            args=(_recorder_callbacks(recorder),))
        thread.start()
        try:
            _wait_status(controller, {"running"})
            assert controller.start_run(
                _recorder_callbacks(StatusRecorder())) is False
            controller.reset()  # 运行中拒绝 reset
            assert controller.status == "running"
            controller.request_stop()
            assert controller.status == "stopping"
        finally:
            stop_gate.set()
            thread.join(_WAIT_TIMEOUT)
        assert not thread.is_alive()
        # 协作式停止：当前节点完成后中断，preview 未执行，结果为 done
        assert controller.status == "done"
        assert recorder.statuses_of("prev-1") == []


class TestUnexpectedException:
    """执行期非预期异常兜底：转为 error 汇总并补发 on_run_finished。"""

    def test_executor_crash_converted_to_error(self, node_defs):
        """executor.run 抛非预期异常：状态 error、回调收到 error 汇总。"""
        controller = PipelineController(node_defs)
        controller.update_graph(solid_preview_graph(node_defs))
        recorder = StatusRecorder()
        with mock.patch.object(controller._executor, "run",
                               side_effect=RuntimeError("boom")):
            assert controller.start_run(
                _recorder_callbacks(recorder)) is True
        assert controller.status == "error"
        assert len(recorder.finished) == 1
        summary = recorder.finished[0]
        assert summary["status"] == "error"
        assert "管线执行异常: boom" in summary["errors"][0]["message"]


class TestSubmitRun:
    """submit_run 的调度注入语义。"""

    def test_submit_inline(self, node_defs):
        """submit 内联执行：返回 True 且状态 done。"""
        controller = PipelineController(node_defs)
        controller.update_graph(solid_preview_graph(node_defs))
        result = controller.submit_run(_recorder_callbacks(StatusRecorder()),
                                       submit=lambda work: work())
        assert result is True
        assert controller.status == "done"

    def test_submit_failure_restores_idle(self, node_defs):
        """submit 自身抛错：异常上抛且状态回 idle（不卡 running）。"""
        controller = PipelineController(node_defs)
        controller.update_graph(solid_preview_graph(node_defs))

        def bad_submit(work):
            raise RuntimeError("线程池已关闭")

        with pytest.raises(RuntimeError, match="线程池已关闭"):
            controller.submit_run(_recorder_callbacks(StatusRecorder()),
                                  submit=bad_submit)
        assert controller.status == "idle"
