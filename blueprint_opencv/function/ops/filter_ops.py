# -*- coding: utf-8 -*-
"""滤波类节点 op 实现：gaussian_blur / median_blur / bilateral。

ksize 的奇数约束由 param_schema（int(odd)，偶数自动 +1）保证，
本模块直接使用校验后的 props。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image


def op_gaussian_blur(inputs: Dict[str, np.ndarray],
                     props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """高斯模糊；sigma_x 为 0 时由 ksize 自动推导。"""
    img = require_input_image(inputs)
    ksize = int(require_prop(props, "ksize"))
    sigma_x = float(require_prop(props, "sigma_x"))
    result = cv2.GaussianBlur(img, (ksize, ksize), sigmaX=sigma_x)
    return {PIN_IMAGE_OUT: result}


def op_median_blur(inputs: Dict[str, np.ndarray],
                   props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """中值模糊（ksize ≥ 3 且为奇数）。"""
    img = require_input_image(inputs)
    ksize = int(require_prop(props, "ksize"))
    return {PIN_IMAGE_OUT: cv2.medianBlur(img, ksize)}


def op_bilateral(inputs: Dict[str, np.ndarray],
                 props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """双边滤波（保边平滑）。"""
    img = require_input_image(inputs)
    diameter = int(require_prop(props, "d"))
    sigma_color = float(require_prop(props, "sigma_color"))
    sigma_space = float(require_prop(props, "sigma_space"))
    result = cv2.bilateralFilter(img, diameter, sigma_color, sigma_space)
    return {PIN_IMAGE_OUT: result}
