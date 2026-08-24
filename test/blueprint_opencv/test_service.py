# -*- coding: utf-8 -*-
"""BlueprintOpenCVService 服务层的单元测试。

覆盖范围（均以共享 conftest 的 ``plugin_id`` fixture + tmp_path
DataProvider 隔离，不触碰真实运行数据目录）：

- 存档管理：save_graph / list_graphs / load_graph / delete_graph /
  rename_graph 的正常路径、往返一致性与元信息契约；
- 异常路径：空名 / 非法字符名、存档不存在、重名冲突、损坏存档
  （list 时 node_count 为 None、load 时回退示例图）；
- list_node_types：20 个节点定义、可 JSON 序列化；
- run_pipeline / stop_pipeline：未设置图快照报错、内联任务管理器
  跑通全流程（信号封送 + last_result_info）、挂起任务管理器验证
  「已有运行中」互斥。
"""

import json
from pathlib import Path

from plugin.blueprint_opencv.service import BlueprintOpenCVService

from .conftest import (
    InlineTaskManager,
    PendingTaskManager,
    solid_preview_graph,
)

#: 预置示例图资产（load_graph 的最终回退数据源，随插件仓库发布）
_PRESET_GRAPH_PATH = (
    Path(__file__).resolve().parents[2]
    / "blueprint_opencv" / "assets" / "preset_graph.json"
)

#: 测试用图名
_NAME_A = "alpha"
_NAME_B = "beta"
#: 含非法字符的图名样例（Windows 文件名禁用字符）
_INVALID_NAMES = ["", "   ", "a/b", "a\\b", "a:b", "a?b", "a*b"]


def _save(service: BlueprintOpenCVService, name: str) -> dict:
    """保存当前图快照并断言成功，返回 result dict。"""
    result = service.save_graph(name)
    assert result["success"] is True, result.get("error")
    return result


class TestSaveAndList:
    """save_graph / list_graphs 正常路径与元信息契约。"""

    def test_save_and_list(self, service):
        """保存后列表出现该存档：名称 / 节点数 / 大小 / 修改时间齐全。"""
        _save(service, _NAME_A)
        result = service.list_graphs()
        assert result["success"] is True
        graphs = result["data"]["graphs"]
        assert len(graphs) == 1
        meta = graphs[0]
        assert meta["name"] == _NAME_A
        assert meta["node_count"] == 0  # 初始空图快照
        assert meta["size_bytes"] > 0
        assert meta["modified_at"]

    def test_save_empty_name_uses_default(self, service):
        """边界：空名按缺省名 default 保存。"""
        result = _save(service, "")
        assert result["data"]["name"] == "default"

    def test_save_reports_node_count(self, service, node_defs):
        """保存的 node_count 与当前快照节点数一致。"""
        service.update_graph(solid_preview_graph(node_defs))
        result = _save(service, _NAME_A)
        assert result["data"]["node_count"] == 3

    def test_list_empty_when_no_archive(self, service):
        """尚未保存过时列表为空（而非报错）。"""
        result = service.list_graphs()
        assert result == {"success": True, "data": {"graphs": []}}

    def test_list_sorted_by_name(self, service):
        """多个存档按文件名排序返回。"""
        _save(service, "zeta")
        _save(service, _NAME_A)
        names = [g["name"] for g in service.list_graphs()["data"]["graphs"]]
        assert names == sorted(names)


class TestLoad:
    """load_graph 正常 / 回退路径。"""

    def test_round_trip(self, service, node_defs):
        """保存 → 加载往返：快照内容一致，fallback 为 False。"""
        graph = solid_preview_graph(node_defs)
        service.update_graph(graph)
        _save(service, _NAME_A)
        service.update_graph({"graph": {"nodes": [], "edges": []}})
        result = service.load_graph(_NAME_A)
        assert result["success"] is True
        assert result["data"]["fallback"] is False
        assert service.current_graph == graph

    def test_load_missing_falls_back(self, service):
        """存档不存在：回退预置示例图（assets/preset_graph.json），fallback=True。"""
        with open(_PRESET_GRAPH_PATH, encoding="utf-8") as fh:
            preset_nodes = len(json.load(fh)["graph"]["nodes"])
        result = service.load_graph("no_such_graph")
        assert result["success"] is True
        assert result["data"]["fallback"] is True
        payload = service.current_graph.get("graph", service.current_graph)
        assert len(payload["nodes"]) == preset_nodes

    def test_load_corrupted_falls_back(self, service):
        """存档损坏（非 JSON）：load 回退示例图，list 中 node_count 为 None。"""
        _save(service, _NAME_A)
        archive = service._storage_dir() / f"{_NAME_A}.json"
        archive.write_bytes(b"not a json {")
        result = service.load_graph(_NAME_A)
        assert result["success"] is True
        assert result["data"]["fallback"] is True
        meta = service.list_graphs()["data"]["graphs"][0]
        assert meta["node_count"] is None


class TestDelete:
    """delete_graph 正常与异常路径。"""

    def test_delete_ok(self, service):
        """删除存在的存档：成功后列表为空。"""
        _save(service, _NAME_A)
        result = service.delete_graph(_NAME_A)
        assert result == {"success": True, "data": {"name": _NAME_A}}
        assert service.list_graphs()["data"]["graphs"] == []

    def test_delete_missing(self, service):
        """异常路径：删除不存在的存档报「存档不存在」。"""
        result = service.delete_graph("ghost")
        assert result["success"] is False
        assert "存档不存在" in result["error"]

    def test_delete_invalid_names(self, service):
        """异常路径：空名 / 含非法字符名报中文校验错误，不做文件操作。"""
        for bad in _INVALID_NAMES:
            result = service.delete_graph(bad)
            assert result["success"] is False, f"应拒绝非法图名: {bad!r}"
            assert "图名" in result["error"]


class TestRename:
    """rename_graph 正常与异常路径。"""

    def test_rename_ok(self, service):
        """重命名后旧名消失、新名可加载。"""
        _save(service, _NAME_A)
        result = service.rename_graph(_NAME_A, _NAME_B)
        assert result == {"success": True,
                          "data": {"old_name": _NAME_A, "new_name": _NAME_B}}
        names = [g["name"] for g in service.list_graphs()["data"]["graphs"]]
        assert names == [_NAME_B]
        assert service.load_graph(_NAME_B)["data"]["fallback"] is False

    def test_rename_missing_source(self, service):
        """异常路径：旧存档不存在报「存档不存在」。"""
        result = service.rename_graph("ghost", _NAME_B)
        assert result["success"] is False
        assert "存档不存在" in result["error"]

    def test_rename_conflict(self, service):
        """异常路径：新名已存在报「已存在同名存档」。"""
        _save(service, _NAME_A)
        _save(service, _NAME_B)
        result = service.rename_graph(_NAME_A, _NAME_B)
        assert result["success"] is False
        assert "已存在同名存档" in result["error"]

    def test_rename_invalid_names(self, service):
        """异常路径：旧名 / 新名含非法字符均被拒绝。"""
        _save(service, _NAME_A)
        for old, new in (("a/b", _NAME_B), (_NAME_A, "b?c")):
            result = service.rename_graph(old, new)
            assert result["success"] is False
            assert "图名" in result["error"]


class TestListNodeTypes:
    """list_node_types 契约。"""

    def test_twenty_serializable_nodes(self, service):
        """返回 20 个节点定义，剔除 op 后可 JSON 序列化。"""
        result = service.list_node_types()
        assert result["success"] is True
        nodes = result["data"]["nodes"]
        assert len(nodes) == 20
        json.dumps(nodes, ensure_ascii=False)  # 不抛异常即可序列化
        assert all("op" not in node for node in nodes)
        type_names = {node["type_name"] for node in nodes}
        assert {"load_image", "grayscale", "canny", "preview",
                "save_image"} <= type_names


class TestRunPipeline:
    """run_pipeline / stop_pipeline / get_last_result_info。"""

    def test_run_without_graph(self, service):
        """未设置图快照：返回中文错误而非抛异常。"""
        result = service.run_pipeline()
        assert result["success"] is False
        assert "尚未设置图快照" in result["error"]

    def test_run_inline_success(self, qapp, plugin_id, provider, node_defs):
        """内联任务管理器跑通：信号封送齐全、结果信息 done、preview 落库。"""
        service = BlueprintOpenCVService(
            plugin_id=plugin_id, data_provider=provider,
            task_manager=InlineTaskManager())
        service.update_graph(solid_preview_graph(node_defs))
        finished, previews, statuses = [], [], []
        service.run_finished.connect(finished.append)
        service.preview_ready.connect(lambda data, info: previews.append(info))
        service.node_status_changed.connect(
            lambda nid, st, ms, msg: statuses.append((nid, st)))
        result = service.run_pipeline()
        assert result == {"success": True, "data": {"started": True}}
        assert len(finished) == 1
        assert finished[0]["status"] == "done"
        assert len(previews) == 1
        assert ("solid-1", "done") in statuses
        info = service.get_last_result_info()
        assert info["success"] is True
        assert info["data"]["status"] == "done"
        assert info["data"]["preview"] is not None

    def test_run_busy_rejected(self, plugin_id, provider, node_defs):
        """挂起任务管理器：运行中再次运行被拒，drain 后状态 done。"""
        task_manager = PendingTaskManager()
        service = BlueprintOpenCVService(
            plugin_id=plugin_id, data_provider=provider,
            task_manager=task_manager)
        service.update_graph(solid_preview_graph(node_defs))
        assert service.run_pipeline()["success"] is True
        rejected = service.run_pipeline()
        assert rejected["success"] is False
        assert "已有运行中的管线" in rejected["error"]
        task_manager.drain()
        assert service.get_last_result_info()["data"]["status"] == "done"

    def test_run_validation_error(self, plugin_id, provider):
        """图校验失败（无 start）：返回中文错误，不进入后台。"""
        service = BlueprintOpenCVService(
            plugin_id=plugin_id, data_provider=provider,
            task_manager=PendingTaskManager())
        service.update_graph({"nodes": [], "edges": []})
        result = service.run_pipeline()
        assert result["success"] is False
        assert "无 start 节点" in result["error"]

    def test_stop_pipeline_always_success(self, service):
        """stop_pipeline 幂等：未运行时也返回成功。"""
        assert service.stop_pipeline() == {
            "success": True, "data": {"stopping": True}}

    def test_shutdown_no_raise(self, plugin_id, provider, node_defs):
        """shutdown：运行中请求停止不抛异常。"""
        service = BlueprintOpenCVService(
            plugin_id=plugin_id, data_provider=provider,
            task_manager=PendingTaskManager())
        service.update_graph(solid_preview_graph(node_defs))
        service.run_pipeline()
        service.shutdown()  # 不抛异常即通过
