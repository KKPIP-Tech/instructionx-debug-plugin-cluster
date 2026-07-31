# -*- coding: utf-8 -*-
"""节点类型注册引导（ui 层）。

职责：把 ``function.node_catalog.NODE_DEFINITIONS`` 中的注册数据
（引脚 / 标题 / 分类 / 描述）经 UIKit ``register_node_type`` 注册进
蓝图注册表的本插件命名空间（``REGISTRY_OWNER``），并保证**幂等 +
同名异定义纠正**——既有 spec 与本插件定义一致时直接跳过（热重载
不产生重复注册或异常）；同空间内同名但引脚定义不一致时（被本
插件自身旧版注册或异常覆盖）重新注册纠正并记 WARNING，保证本插件
画布创建的节点引脚 id 与 function 层 op 契约一致。

命名空间说明：UIKit ``NodeRegistry`` 支持 owner 命名空间，本插件
注册与查询均限定在 ``REGISTRY_OWNER`` 空间内，跨插件同名类型
（如 ui_demo 蓝图演示页的 in/out/img 引脚版 load_image）已不可能
互相覆盖；「同名异定义纠正」逻辑仅作为同空间内的防御保留。

设计说明：
- 注册数据（NODE_DEFINITIONS）由 function 层提供（SPEC §3.8）；
  accent 强调色是纯展示关注点，由本模块按分类映射（SPEC §3.0 色值），
  避免 function 层反向依赖 UIKit；
- 属性面板所需的 ``param_schema`` 查询与默认值回填也在此集中提供，
  ui 其他模块不直接触碰 function 层数据结构。
"""

from typing import Any, Callable, Dict, List, Optional

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from InstructionX_UIKit.blueprint import BlueprintNode, NodeRegistry, register_node_type

from utils.logging_tools import LoggerManager, get_name

from ..function.node_catalog import NODE_DEFINITIONS

__all__ = [
    "REGISTRY_OWNER",
    "ensure_node_types_registered",
    "param_schema_of",
    "apply_catalog_defaults",
]

_logger = LoggerManager()

#: 注册表命名空间标识（UIKit NodeRegistry owner）：本插件节点类型注册 /
#: 查询 / 画布创建均限定该空间，与其他插件同名类型互不覆盖
REGISTRY_OWNER = "blueprint-opencv"

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

#: 文件路径体区标签固定宽度（px）：与 NodeWidget MIN_W=160、两侧边距
#: 2*PAD_X=20 匹配，使含路径节点的宽度固定为 160 不随文件名膨胀
_PATH_LABEL_WIDTH = 140


def ensure_node_types_registered() -> int:
    """把节点目录中的类型注册进 UIKit 本插件命名空间（幂等 + 防御纠正）。

    注册与查询均限定 ``REGISTRY_OWNER`` 命名空间，跨插件同名类型
    注册已不可能覆盖本插件定义；但同空间内仍可能被本插件自身旧版
    注册或异常写入覆盖，因此本函数只在既有 spec 与本插件定义
    **一致**时跳过；同名异定义时重新注册纠正并记 WARNING（防御性语义）。

    返回:
        本次新注册或纠正的类型数量（全部一致时返回 0）。
    """
    registry = NodeRegistry.instance()
    registered = 0
    for definition in NODE_DEFINITIONS:
        spec = registry.spec(definition.type_name, owner=REGISTRY_OWNER)
        if spec is not None and _spec_matches(spec, definition):
            continue  # 幂等：同名同定义跳过，重复调用不产生重复注册
        if spec is not None:
            _logger.warning(
                _MODULE,
                f"节点类型 {definition.type_name} 在同空间内被同名异定义覆盖，"
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
    """注册单个节点类型（accent 按分类映射，文件参数节点带文件名体区）。"""
    register_node_type(
        definition.type_name,
        definition.title,
        definition.category,
        inputs=[dict(pin) for pin in definition.inputs],
        outputs=[dict(pin) for pin in definition.outputs],
        accent=CATEGORY_ACCENTS.get(definition.category),
        body_builder=_make_path_body_builder(definition),
        description=definition.description,
        owner=REGISTRY_OWNER,
    )


def _make_path_body_builder(definition) -> Optional[Callable]:
    """为含 file_path 参数的节点构建体区 builder，其余返回 ``None``。

    节点体缺省会展示 properties 键值原文，完整文件路径会把节点撑得
    很宽；这里改为只显示文件名（完整路径放 tooltip），并监听
    ``node.changed`` 在参数面板改值后同步刷新（体区 builder 仅在
    NodeWidget 构造时调用一次，不会自动重建）。
    """
    field = _file_path_field(definition)
    if field is None:
        return None

    def build_body(node: BlueprintNode, container) -> None:
        label = QLabel(container)
        # 固定体区宽度使节点宽度与文件名长度解耦（NodeWidget 按体区
        # sizeHint 计算节点宽），超长文件名中间省略，完整路径入 tooltip
        label.setFixedWidth(_PATH_LABEL_WIDTH)
        label.setToolTip(str(node.properties.get(field["key"], "")))
        _refresh_path_label(label, node, field)
        node.changed.connect(lambda: _refresh_path_label(label, node, field))
        container.layout().addWidget(label)

    return build_body


def _file_path_field(definition) -> Optional[Dict[str, Any]]:
    """取节点第一个 file_path 类型参数 schema，无则返回 ``None``。"""
    for field in definition.param_schema:
        if field.get("type") == "file_path":
            return field
    return None


def _refresh_path_label(label: QLabel, node: BlueprintNode,
                        field: Dict[str, Any]) -> None:
    """按当前 properties 刷新体区文件名显示（空路径显示占位提示）。"""
    path = str(node.properties.get(field["key"], "") or "")
    name = os.path.basename(path) if path else "（未设置）"
    text = f"{field.get('label', field['key'])}: {name}"
    elided = label.fontMetrics().elidedText(
        text, Qt.TextElideMode.ElideMiddle, _PATH_LABEL_WIDTH)
    label.setText(elided)
    label.setToolTip(path)


def _find_definition(type_name: str) -> Optional[Any]:
    """在节点目录中按类型名查定义，未找到返回 ``None``。"""
    for definition in NODE_DEFINITIONS:
        if definition.type_name == type_name:
            return definition
    return None
