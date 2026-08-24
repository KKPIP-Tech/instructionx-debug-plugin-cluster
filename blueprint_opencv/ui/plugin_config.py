# -*- coding: utf-8 -*-
"""插件配置读取（ui 层唯一入口，无业务逻辑）。

``config/default.json`` 的读取与缺省回退集中在模块：配置缺失 /
损坏 / 键不存在 / 类型不符时记 WARNING 并回退 SPEC §8 的约定缺省值。

边界约定：service / function 层**不读配置**（跨插件 / MCP 调用路径
不依赖配置文件），其缺省值由 ``function/constants.py`` 与
``service.py`` 的命名常量承载；配置仅由 ui 层读取后经 service 的
内部方法（如 ``set_max_nodes``）透传到运行层。
"""

import json
from pathlib import Path
from typing import Any, Dict, Tuple

from utils.logging_tools import LoggerManager, get_name

from ..function.constants import DEFAULT_MAX_NODES

__all__ = [
    "graph_max_nodes",
    "min_canvas_width",
    "preview_max_size",
    "right_panel_width",
    "sample_image_path",
]

#: 插件默认配置文件路径与插件根目录（相对路径配置的解析基准）
_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "default.json"
_PLUGIN_ROOT = Path(__file__).resolve().parents[1]

# 各配置项缺省值（SPEC §8 约定值；配置缺失 / 损坏时的回退）
_FALLBACK_RIGHT_PANEL_WIDTH = 320
_FALLBACK_MIN_CANVAS_WIDTH = 480
_FALLBACK_PREVIEW_WIDTH = 960
_FALLBACK_PREVIEW_HEIGHT = 720
#: 预置示例输入图相对路径缺省值（config assets.sample_image 缺省时的回退）
_FALLBACK_SAMPLE_IMAGE = "assets/sample.png"

_logger = LoggerManager()
_MODULE = get_name()


def right_panel_width() -> int:
    """右侧固定面板宽（panel.right_panel_width）。"""
    return _read_int("panel", "right_panel_width", _FALLBACK_RIGHT_PANEL_WIDTH)


def min_canvas_width() -> int:
    """画布最小宽度（panel.min_canvas_width，防压缩至不可操作）。"""
    return _read_int("panel", "min_canvas_width", _FALLBACK_MIN_CANVAS_WIDTH)


def preview_max_size() -> Tuple[int, int]:
    """预览显示等比缩放上限（preview.max_width / max_height，仅影响显示）。"""
    return (_read_int("preview", "max_width", _FALLBACK_PREVIEW_WIDTH),
            _read_int("preview", "max_height", _FALLBACK_PREVIEW_HEIGHT))


def graph_max_nodes() -> int:
    """单次运行节点数防御性上限（graph.max_nodes，经 service 透传运行层）。"""
    return _read_int("graph", "max_nodes", DEFAULT_MAX_NODES)


def sample_image_path() -> Path:
    """预置示例输入图绝对路径（assets.sample_image 相对插件根目录解析）。"""
    relative = str(_read_key("assets", "sample_image", _FALLBACK_SAMPLE_IMAGE))
    return _PLUGIN_ROOT / relative


def _read_int(group: str, key: str, fallback: int) -> int:
    """读取整数配置项；缺失 / 非整数记 WARNING 并回退缺省值。"""
    value = _read_key(group, key, fallback)
    try:
        return int(value)
    except (TypeError, ValueError):
        _logger.warning(
            _MODULE, f"配置项 {group}.{key} 非整数（回退 {fallback}）: {value!r}")
        return fallback


def _read_key(group: str, key: str, fallback: Any) -> Any:
    """读取单个配置键；配置缺失 / 损坏 / 键不存在时回退缺省值（记 WARNING）。"""
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
        section = data[group]
        return section.get(key, fallback)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        _logger.warning(
            _MODULE, f"读取配置项 {group}.{key} 失败（回退 {fallback}）: {e}")
        return fallback
