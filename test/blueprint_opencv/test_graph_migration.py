# -*- coding: utf-8 -*-
"""graph_migration.migrate_graph_dict 的单元测试。

覆盖范围：

- 污染引脚迁移：in/out/img 旧引脚按同方向索引映射纠正为目录标准
  定义，边的 from_pin / to_pin 同步改写，并补全 direction/multi
  序列化字段；
- 幂等：干净图迁移返回 ``(图, False)``，迁移结果再迁移无改动；
- 跳过策略：未在目录中的类型（start）保持原样；同方向引脚数量
  不等的节点跳过迁移并保留原引脚与边引用；
- 结构保持：外壳 ``{"graph": ...}`` 形态进出演化不变，输入 dict
  不被修改（深拷贝语义）。
"""

import copy

from plugin.blueprint_opencv.function.constants import (
    PIN_DATA_TYPE_EXEC,
)
from plugin.blueprint_opencv.function.graph_migration import migrate_graph_dict

from .conftest import make_node, make_start

#: 污染期旧存档的引脚 id（ui_demo 蓝图演示页覆盖注册的 in/out/img）
_POLLUTED_EXEC_IN = "in"
_POLLUTED_EXEC_OUT = "out"
_POLLUTED_IMAGE_PIN = "img"


def _pollute(pins: list, exec_id: str) -> list:
    """把标准引脚列表的 id 替换为污染期 id（exec→in/out，image→img）。"""
    return [{"id": exec_id if pin["data_type"] == PIN_DATA_TYPE_EXEC
             else _POLLUTED_IMAGE_PIN, "data_type": pin["data_type"]}
            for pin in pins]


def _polluted_node(node_defs, node_id: str, type_name: str) -> dict:
    """构造引脚被污染的节点 dict（引脚数量与标准定义一致、id 被污染）。"""
    definition = node_defs[type_name]
    return {"id": node_id, "type_name": type_name, "title": node_id,
            "properties": {},
            "inputs": _pollute(definition.inputs, _POLLUTED_EXEC_IN),
            "outputs": _pollute(definition.outputs, _POLLUTED_EXEC_OUT)}


def _polluted_graph(node_defs) -> dict:
    """构造污染图：start → solid_color → grayscale（exec + img 双线）。"""
    nodes = [make_start(),
             _polluted_node(node_defs, "solid-1", "solid_color"),
             _polluted_node(node_defs, "gray-1", "grayscale")]
    edges = [
        {"from_node": "start-1", "from_pin": "out",
         "to_node": "solid-1", "to_pin": "in"},
        {"from_node": "solid-1", "from_pin": "out",
         "to_node": "gray-1", "to_pin": "in"},
        {"from_node": "solid-1", "from_pin": "img",
         "to_node": "gray-1", "to_pin": "img"},
    ]
    return {"nodes": nodes, "edges": edges}


class TestPollutedMigration:
    """污染引脚纠正：引脚替换 + 边改写。"""

    def test_pins_replaced_with_standard(self, node_defs):
        """迁移后节点引脚 id / data_type 与目录标准定义一致。"""
        migrated, changed = migrate_graph_dict(
            _polluted_graph(node_defs), node_defs)
        assert changed is True
        for node_id, type_name in (("solid-1", "solid_color"),
                                   ("gray-1", "grayscale")):
            node = next(n for n in migrated["nodes"] if n["id"] == node_id)
            definition = node_defs[type_name]
            assert [p["id"] for p in node["inputs"]] == \
                   [p["id"] for p in definition.inputs]
            assert [p["id"] for p in node["outputs"]] == \
                   [p["id"] for p in definition.outputs]

    def test_migrated_pins_have_serialized_fields(self, node_defs):
        """迁移补全 direction / multi 序列化字段（UIKit from_dict 依赖）。"""
        migrated, _ = migrate_graph_dict(_polluted_graph(node_defs), node_defs)
        node = next(n for n in migrated["nodes"] if n["id"] == "gray-1")
        assert all(p["direction"] == "input" for p in node["inputs"])
        assert all(p["direction"] == "output" for p in node["outputs"])
        assert all("multi" in p for p in node["inputs"] + node["outputs"])

    def test_edges_rewritten(self, node_defs):
        """边的 from_pin / to_pin 按映射改写为标准引脚 id。"""
        migrated, _ = migrate_graph_dict(_polluted_graph(node_defs), node_defs)
        solid_exec, gray_exec, gray_img = migrated["edges"]
        # start 不在目录、引脚不迁移，但其 to_pin（solid 的 in）应改写
        assert solid_exec == {"from_node": "start-1", "from_pin": "out",
                              "to_node": "solid-1", "to_pin": "exec_in"}
        assert gray_exec["from_pin"] == "exec_out"
        assert gray_exec["to_pin"] == "exec_in"
        assert gray_img["from_pin"] == "image_out"
        assert gray_img["to_pin"] == "image_in"


class TestIdempotency:
    """幂等与跳过策略。"""

    def test_clean_graph_unchanged(self, node_defs):
        """干净图返回 changed=False，且内容逐键相等。"""
        graph = {"nodes": [make_start(),
                           make_node(node_defs, "gray-1", "grayscale")],
                 "edges": [{"from_node": "start-1", "from_pin": "out",
                            "to_node": "gray-1", "to_pin": "exec_in"}]}
        migrated, changed = migrate_graph_dict(graph, node_defs)
        assert changed is False
        assert migrated == graph

    def test_migration_is_idempotent(self, node_defs):
        """迁移结果再迁移：changed=False 且内容不变。"""
        once, changed = migrate_graph_dict(_polluted_graph(node_defs),
                                           node_defs)
        assert changed is True
        twice, changed_again = migrate_graph_dict(once, node_defs)
        assert changed_again is False
        assert twice == once

    def test_input_dict_not_mutated(self, node_defs):
        """输入 dict 深拷贝语义：原图在迁移后保持污染形态。"""
        graph = _polluted_graph(node_defs)
        snapshot = copy.deepcopy(graph)
        migrate_graph_dict(graph, node_defs)
        assert graph == snapshot

    def test_unknown_type_skipped(self, node_defs):
        """未在目录中的类型（start）引脚保持原样。"""
        migrated, _ = migrate_graph_dict(_polluted_graph(node_defs), node_defs)
        start = next(n for n in migrated["nodes"] if n["id"] == "start-1")
        assert start["outputs"] == make_start()["outputs"]

    def test_pin_count_mismatch_skipped(self, node_defs):
        """同方向引脚数量不等的节点跳过迁移（引脚与边引用保持原样）。"""
        node = _polluted_node(node_defs, "gray-1", "grayscale")
        node["inputs"] = node["inputs"][:1]  # 1 个输入引脚 vs 标准 2 个
        graph = {"nodes": [node],
                 "edges": [{"from_node": "gray-1", "from_pin": "img",
                            "to_node": "gray-1", "to_pin": "img"}]}
        migrated, changed = migrate_graph_dict(graph, node_defs)
        assert changed is False
        assert migrated["nodes"][0]["inputs"] == node["inputs"]
        assert migrated["nodes"][0]["outputs"] == node["outputs"]
        # 被跳过节点的边引用保持原值（不静默吞掉）
        assert migrated["edges"][0]["from_pin"] == "img"


class TestStructurePreservation:
    """外壳形态与空图边界。"""

    def test_shell_form_preserved(self, node_defs):
        """外壳 ``{"graph": ...}`` 进、外壳出，view 字段原样保留。"""
        inner = _polluted_graph(node_defs)
        shell = {"graph": inner, "view": {"zoom": 1.5, "offset": [3, 4]}}
        migrated, changed = migrate_graph_dict(shell, node_defs)
        assert changed is True
        assert "graph" in migrated and "nodes" not in migrated
        assert migrated["view"] == {"zoom": 1.5, "offset": [3, 4]}
        gray = next(n for n in migrated["graph"]["nodes"]
                    if n["id"] == "gray-1")
        assert [p["id"] for p in gray["inputs"]] == ["exec_in", "image_in"]

    def test_empty_graph(self, node_defs):
        """空图（无节点无边）迁移返回 changed=False。"""
        graph = {"nodes": [], "edges": []}
        migrated, changed = migrate_graph_dict(graph, node_defs)
        assert changed is False
        assert migrated == graph
