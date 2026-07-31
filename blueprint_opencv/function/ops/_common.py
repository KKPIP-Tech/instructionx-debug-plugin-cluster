# -*- coding: utf-8 -*-
"""ops 包内部共享的图像辅助函数（私有模块，不对外导出）。

集中放置各 op 模块共用的防御性校验与通道适配逻辑，避免在多个
op 模块中重复实现：

- ``require_input_image``：取 ``image_in`` 输入并做存在性校验；
- ``to_gray`` / ``to_bgr``：SPEC §3.0 灰度 / 三通道自动适配；
- ``hex_to_bgr``：#RRGGBB 字符串转 BGR 元组（solid_color 使用）。
"""

from typing import Any, Dict, Tuple

import cv2
import numpy as np

from ..constants import NodeExecutionError, PIN_IMAGE_IN
from ..param_schema import require_prop

#: 图像维度索引（np.ndarray shape 语义）
_DIM_HEIGHT = 0
_DIM_WIDTH = 1
#: 三通道彩色图的通道数
_CHANNELS_COLOR = 3


def require_input_image(inputs: Dict[str, np.ndarray]) -> np.ndarray:
    """取 ``image_in`` 输入图像；未连接 / 数据非法时抛中文错误。

    参数:
        inputs: op 入参，以输入引脚 id 为键的图像 dict。

    异常:
        NodeExecutionError: 输入缺失或不是合法图像数组。
    """
    img = inputs.get(PIN_IMAGE_IN)
    if img is None:
        raise NodeExecutionError("输入未连接：缺少图像输入")
    if not isinstance(img, np.ndarray) or img.size == 0:
        raise NodeExecutionError("输入图像数据非法（不是有效的图像数组）")
    return img


def is_color(img: np.ndarray) -> bool:
    """判断图像是否为三通道彩色（BGR）。"""
    return img.ndim == _CHANNELS_COLOR and img.shape[2] == _CHANNELS_COLOR


def to_gray(img: np.ndarray) -> np.ndarray:
    """转为单通道灰度；已是单通道则原样透传（SPEC §3.0 防御性适配）。"""
    if is_color(img):
        return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return img


def to_bgr(img: np.ndarray) -> np.ndarray:
    """转为三通道 BGR；已是三通道则原样透传。"""
    if not is_color(img):
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    return img


def hex_to_bgr(value: str) -> Tuple[int, int, int]:
    """``#RRGGBB`` 字符串转 ``(B, G, R)`` 元组；非法格式抛中文错误。"""
    text = str(value).lstrip("#")
    if len(text) != _CHANNELS_COLOR * 2:
        raise NodeExecutionError(f"颜色格式非法: {value}（应为 #RRGGBB）")
    try:
        red = int(text[0:2], 16)
        green = int(text[2:4], 16)
        blue = int(text[4:6], 16)
    except ValueError:
        raise NodeExecutionError(f"颜色格式非法: {value}（应为 #RRGGBB）")
    return blue, green, red


def image_size(props: Dict[str, Any], width_key: str, height_key: str) -> Tuple[int, int]:
    """从 props 取 (width, height)，由 param_schema 保证已校验。"""
    return int(require_prop(props, width_key)), int(require_prop(props, height_key))
