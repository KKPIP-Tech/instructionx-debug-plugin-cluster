# -*- coding: utf-8 -*-
"""节点参数 schema 类型定义与校验（供属性面板 / 执行引擎共用）。

schema 条目为纯 dict，字段契约见 SPEC §3：``{key, label, type,
default, min?, max?, options?, odd?}``。本模块提供：

- 参数类型常量与 schema 构建辅助函数（``int_param`` 等）；
- ``resolve_props``：按 schema 合并默认值并逐项校验 / 类型转换，
  产出可直接交给 op 函数使用的 props dict；
- 校验失败统一抛 ``NodeExecutionError``（中文原因）。

参数默认值的唯一来源是各节点 schema 的 ``default`` 字段（SPEC §8），
本模块不重复定义任何默认值。
"""

import re
from typing import Any, Callable, Dict, List

from .constants import NodeExecutionError

# ---------------------------------------------------------------------------
# 参数类型常量（SPEC §3 type ∈ int/float/str/choice/file_path/color）
# ---------------------------------------------------------------------------

PARAM_INT = "int"
PARAM_FLOAT = "float"
PARAM_STR = "str"
PARAM_CHOICE = "choice"
PARAM_FILE_PATH = "file_path"
PARAM_COLOR = "color"

# schema dict 字段键名
SCHEMA_KEY = "key"
SCHEMA_LABEL = "label"
SCHEMA_TYPE = "type"
SCHEMA_DEFAULT = "default"
SCHEMA_MIN = "min"
SCHEMA_MAX = "max"
SCHEMA_OPTIONS = "options"
SCHEMA_ODD = "odd"

#: color 类型合法格式：#RRGGBB
_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


# ---------------------------------------------------------------------------
# schema 构建辅助（供 node_catalog 使用，避免重复字面量）
# ---------------------------------------------------------------------------

def int_param(key: str, label: str, default: int, min_value: int,
              max_value: int, odd: bool = False) -> dict:
    """构建 int 类型参数 schema；``odd=True`` 表示取奇数（偶数自动 +1）。"""
    spec = {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_INT,
            SCHEMA_DEFAULT: int(default), SCHEMA_MIN: int(min_value),
            SCHEMA_MAX: int(max_value)}
    if odd:
        spec[SCHEMA_ODD] = True
    return spec


def float_param(key: str, label: str, default: float, min_value: float,
                max_value: float) -> dict:
    """构建 float 类型参数 schema。"""
    return {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_FLOAT,
            SCHEMA_DEFAULT: float(default), SCHEMA_MIN: float(min_value),
            SCHEMA_MAX: float(max_value)}


def str_param(key: str, label: str, default: str = "") -> dict:
    """构建 str 类型参数 schema。"""
    return {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_STR,
            SCHEMA_DEFAULT: str(default)}


def choice_param(key: str, label: str, default: str, options: List[str]) -> dict:
    """构建 choice 类型参数 schema，``options`` 为可选值列表。"""
    return {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_CHOICE,
            SCHEMA_DEFAULT: str(default), SCHEMA_OPTIONS: list(options)}


def file_path_param(key: str, label: str, default: str = "") -> dict:
    """构建 file_path 类型参数 schema。"""
    return {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_FILE_PATH,
            SCHEMA_DEFAULT: str(default)}


def color_param(key: str, label: str, default: str) -> dict:
    """构建 color 类型参数 schema（值为 #RRGGBB hex 字符串）。"""
    return {SCHEMA_KEY: key, SCHEMA_LABEL: label, SCHEMA_TYPE: PARAM_COLOR,
            SCHEMA_DEFAULT: str(default)}


# ---------------------------------------------------------------------------
# 校验与合并
# ---------------------------------------------------------------------------

def require_prop(props: Dict[str, Any], key: str) -> Any:
    """取必需的参数值；缺失时抛 ``NodeExecutionError``（引擎契约外调用兜底）。"""
    if key not in props:
        raise NodeExecutionError(f"缺少参数: {key}")
    return props[key]


def resolve_props(schema: List[dict], props: Dict[str, Any]) -> Dict[str, Any]:
    """按 schema 合并默认值并逐项校验，返回可交给 op 的完整 props。

    以 schema key 为键产出经类型转换与范围校验的新 dict；``props`` 中
    schema 未声明的多余键被忽略。类型转换失败 / 越界 / 取值非法时抛
    ``NodeExecutionError``（中文原因）。
    """
    resolved: Dict[str, Any] = {}
    for spec in schema:
        key = spec[SCHEMA_KEY]
        raw = props.get(key, spec.get(SCHEMA_DEFAULT))
        resolved[key] = _validate_value(spec, raw)
    return resolved


def _validate_value(spec: dict, value: Any) -> Any:
    """按 schema 条目类型分派校验（查表替代 if-elif 长链）。"""
    ptype = spec[SCHEMA_TYPE]
    validator = _VALIDATORS.get(ptype)
    if validator is None:
        raise NodeExecutionError(f"未知参数类型: {ptype}")
    return validator(spec, value)


def _validate_int(spec: dict, value: Any) -> int:
    """int 校验：转换 → 奇数修正 → 范围检查。"""
    label = spec[SCHEMA_LABEL]
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise NodeExecutionError(f"参数「{label}」不是有效整数: {value!r}")
    if spec.get(SCHEMA_ODD) and result % 2 == 0:
        result += 1  # SPEC §3：int(odd) 偶数输入自动 +1
    return _check_range(result, spec, label)


def _validate_float(spec: dict, value: Any) -> float:
    """float 校验：转换 → 范围检查。"""
    label = spec[SCHEMA_LABEL]
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise NodeExecutionError(f"参数「{label}」不是有效数值: {value!r}")
    return _check_range(result, spec, label)


def _check_range(value: Any, spec: dict, label: str) -> Any:
    """数值范围检查，越界抛 ``NodeExecutionError``。"""
    min_value = spec.get(SCHEMA_MIN)
    max_value = spec.get(SCHEMA_MAX)
    if min_value is not None and value < min_value:
        raise NodeExecutionError(f"参数「{label}」小于下限 {min_value}: {value}")
    if max_value is not None and value > max_value:
        raise NodeExecutionError(f"参数「{label}」大于上限 {max_value}: {value}")
    return value


def _validate_choice(spec: dict, value: Any) -> str:
    """choice 校验：值必须在 options 内。"""
    options = spec.get(SCHEMA_OPTIONS, [])
    result = str(value)
    if result not in options:
        raise NodeExecutionError(
            f"参数「{spec[SCHEMA_LABEL]}」取值非法: {result}（可选: {options}）")
    return result


def _validate_str(spec: dict, value: Any) -> str:
    """str / file_path 校验：统一转为字符串。"""
    if value is None:
        return ""
    return str(value)


def _validate_color(spec: dict, value: Any) -> str:
    """color 校验：必须为 #RRGGBB 格式。"""
    result = str(value)
    if not _COLOR_PATTERN.match(result):
        raise NodeExecutionError(
            f"参数「{spec[SCHEMA_LABEL]}」颜色格式非法: {result}（应为 #RRGGBB）")
    return result


#: 参数类型 → 校验函数 分派表
_VALIDATORS: Dict[str, Callable[[dict, Any], Any]] = {
    PARAM_INT: _validate_int,
    PARAM_FLOAT: _validate_float,
    PARAM_STR: _validate_str,
    PARAM_CHOICE: _validate_choice,
    PARAM_FILE_PATH: _validate_str,
    PARAM_COLOR: _validate_color,
}
