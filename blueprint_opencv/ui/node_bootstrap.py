# -*- coding: utf-8 -*-
"""节点类型注册引导（ui 层）。

职责：把 ``function.node_catalog.NODE_DEFINITIONS`` 中的注册数据
（引脚 / 标题 / 分类 / 描述）经 UIKit ``register_node_type`` 注册进
蓝图注册表，并保证**幂等 + 同名冲突纠正**——既有 spec 与本插件
定义一致时直接跳过（热重载不产生重复注册或异常）；同名但引脚
定义不一致时（被其他插件/demo 覆盖注册，如 ui_demo 蓝图演示页的
in/out/img 引脚）重新注册纠正并记 WARNING，保证本插件画布创建
的节点引脚 id 与 function 层 op 契约一致。

设计说明：
- 注册数据（NODE_DEFINITIONS）由 function 层提供（SPEC §3.8）；
  accent 强调色是纯展示关注点，由本模块按分类映射（SPEC §3.0 色值），
  避免 function 层反向依赖 UIKit；
- 属性面板所需的 ``param_schema`` 查询与默认值回填也在此集中提供，
  ui 其他模块不直接触碰 function 层数据结构。
"""

from typing import Any, Dict, List, Optional

from InstructionX_UIKit.blueprint import NodeRegistry, register_node_type

from utils.logging_tools import LoggerManager, get_name

from ..function.node_catalog import NODE_DEFINITIONS

__all__ = [
    "ensure_node_types_registered",
    "param_schema_of",
    "apply_catalog_defaults",
]

_logger = LoggerManager()

#: 分类 → accent 强调色（SPEC §3.0 契约色值；展示关注点，ui 层持有）
CATEGORY_ACCENTS: Dict[str, str] = {
    "输入": "#4CAF50",
    "基础": "#2196F3",
    "滤波": "#9C27B0",
    "阈值与边缘": "#FF9800",
    "形态学": "#795548",
    "调整": "#00BCD4",
    "输出": "#F44336",
}

#: 模块名（日志用，get_name() 在模块级取一次即可）
_MODULE = get_name()


def ensure_node_types_registered() -> int:
    """把节点目录中的类型注册进 UIKit（幂等 + 同名冲突纠正）。

    UIKit ``NodeRegistry`` 是全局单例，其他插件（如 ui_demo 的蓝图
    演示页）可能用同名 ``type_name`` 注册引脚定义不同的 spec 并覆盖
    本插件的注册；若仅按「已注册即跳过」处理，本插件画布随后创建的
    节点会带上外来引脚 id（如 in/out/img），与 function 层 op 的
    输出键（image_out）不匹配，运行即报「上游节点缺少输出引脚」。
    因此本函数只在既有 spec 与本插件定义**一致**时跳过；同名异定义
    （冲突）时重新注册纠正并记 WARNING。

    返回:
        本次新注册或纠正的类型数量（全部一致时返回 0）。
    """
    registry = NodeRegistry.instance()
    registered = 0
    for definition in NODE_DEFINITIONS:
        spec = registry.spec(definition.type_name)
        if spec is not None and _spec_matches(spec, definition):
            continue  # 幂等：同名同定义跳过，重复调用不产生重复注册
        if spec is not None:
            _logger.warning(
                _MODULE,
                f"节点类型 {definition.type_name} 被他处同名注册覆盖，"
                "已纠正回本插件定义")
        _register_definition(definition)
        registered += 1
    _logger.info(_MODULE, f"节点类型注册完成：本次新注册/纠正 {registered} 个")
    return registered


def _spec_matches(spec, definition) -> bool:
    """判定注册表既有 spec 的引脚定义是否与本插件目录一致。"""
    return (_pin_keys(spec.inputs) == _pin_keys(definition.inputs)
            and _pin_keys(spec.outputs) == _pin_keys(definition.outputs))


def _pin_keys(pins: List[Dict[str, Any]]) -> List[tuple]:
    """取引脚 ``(id, data_type)`` 序列，用于定义一致性比较。"""
    return [(pin["id"], pin.get("data_type", "any")) for pin in pins]


def param_schema_of(type_name: str) -> List[Dict[str, Any]]:
    """按节点类型名取参数 schema（供属性面板建表单），未定义返回空表。"""
    definition = _find_definition(type_name)
    if definition is None:
        return []
    return list(definition.param_schema)


def apply_catalog_defaults(node) -> None:
    """把 schema 默认值以 setdefault 方式写入 ``node.properties``。

    参数:
        node: ``BlueprintNode`` 实例（画布上新创建的节点）。
    """
    for field in param_schema_of(node.type_name):
        node.properties.setdefault(field["key"], field.get("default"))


def _register_definition(definition) -> None:
    """注册单个节点类型（accent 按分类映射，无 body_builder）。"""
    register_node_type(
        definition.type_name,
        definition.title,
        definition.category,
        inputs=[dict(pin) for pin in definition.inputs],
        outputs=[dict(pin) for pin in definition.outputs],
        accent=CATEGORY_ACCENTS.get(definition.category),
        description=definition.description,
    )


def _find_definition(type_name: str) -> Optional[Any]:
    """在节点目录中按类型名查定义，未找到返回 ``None``。"""
    for definition in NODE_DEFINITIONS:
        if definition.type_name == type_name:
            return definition
    return None
