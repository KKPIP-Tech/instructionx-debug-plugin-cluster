# -*- coding: utf-8 -*-
"""阈值与边缘类节点 op 实现：threshold / adaptive_threshold / canny。

threshold 与 adaptive_threshold 需单通道输入，收到三通道时按
SPEC §3.0 自动转灰度（防御性，不报错）。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import NodeExecutionError, PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image, to_gray

# thresh_type 可选值（固定阈值）
THRESH_BINARY = "binary"
THRESH_BINARY_INV = "binary_inv"
THRESH_TRUNC = "trunc"
THRESH_TOZERO = "tozero"
THRESH_TOZERO_INV = "tozero_inv"

#: thresh_type → cv2 阈值类型常量映射
_THRESH_TYPE_MAP = {
    THRESH_BINARY: cv2.THRESH_BINARY,
    THRESH_BINARY_INV: cv2.THRESH_BINARY_INV,
    THRESH_TRUNC: cv2.THRESH_TRUNC,
    THRESH_TOZERO: cv2.THRESH_TOZERO,
    THRESH_TOZERO_INV: cv2.THRESH_TOZERO_INV,
}

# 自适应阈值 method 可选值
ADAPTIVE_MEAN = "mean"
ADAPTIVE_GAUSSIAN = "gaussian"

#: method → cv2 自适应方法常量映射
_ADAPTIVE_METHOD_MAP = {
    ADAPTIVE_MEAN: cv2.ADAPTIVE_THRESH_MEAN_C,
    ADAPTIVE_GAUSSIAN: cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
}

#: cv2.threshold 返回值索引（retval, dst）
_THRESHOLD_RESULT_INDEX = 1


def op_threshold(inputs: Dict[str, np.ndarray],
                 props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """固定阈值二值化（自动转灰度）。"""
    gray = to_gray(require_input_image(inputs))
    thresh = int(require_prop(props, "thresh"))
    max_value = int(require_prop(props, "max_value"))
    thresh_type = _THRESH_TYPE_MAP[str(require_prop(props, "thresh_type"))]
    result = cv2.threshold(gray, thresh, max_value, thresh_type)
    return {PIN_IMAGE_OUT: result[_THRESHOLD_RESULT_INDEX]}


def op_adaptive_threshold(inputs: Dict[str, np.ndarray],
                          props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """自适应阈值二值化（自动转灰度）。"""
    gray = to_gray(require_input_image(inputs))
    max_value = int(require_prop(props, "max_value"))
    method = _ADAPTIVE_METHOD_MAP[str(require_prop(props, "method"))]
    thresh_type = _THRESH_TYPE_MAP[str(require_prop(props, "thresh_type"))]
    block_size = int(require_prop(props, "block_size"))
    constant_c = int(require_prop(props, "c"))
    result = cv2.adaptiveThreshold(gray, max_value, method, thresh_type,
                                   block_size, constant_c)
    return {PIN_IMAGE_OUT: result}


def op_canny(inputs: Dict[str, np.ndarray],
             props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """Canny 边缘检测；low > high 视为参数非法。"""
    img = require_input_image(inputs)
    low = int(require_prop(props, "low"))
    high = int(require_prop(props, "high"))
    if low > high:
        raise NodeExecutionError(
            f"Canny 参数非法：低阈值 {low} 不能大于高阈值 {high}")
    return {PIN_IMAGE_OUT: cv2.Canny(img, low, high)}
