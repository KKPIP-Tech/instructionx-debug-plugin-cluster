# -*- coding: utf-8 -*-
"""存档图引脚自动迁移：把污染期旧存档的引脚纠正为目录标准定义（纯 Python，无 Qt）。

背景：UIKit ``NodeRegistry`` 是全局单例，曾被其他插件（ui_demo 蓝图
演示页）用 ``in/out/img`` 引脚覆盖注册同名的 ``load_image`` /
``gaussian_blur`` 等类型；该期间保存的图存档中节点引脚与边引用的是
污染引脚 id，而 UIKit ``BlueprintNode.from_dict`` 按存档原样重建
引脚、不跟注册表纠正，导致加载后运行报「上游节点缺少输出引脚「img」
的图像数据」。本模块在图快照进入运行路径前统一纠正（幂等）。

迁移策略：

- 未在目录中的类型（如内置 start）跳过，引脚保持原样；
- 节点引脚与目录定义按 ``(id, data_type)`` 序列比较，一致则跳过；
- 不一致且同方向数量相等时，按同方向索引位映射（旧第 i 个 → 标准
  第 i 个），引脚整体替换为标准定义（id/name/data_type 以目录为准，
  与 op 契约对齐），并据此改写所有边的 from_pin / to_pin；
- 同方向数量不等或无法确定时跳过该节点并记 WARNING（不强行纠正，
  避免错连）；边引用的引脚不在映射中时保持原值，留待运行校验报出。
"""

import copy
from typing import Any, Dict, List, Optional, Tuple

from utils.logging_tools import LoggerManager, get_name

from .node_catalog import NodeDefinition

__all__ = ["migrate_graph_dict"]

_logger = LoggerManager()
_MODULE = get_name()

#: Pin.to_dict 缺省数据类型（与 UIKit model.py 一致）
_DEFAULT_PIN_DATA_TYPE = "any"
#: 引脚序列化 direction 取值（与 UIKit PinDirection 一致）
_PIN_DIRECTION_INPUT = "input"
_PIN_DIRECTION_OUTPUT = "output"
#: 引脚映射表的方向键（输入 / 输出）
_MAP_KEY_INPUTS = "inputs"
_MAP_KEY_OUTPUTS = "outputs"

#: 节点引脚映射表类型：node_id -> {方向键: {旧引脚 id: 新引脚 id}}
PinMaps = Dict[str, Dict[str, Dict[str, str]]]


def migrate_graph_dict(
        graph: Dict[str, Any],
        node_defs: Dict[str, NodeDefinition]) -> Tuple[Dict[str, Any], bool]:
    """迁移存档图 dict 的节点引脚与边引用到目录标准定义。

    参数:
        graph: ``canvas.to_dict()`` 外壳（含 ``graph`` 键）或内层
            ``{"nodes","edges"}`` dict；输出保持原结构（外壳进外壳出）。
        node_defs: ``type_name -> NodeDefinition`` 目录定义表。

    返回:
        ``(迁移后的图 dict, 是否有改动)``；输入 dict 不被修改（深拷贝）。
        迁移幂等：对已干净的图重复调用返回 ``(图, False)``。
    """
    migrated = copy.deepcopy(graph)
    inner = _graph_inner(migrated)
    pin_maps, node_count = _migrate_nodes(inner.get("nodes", []), node_defs)
    edge_count = _migrate_edges(inner.get("edges", []), pin_maps)
    if node_count:
        _logger.info(
            _MODULE,
            f"存档图引脚迁移完成：纠正节点 {node_count} 个、改写边 {edge_count} 条")
    return migrated, node_count > 0


def _graph_inner(graph: Dict[str, Any]) -> Dict[str, Any]:
    """取内层 ``{"nodes","edges"}``（沿用 executor.normalize_graph 的兼容逻辑）。"""
    if "nodes" in graph:
        return graph
    return graph.get("graph", {})


def _migrate_nodes(
        nodes: List[dict],
        node_defs: Dict[str, NodeDefinition]) -> Tuple[PinMaps, int]:
    """逐节点迁移引脚，返回 ``(引脚映射表, 迁移节点数)``。"""
    pin_maps: PinMaps = {}
    for node in nodes:
        maps = _migrate_node_pins(node, node_defs)
        if maps is not None:
            pin_maps[node["id"]] = maps
    return pin_maps, len(pin_maps)


def _migrate_node_pins(
        node: dict,
        node_defs: Dict[str, NodeDefinition]) -> Optional[Dict[str, Dict[str, str]]]:
    """迁移单节点引脚为标准定义，返回方向映射；无需/无法迁移返回 ``None``。"""
    definition = node_defs.get(node.get("type_name", ""))
    if definition is None:
        return None  # 未在目录中的类型（如内置 start）保持原样
    in_map = _direction_map(node, node.get("inputs", []), definition.inputs, "输入")
    out_map = _direction_map(node, node.get("outputs", []), definition.outputs, "输出")
    if in_map is None or out_map is None:
        return None  # 数量不等无法确定映射，跳过该节点（已记 WARNING）
    if not in_map and not out_map:
        return None  # 引脚已与标准定义一致，跳过
    node[_MAP_KEY_INPUTS] = _serialized_pins(definition.inputs,
                                             _PIN_DIRECTION_INPUT)
    node[_MAP_KEY_OUTPUTS] = _serialized_pins(definition.outputs,
                                              _PIN_DIRECTION_OUTPUT)
    return {_MAP_KEY_INPUTS: in_map, _MAP_KEY_OUTPUTS: out_map}


def _serialized_pins(std_pins: List[dict], direction: str) -> List[dict]:
    """把目录引脚定义补全为 Pin.to_dict 序列化形态（含 direction/multi）。

    目录定义只有 ``{"id","name","data_type"}``；若缺 ``direction``，
    UIKit ``Pin.from_dict`` 会把输出引脚误置为 input 方向，导致画布
    按方向索引引脚时 ``ValueError``，因此迁移必须补全序列化字段。
    """
    return [{**pin, "direction": direction, "multi": bool(pin.get("multi", False))}
            for pin in std_pins]


def _direction_map(
        node: dict, saved_pins: List[dict],
        std_pins: List[dict], label: str) -> Optional[Dict[str, str]]:
    """构建单方向旧引脚 id → 标准引脚 id 映射（同方向索引位对应）。

    返回空 dict 表示已一致；返回 ``None`` 表示数量不等无法映射（记 WARNING）。
    """
    if _pin_keys(saved_pins) == _pin_keys(std_pins):
        return {}
    if len(saved_pins) != len(std_pins):
        _logger.warning(
            _MODULE,
            f"节点 {node.get('id')}（{node.get('type_name')}）{label}引脚数量 "
            f"{len(saved_pins)} 与标准定义 {len(std_pins)} 不符，跳过该节点迁移")
        return None
    return {saved["id"]: std["id"] for saved, std in zip(saved_pins, std_pins)}


def _pin_keys(pins: List[dict]) -> List[Tuple[str, str]]:
    """取引脚 ``(id, data_type)`` 序列，用于与标准定义的一致性比较。"""
    return [(pin.get("id"), pin.get("data_type", _DEFAULT_PIN_DATA_TYPE))
            for pin in pins]


def _migrate_edges(edges: List[dict], pin_maps: PinMaps) -> int:
    """按引脚映射改写边的 from_pin / to_pin，返回改写的边数。

    边引用的引脚不在映射中（未迁移节点的引脚）时保持原值，不静默吞掉，
    留待运行前校验 / 执行求值按原错误路径报出。
    """
    changed = 0
    for edge in edges:
        from_pin = _map_pin(pin_maps, edge.get("from_node"),
                            _MAP_KEY_OUTPUTS, edge.get("from_pin"))
        to_pin = _map_pin(pin_maps, edge.get("to_node"),
                          _MAP_KEY_INPUTS, edge.get("to_pin"))
        if from_pin != edge.get("from_pin") or to_pin != edge.get("to_pin"):
            edge["from_pin"], edge["to_pin"] = from_pin, to_pin
            changed += 1
    return changed


def _map_pin(pin_maps: PinMaps, node_id: Optional[str],
             direction: str, pin_id: Optional[str]) -> Optional[str]:
    """查引脚映射：命中返回新引脚 id，未命中返回原值。"""
    return pin_maps.get(node_id, {}).get(direction, {}).get(pin_id, pin_id)
