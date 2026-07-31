# -*- coding: utf-8 -*-
"""节点类型注册引导（ui 层）。

职责：把 ``function.node_catalog.NODE_DEFINITIONS`` 中的注册数据
（引脚 / 标题 / 分类 / 描述）经 UIKit ``register_node_type`` 注册进
蓝图注册表，并保证**幂等**——已注册过的 ``type_name`` 直接跳过，
热重载（重复 import / 重复调用）不产生重复注册或异常。

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
    """把节点目录中尚未注册的类型注册进 UIKit（幂等）。

    返回:
        本次新注册的类型数量（已注册跳过，重复调用返回 0）。
    """
    registry = NodeRegistry.instance()
    registered = 0
    for definition in NODE_DEFINITIONS:
        if registry.spec(definition.type_name) is not None:
            continue  # 幂等：先查后注册
        _register_definition(definition)
        registered += 1
    _logger.info(_MODULE, f"节点类型注册完成：本次新注册 {registered} 个")
    return registered


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
