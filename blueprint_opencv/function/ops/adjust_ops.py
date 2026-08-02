# -*- coding: utf-8 -*-
"""调整类节点 op 实现：brightness_contrast / sharpen / hsv_convert。

hsv_convert 的 direction 取值常量定义在本模块，作为节点 schema
options 的唯一来源。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image, to_bgr

# hsv_convert direction 可选值
HSV_TO_HSV = "to_hsv"
HSV_FROM_HSV = "from_hsv"

#: 锐化反锐化掩模的高斯模糊标准差（核大小由 sigma 自动推导）
_SHARPEN_BLUR_SIGMA = 3.0


def op_brightness_contrast(inputs: Dict[str, np.ndarray],
                           props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """亮度对比度调整：alpha 对比度、beta 亮度。"""
    img = require_input_image(inputs)
    alpha = float(require_prop(props, "alpha"))
    beta = float(require_prop(props, "beta"))
    result = cv2.convertScaleAbs(img, alpha=alpha, beta=beta)
    return {PIN_IMAGE_OUT: result}


def op_sharpen(inputs: Dict[str, np.ndarray],
               props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """锐化：反锐化掩模 img*(1+s) - blur*s。"""
    img = require_input_image(inputs)
    strength = float(require_prop(props, "strength"))
    blur = cv2.GaussianBlur(img, (0, 0), _SHARPEN_BLUR_SIGMA)
    result = cv2.addWeighted(img, 1.0 + strength, blur, -strength, 0)
    return {PIN_IMAGE_OUT: result}


def op_hsv_convert(inputs: Dict[str, np.ndarray],
                   props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """HSV 转换：需三通道（单通道先转 BGR），方向可选。"""
    img = to_bgr(require_input_image(inputs))
    direction = str(require_prop(props, "direction"))
    if direction == HSV_FROM_HSV:
        return {PIN_IMAGE_OUT: cv2.cvtColor(img, cv2.COLOR_HSV2BGR)}
    return {PIN_IMAGE_OUT: cv2.cvtColor(img, cv2.COLOR_BGR2HSV)}
