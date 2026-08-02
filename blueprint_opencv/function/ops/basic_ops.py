# -*- coding: utf-8 -*-
"""基础类节点 op 实现：grayscale / invert / resize / flip / rotate。

choice 参数取值常量（scale_mode / interpolation / direction / angle）
集中定义在本模块，作为节点 schema options 的唯一来源。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image, to_gray

# scale_mode 可选值
SCALE_MODE_FIXED = "fixed"
SCALE_MODE_SCALE = "scale"

# interpolation 可选值
INTERP_NEAREST = "nearest"
INTERP_LINEAR = "linear"
INTERP_CUBIC = "cubic"
INTERP_AREA = "area"

#: interpolation → cv2 插值常量映射
_INTERP_MAP = {
    INTERP_NEAREST: cv2.INTER_NEAREST,
    INTERP_LINEAR: cv2.INTER_LINEAR,
    INTERP_CUBIC: cv2.INTER_CUBIC,
    INTERP_AREA: cv2.INTER_AREA,
}

# flip direction 可选值
FLIP_HORIZONTAL = "horizontal"
FLIP_VERTICAL = "vertical"
FLIP_BOTH = "both"

#: direction → cv2.flip flipCode 映射
_FLIP_MAP = {
    FLIP_HORIZONTAL: 1,
    FLIP_VERTICAL: 0,
    FLIP_BOTH: -1,
}

# rotate angle 可选值
ROTATE_90_CW = "90_cw"
ROTATE_180 = "180"
ROTATE_90_CCW = "90_ccw"

#: angle → cv2.rotate 常量映射
_ROTATE_MAP = {
    ROTATE_90_CW: cv2.ROTATE_90_CLOCKWISE,
    ROTATE_180: cv2.ROTATE_180,
    ROTATE_90_CCW: cv2.ROTATE_90_COUNTERCLOCKWISE,
}


def op_grayscale(inputs: Dict[str, np.ndarray],
                 props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """灰度化：三通道转单通道，已是单通道则透传。"""
    return {PIN_IMAGE_OUT: to_gray(require_input_image(inputs))}


def op_invert(inputs: Dict[str, np.ndarray],
              props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """反色：按位取反。"""
    return {PIN_IMAGE_OUT: cv2.bitwise_not(require_input_image(inputs))}


def op_resize(inputs: Dict[str, np.ndarray],
              props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """缩放：scale 模式按倍率，fixed 模式按目标宽高，插值方式可选。"""
    img = require_input_image(inputs)
    mode = str(require_prop(props, "scale_mode"))
    interp = _INTERP_MAP[str(require_prop(props, "interpolation"))]
    if mode == SCALE_MODE_FIXED:
        width = int(require_prop(props, "width"))
        height = int(require_prop(props, "height"))
        result = cv2.resize(img, (width, height), interpolation=interp)
    else:
        scale = float(require_prop(props, "scale"))
        result = cv2.resize(img, None, fx=scale, fy=scale, interpolation=interp)
    return {PIN_IMAGE_OUT: result}


def op_flip(inputs: Dict[str, np.ndarray],
            props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """翻转：水平 / 垂直 / 同时。"""
    img = require_input_image(inputs)
    flip_code = _FLIP_MAP[str(require_prop(props, "direction"))]
    return {PIN_IMAGE_OUT: cv2.flip(img, flip_code)}


def op_rotate(inputs: Dict[str, np.ndarray],
              props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """旋转：90° 顺时针 / 180° / 90° 逆时针。"""
    img = require_input_image(inputs)
    rotate_code = _ROTATE_MAP[str(require_prop(props, "angle"))]
    return {PIN_IMAGE_OUT: cv2.rotate(img, rotate_code)}
