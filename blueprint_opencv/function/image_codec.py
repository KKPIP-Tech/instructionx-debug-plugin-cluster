# -*- coding: utf-8 -*-
"""numpy 图像 → PNG 字节编码与图像元信息提取（纯 cv2/numpy，不创建 QPixmap）。

本模块仅在工作线程活动：执行引擎把 preview 节点的图像编码为 PNG
字节后经回调上抛，UI 线程再自行解码 / 创建 QPixmap 显示（UI 侧的
解码用 QPixmap.loadFromData，不经本模块）。
"""

from typing import Any, Dict

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


def image_info(img: np.ndarray) -> Dict[str, Any]:
    """取图像元信息 dict：``{"width", "height", "channels"}``（SPEC §4.2.4）。"""
    channels = 1 if img.ndim == _NDIM_GRAY else int(img.shape[_DIM_CHANNEL])
    return {
        INFO_WIDTH: int(img.shape[_DIM_WIDTH]),
        INFO_HEIGHT: int(img.shape[_DIM_HEIGHT]),
        INFO_CHANNELS: channels,
    }
