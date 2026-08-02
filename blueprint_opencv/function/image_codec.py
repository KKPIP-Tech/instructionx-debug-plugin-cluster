# -*- coding: utf-8 -*-
"""numpy 图像 ↔ PNG 字节编解码与尺寸归一（纯 cv2/numpy，不创建 QPixmap）。

本模块仅在工作线程活动：执行引擎把 preview 节点的图像编码为 PNG
字节后经回调上抛，UI 线程再自行解码 / 创建 QPixmap 显示。
"""

from typing import Any, Dict, Tuple

import cv2
import numpy as np

from .constants import (INFO_CHANNELS, INFO_HEIGHT, INFO_WIDTH,
                        NodeExecutionError)

#: PNG 编码格式标识（cv2.imencode 扩展名参数）
_PNG_EXT = ".png"

# 图像维度 / 通道索引
_DIM_HEIGHT = 0
_DIM_WIDTH = 1
_DIM_CHANNEL = 2
#: 单通道灰度图的维度数（shape 长度）
_NDIM_GRAY = 2


def encode_png(img: np.ndarray) -> bytes:
    """把 numpy 图像编码为 PNG 字节。

    异常:
        NodeExecutionError: 输入非法或编码失败。
    """
    if not isinstance(img, np.ndarray) or img.size == 0:
        raise NodeExecutionError("预览编码失败：图像数据为空")
    ok, buffer = cv2.imencode(_PNG_EXT, img)
    if not ok:
        raise NodeExecutionError("预览编码失败：cv2.imencode 返回失败")
    return buffer.tobytes()


def decode_png(data: bytes) -> np.ndarray:
    """把 PNG 字节解码为 numpy 图像（保持原通道数）。

    异常:
        NodeExecutionError: 数据非法或解码失败。
    """
    if not data:
        raise NodeExecutionError("PNG 解码失败：数据为空")
    array = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise NodeExecutionError("PNG 解码失败：数据不是有效的 PNG 图像")
    return img


def image_info(img: np.ndarray) -> Dict[str, Any]:
    """取图像元信息 dict：``{"width", "height", "channels"}``（SPEC §4.2.4）。"""
    channels = 1 if img.ndim == _NDIM_GRAY else int(img.shape[_DIM_CHANNEL])
    return {
        INFO_WIDTH: int(img.shape[_DIM_WIDTH]),
        INFO_HEIGHT: int(img.shape[_DIM_HEIGHT]),
        INFO_CHANNELS: channels,
    }


def normalize_size(img: np.ndarray, max_width: int,
                   max_height: int) -> np.ndarray:
    """等比缩小到不超过 (max_width, max_height)；未超限则原样返回。

    仅用于预览显示前的尺寸归一，不影响管线中的实际数据。
    """
    limit = _fit_scale(img, max_width, max_height)
    if limit >= 1.0:
        return img
    new_size = (int(img.shape[_DIM_WIDTH] * limit),
                int(img.shape[_DIM_HEIGHT] * limit))
    return cv2.resize(img, new_size, interpolation=cv2.INTER_AREA)


def _fit_scale(img: np.ndarray, max_width: int, max_height: int) -> float:
    """计算等比缩放系数（≤ 1 表示需要缩小，> 1 表示无需缩放）。"""
    width_ratio = max_width / img.shape[_DIM_WIDTH]
    height_ratio = max_height / img.shape[_DIM_HEIGHT]
    return min(width_ratio, height_ratio)
