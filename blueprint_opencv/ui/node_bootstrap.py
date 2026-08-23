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

from core.interfaces import ILocalizationFacade
from utils.logging_tools import LoggerManager, get_name

from ..function.node_catalog import NODE_DEFINITIONS

__all__ = [
    "REGISTRY_OWNER",
    "ensure_node_types_registered",
    "param_schema_of",
    "param_label_of",
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

#: 取词分组名（与 text/zh.xml 的 <group name="..."> 一致）
_GROUP_NODES = "nodes"
_GROUP_CATEGORIES = "categories"
_GROUP_PINS = "pins"
_GROUP_PARAMS = "params"
_GROUP_NODE_BODY = "node_body"

#: 节点分类（中文原文，function/constants.py）→ 语言文件键
_CATEGORY_KEYS: Dict[str, str] = {
    "输入": "input",
    "基础": "basic",
    "滤波": "filter",
    "阈值与边缘": "threshold",
    "形态学": "morphology",
    "调整": "adjust",
    "输出": "output",
}

#: 引脚数据类型 → 语言文件键（pins 组）
_PIN_NAME_KEYS: Dict[str, str] = {
    "exec": "pin.exec",
    "image": "pin.image",
}

#: 体区空路径占位的中文原文（i18n 未注入时的回退值，与 zh.xml 一致）
_NOT_SET_FALLBACK = "（未设置）"


def _tr_text(i18n: Optional[ILocalizationFacade], group: str, key: str,
             fallback: str) -> str:
    """经门面取词；门面未注入时回退目录中文原文（注册早于注入的兼容路径）。"""
    if i18n is None:
        return fallback
    return i18n.tr(group, key)


def _node_text(i18n: Optional[ILocalizationFacade], definition,
               key_suffix: str, fallback: str) -> str:
    """取节点标题 / 描述文案（键 ``node.{type_name}.{key_suffix}``）。"""
    key = f"node.{definition.type_name}.{key_suffix}"
    return _tr_text(i18n, _GROUP_NODES, key, fallback)


def _category_text(i18n: Optional[ILocalizationFacade], category: str) -> str:
    """取分类显示文案（未知名分类回退原文）。"""
    key = _CATEGORY_KEYS.get(category)
    if key is None:
        return category
    return _tr_text(i18n, _GROUP_CATEGORIES, key, category)


def _pin_name(i18n: Optional[ILocalizationFacade], pin: Dict[str, Any]) -> str:
    """取引脚显示名（按 data_type 取词，未知类型回退原文）。"""
    original = str(pin.get("name", ""))
    key = _PIN_NAME_KEYS.get(pin.get("data_type"))
    if key is None:
        return original
    return _tr_text(i18n, _GROUP_PINS, key, original)


def _translated_pins(pins: List[Dict[str, Any]],
                     i18n: Optional[ILocalizationFacade]) -> List[Dict[str, Any]]:
    """逐份拷贝引脚定义并翻译显示名（不改动共享模板对象）。"""
    return [{**pin, "name": _pin_name(i18n, pin)} for pin in pins]


def ensure_node_types_registered(
        i18n: Optional[ILocalizationFacade] = None) -> int:
    """把节点目录中的类型注册进 UIKit 本插件命名空间（幂等 + 同名异定义纠正）。

    标题 / 分类 / 引脚名 / 描述按 ``i18n`` 当前语言取词；一致性比较同样
    按翻译后文本进行，语言切换后重复调用经纠正机制自然完成重注册
    （详见 docs/req/2026-08-22/SPEC-i18n §D5）。

    参数:
        i18n: 取词门面（可选；缺省按目录中文原文注册，兼容模块级 /
            独立运行等注册早于门面注入的路径）。

    返回:
        本次新注册或纠正的类型数量（全部一致时返回 0）。
    """
    registry = NodeRegistry.instance()
    registered = sum(_sync_definition(registry, d, i18n)
                     for d in NODE_DEFINITIONS)
    _logger.info(_MODULE, f"节点类型注册完成：本次新注册/纠正 {registered} 个")
    return registered


def _sync_definition(registry, definition,
                     i18n: Optional[ILocalizationFacade]) -> int:
    """同步单个类型定义：一致跳过（幂等），缺失 / 异定义注册纠正。"""
    spec = registry.spec(definition.type_name, owner=REGISTRY_OWNER)
    if spec is not None and _spec_matches(spec, definition, i18n):
        return 0  # 幂等：同名同定义跳过，重复调用不产生重复注册
    if spec is not None:
        _logger.warning(
            _MODULE,
            f"节点类型 {definition.type_name} 在同空间内被同名异定义覆盖"
            "（或界面语言已切换），已纠正回本插件当前语言定义")
    _register_definition(definition, i18n)
    return 1


def _spec_matches(spec, definition, i18n: Optional[ILocalizationFacade]) -> bool:
    """判定既有 spec 是否与本插件定义一致（引脚 id/类型/名称 + 标题 + 分类）。"""
    return (_pin_keys(spec.inputs) == _pin_keys(
                _translated_pins(definition.inputs, i18n))
            and _pin_keys(spec.outputs) == _pin_keys(
                _translated_pins(definition.outputs, i18n))
            and spec.title == _node_text(i18n, definition, "title",
                                         definition.title)
            and spec.category == _category_text(i18n, definition.category))


def _pin_keys(pins: List[Dict[str, Any]]) -> List[tuple]:
    """取引脚 ``(id, data_type, name)`` 序列，用于定义一致性比较。"""
    return [(pin["id"], pin.get("data_type", "any"),
             str(pin.get("name", ""))) for pin in pins]


def param_schema_of(type_name: str) -> List[Dict[str, Any]]:
    """按节点类型名取参数 schema（供属性面板建表单），未定义返回空表。"""
    definition = _find_definition(type_name)
    if definition is None:
        return []
    return list(definition.param_schema)


def param_label_of(i18n: Optional[ILocalizationFacade], type_name: str,
                   field: Dict[str, Any]) -> str:
    """取参数标签显示文案（键 ``param.{type_name}.{key}``）。

    供属性面板表单与节点体区共用；门面未注入时回退 schema 中文原文。
    """
    fallback = str(field.get("label", field["key"]))
    key = f"param.{type_name}.{field['key']}"
    return _tr_text(i18n, _GROUP_PARAMS, key, fallback)


def apply_catalog_defaults(node) -> None:
    """把 schema 默认值以 setdefault 方式写入 ``node.properties``。

    参数:
        node: ``BlueprintNode`` 实例（画布上新创建的节点）。
    """
    for field in param_schema_of(node.type_name):
        node.properties.setdefault(field["key"], field.get("default"))


def _register_definition(definition,
                         i18n: Optional[ILocalizationFacade]) -> None:
    """注册单个节点类型（标题/分类/引脚名/描述按当前语言取词）。"""
    register_node_type(
        definition.type_name,
        _node_text(i18n, definition, "title", definition.title),
        _category_text(i18n, definition.category),
        inputs=_translated_pins(definition.inputs, i18n),
        outputs=_translated_pins(definition.outputs, i18n),
        accent=CATEGORY_ACCENTS.get(definition.category),
        body_builder=_make_path_body_builder(definition, i18n),
        description=_node_text(i18n, definition, "desc", definition.description),
        owner=REGISTRY_OWNER,
    )


def _make_path_body_builder(definition,
                            i18n: Optional[ILocalizationFacade]) -> Optional[Callable]:
    """为含 file_path 参数的节点构建体区 builder（标签经 i18n 取词），其余返回 ``None``。"""
    field = _file_path_field(definition)
    if field is None:
        return None

    def build_body(node: BlueprintNode, container) -> None:
        label = QLabel(container)
        # 固定体区宽度使节点宽度与文件名长度解耦（NodeWidget 按体区
        # sizeHint 计算节点宽），超长文件名中间省略，完整路径入 tooltip
        label.setFixedWidth(_PATH_LABEL_WIDTH)
        label.setToolTip(str(node.properties.get(field["key"], "")))
        _refresh_path_label(label, node, field, i18n)
        node.changed.connect(
            lambda: _refresh_path_label(label, node, field, i18n))
        container.layout().addWidget(label)

    return build_body


def _file_path_field(definition) -> Optional[Dict[str, Any]]:
    """取节点第一个 file_path 类型参数 schema，无则返回 ``None``。"""
    for field in definition.param_schema:
        if field.get("type") == "file_path":
            return field
    return None


def _refresh_path_label(label: QLabel, node: BlueprintNode,
                        field: Dict[str, Any],
                        i18n: Optional[ILocalizationFacade] = None) -> None:
    """按当前 properties 刷新体区文件名显示（空路径显示本地化占位提示）。"""
    path = str(node.properties.get(field["key"], "") or "")
    not_set = _tr_text(i18n, _GROUP_NODE_BODY, "not_set", _NOT_SET_FALLBACK)
    name = os.path.basename(path) if path else not_set
    text = f"{param_label_of(i18n, node.type_name, field)}: {name}"
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
