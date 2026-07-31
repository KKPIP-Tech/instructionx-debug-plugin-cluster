# -*- coding: utf-8 -*-
"""PipelineExecutor 执行引擎的单元测试。

覆盖范围：

- exec 拓扑排序：start → solid → preview 链的执行顺序与状态回调序列；
- 按需求值缓存：exec 链外的上游节点被多个下游引用时只求值一次；
- preview 回调：PNG 字节可解码、info 契约键齐全；
- 错误中断：节点失败标记 error 并中断后续 exec 链，不向上抛；
- 图校验拒绝：无 start / 多 start / exec 成环 / 未知节点类型 /
  输入未连接；
- 协作式停止：stop_event 预置时零节点执行；
- normalize_graph：外壳 ``{"graph": ...}`` 形态归一。
"""

import threading

import cv2
import numpy as np
import pytest

from plugin.blueprint_opencv.function.constants import (
    NodeExecutionError,
    PIN_DATA_TYPE_EXEC,
    PIN_DATA_TYPE_IMAGE,
    PIN_EXEC_IN,
    PIN_EXEC_OUT,
    PIN_IMAGE_OUT,
    START_EXEC_OUT_PIN,
)
from plugin.blueprint_opencv.function.executor import (
    ExecutorCallbacks,
    PipelineExecutor,
)
from plugin.blueprint_opencv.function.node_catalog import NodeDefinition

from .conftest import (
    StatusRecorder,
    exec_edge,
    image_edge,
    make_node,
    make_start,
    solid_preview_graph,
)


def _recorder_callbacks(recorder: StatusRecorder) -> ExecutorCallbacks:
    """把记录器包装为执行回调集合。"""
    return ExecutorCallbacks(
        on_node_status=recorder.on_node_status,
        on_preview=recorder.on_preview,
        on_run_finished=recorder.on_run_finished,
    )


@pytest.fixture()
def executor(node_defs):
    """基于真实节点目录的执行引擎。"""
    return PipelineExecutor(node_defs)


class TestNormalRun:
    """正常路径：线性链执行、回调序列与 summary 契约。"""

    def test_linear_chain_summary(self, executor):
        """summary 契约：status done、node_count 不含 start、errors 为空。"""
        recorder = StatusRecorder()
        summary = executor.run(solid_preview_graph(executor._defs),
                               threading.Event(), _recorder_callbacks(recorder))
        assert summary["status"] == "done"
        assert summary["node_count"] == 2
        assert summary["errors"] == []
        assert summary["total_ms"] >= 0.0
        assert recorder.finished == [summary]

    def test_status_callback_sequence(self, executor):
        """节点状态序列：solid 与 preview 均 running → done。"""
        recorder = StatusRecorder()
        executor.run(solid_preview_graph(executor._defs), threading.Event(),
                     _recorder_callbacks(recorder))
        assert recorder.statuses_of("solid-1") == ["running", "done"]
        assert recorder.statuses_of("prev-1") == ["running", "done"]

    def test_preview_callback(self, executor):
        """preview 回调：PNG 可解码为 16×16×3 图，info 契约键齐全。"""
        recorder = StatusRecorder()
        executor.run(solid_preview_graph(executor._defs), threading.Event(),
                     _recorder_callbacks(recorder))
        assert len(recorder.previews) == 1
        node_id, png_bytes, info = recorder.previews[0]
        assert node_id == "prev-1"
        decoded = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8),
                               cv2.IMREAD_UNCHANGED)
        assert decoded.shape == (16, 16, 3)
        assert info["width"] == 16 and info["height"] == 16
        assert info["channels"] == 3
        assert info["elapsed_ms"] >= 0.0

    def test_shell_graph_normalized(self, executor):
        """normalize_graph：外壳 ``{"graph": ...}`` 形态可直接运行。"""
        inner = solid_preview_graph(executor._defs)
        shell = {"graph": inner, "view": {"zoom": 1.0, "offset": [0, 0]}}
        recorder = StatusRecorder()
        summary = executor.run(shell, threading.Event(),
                               _recorder_callbacks(recorder))
        assert summary["status"] == "done"
        # 外壳形态归一为内层 dict（normalize_graph 返回浅拷贝，比较内容）
        assert PipelineExecutor.normalize_graph(shell) == inner

    def test_validate_graph_accepts_valid(self, executor):
        """validate_graph 对合法图静默通过（返回 None）。"""
        assert executor.validate_graph(
            solid_preview_graph(executor._defs)) is None


class TestOnDemandCache:
    """按需求值缓存：一轮运行内每个节点只求值一次。"""

    def test_shared_upstream_evaluated_once(self, node_defs):
        """exec 链外上游被两个 preview 引用，op 只调用一次（缓存命中）。"""
        calls = {"count": 0}
        base = node_defs["solid_color"]

        def counting_op(inputs, props):
            calls["count"] += 1
            return base.op(inputs, props)

        defs = dict(node_defs)
        defs["solid_color"] = NodeDefinition(
            base.type_name, base.title, base.category, base.inputs,
            base.outputs, base.param_schema, counting_op, base.description)
        engine = PipelineExecutor(defs)
        nodes = [make_start(),
                 make_node(defs, "solid-1", "solid_color",
                           {"width": 8, "height": 8}),
                 make_node(defs, "prev-1", "preview"),
                 make_node(defs, "prev-2", "preview")]
        edges = [exec_edge("start-1", "prev-1", from_pin=START_EXEC_OUT_PIN),
                 exec_edge("prev-1", "prev-2"),
                 image_edge("solid-1", "prev-1"),
                 image_edge("solid-1", "prev-2")]
        recorder = StatusRecorder()
        summary = engine.run({"nodes": nodes, "edges": edges},
                             threading.Event(), _recorder_callbacks(recorder))
        assert summary["status"] == "done"
        assert calls["count"] == 1
        assert len(recorder.previews) == 2


class TestErrorPaths:
    """节点错误中断与图校验拒绝。"""

    def test_node_error_interrupts_chain(self, executor):
        """solid 参数非法 → 标 error 并中断，preview 不执行，summary error。"""
        recorder = StatusRecorder()
        graph = solid_preview_graph(executor._defs, color="bad-color")
        summary = executor.run(graph, threading.Event(),
                               _recorder_callbacks(recorder))
        assert summary["status"] == "error"
        assert summary["errors"][0]["node_id"] == "solid-1"
        assert "颜色格式非法" in summary["errors"][0]["message"]
        assert recorder.statuses_of("solid-1") == ["running", "error"]
        assert recorder.statuses_of("prev-1") == []
        assert len(recorder.finished) == 1

    def test_unconnected_input_error(self, executor):
        """灰度节点 image_in 未连接 → 报「未连接」中文错误。"""
        defs = executor._defs
        nodes = [make_start(), make_node(defs, "gray-1", "grayscale")]
        edges = [exec_edge("start-1", "gray-1", from_pin=START_EXEC_OUT_PIN)]
        recorder = StatusRecorder()
        summary = executor.run({"nodes": nodes, "edges": edges},
                               threading.Event(), _recorder_callbacks(recorder))
        assert summary["status"] == "error"
        assert "未连接" in summary["errors"][0]["message"]

    def test_unknown_node_type(self, executor):
        """图中类型名不在目录 → 节点标 error，报「未知节点类型」。"""
        node = {"id": "x-1", "type_name": "no_such_type", "title": "X",
                "properties": {},
                "inputs": [{"id": PIN_EXEC_IN, "name": "执行",
                            "data_type": PIN_DATA_TYPE_EXEC}],
                "outputs": [{"id": PIN_EXEC_OUT, "name": "执行",
                             "data_type": PIN_DATA_TYPE_EXEC}]}
        edges = [exec_edge("start-1", "x-1", from_pin=START_EXEC_OUT_PIN)]
        summary = executor.run({"nodes": [make_start(), node], "edges": edges},
                               threading.Event(),
                               _recorder_callbacks(StatusRecorder()))
        assert summary["status"] == "error"
        assert "未知节点类型" in summary["errors"][0]["message"]

    def test_no_start_rejected(self, executor):
        """无 start 节点：run 抛「无 start 节点」。"""
        graph = {"nodes": [make_node(executor._defs, "prev-1", "preview")],
                 "edges": []}
        with pytest.raises(NodeExecutionError, match="无 start 节点"):
            executor.run(graph, threading.Event(),
                         _recorder_callbacks(StatusRecorder()))

    def test_multiple_starts_rejected(self, executor):
        """多个 start 节点：validate_graph 抛「多个 start」。"""
        graph = {"nodes": [make_start("s1"), make_start("s2")], "edges": []}
        with pytest.raises(NodeExecutionError, match="多个 start 节点"):
            executor.validate_graph(graph)

    def test_exec_cycle_rejected(self, executor):
        """exec 链成环（a→b→a）：validate_graph 抛「环路」。"""
        defs = executor._defs
        nodes = [make_start(),
                 make_node(defs, "a", "grayscale"),
                 make_node(defs, "b", "invert")]
        edges = [exec_edge("start-1", "a", from_pin=START_EXEC_OUT_PIN),
                 exec_edge("a", "b"),
                 exec_edge("b", "a")]
        with pytest.raises(NodeExecutionError, match="环路"):
            executor.validate_graph({"nodes": nodes, "edges": edges})


class TestStopEvent:
    """协作式停止：stop_event 预置时循环立即中断。"""

    def test_pre_set_stop_event_skips_all(self, executor):
        """stop_event 已 set：零节点执行，summary 仍 done、无错误。"""
        stop = threading.Event()
        stop.set()
        recorder = StatusRecorder()
        summary = executor.run(solid_preview_graph(executor._defs), stop,
                               _recorder_callbacks(recorder))
        assert recorder.statuses == []
        assert summary["status"] == "done"
        assert summary["errors"] == []


class TestPreviewWithoutImage:
    """preview 节点无图像输出时不触发 on_preview 的防御路径。"""

    def test_preview_missing_output_skips_callback(self, node_defs):
        """上游 op 返回空 dict：preview 透传失败报「输入未连接」类错误，
        不会触发 on_preview。"""
        defs = dict(node_defs)
        base = defs["grayscale"]

        def empty_op(inputs, props):
            return {}

        defs["grayscale"] = NodeDefinition(
            base.type_name, base.title, base.category, base.inputs,
            base.outputs, base.param_schema, empty_op, base.description)
        engine = PipelineExecutor(defs)
        nodes = [make_start(),
                 make_node(defs, "solid-1", "solid_color",
                           {"width": 8, "height": 8}),
                 make_node(defs, "gray-1", "grayscale"),
                 make_node(defs, "prev-1", "preview")]
        edges = [exec_edge("start-1", "solid-1", from_pin=START_EXEC_OUT_PIN),
                 exec_edge("solid-1", "gray-1"),
                 exec_edge("gray-1", "prev-1"),
                 image_edge("solid-1", "gray-1"),
                 image_edge("gray-1", "prev-1")]
        recorder = StatusRecorder()
        summary = engine.run({"nodes": nodes, "edges": edges},
                             threading.Event(), _recorder_callbacks(recorder))
        assert summary["status"] == "error"
        assert "缺少输出引脚" in summary["errors"][0]["message"]
        assert recorder.previews == []
