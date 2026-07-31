# -*- coding: utf-8 -*-
"""形态学节点 op 实现：morphology（腐蚀/膨胀/开/闭/梯度/顶帽/黑帽）。

op 与 shape 的 choice 取值常量定义在本模块，作为节点 schema
options 的唯一来源。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import NodeExecutionError, PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image

# op 可选值
MORPH_ERODE = "erode"
MORPH_DILATE = "dilate"
MORPH_OPEN = "open"
MORPH_CLOSE = "close"
MORPH_GRADIENT = "gradient"
MORPH_TOPHAT = "tophat"
MORPH_BLACKHAT = "blackhat"

#: morphologyEx 类操作 → cv2 常量映射（erode/dilate 走专用 API，不在此列）
_MORPH_EX_MAP = {
    MORPH_OPEN: cv2.MORPH_OPEN,
    MORPH_CLOSE: cv2.MORPH_CLOSE,
    MORPH_GRADIENT: cv2.MORPH_GRADIENT,
    MORPH_TOPHAT: cv2.MORPH_TOPHAT,
    MORPH_BLACKHAT: cv2.MORPH_BLACKHAT,
}

# shape 可选值
SHAPE_RECT = "rect"
SHAPE_ELLIPSE = "ellipse"
SHAPE_CROSS = "cross"

#: shape → cv2 结构元形状常量映射
_SHAPE_MAP = {
    SHAPE_RECT: cv2.MORPH_RECT,
    SHAPE_ELLIPSE: cv2.MORPH_ELLIPSE,
    SHAPE_CROSS: cv2.MORPH_CROSS,
}


def op_morphology(inputs: Dict[str, np.ndarray],
                  props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """形态学操作：按 op 分派到 erode/dilate 或 morphologyEx。"""
    img = require_input_image(inputs)
    morph_op = str(require_prop(props, "op"))
    ksize = int(require_prop(props, "ksize"))
    iterations = int(require_prop(props, "iterations"))
    shape = _SHAPE_MAP[str(require_prop(props, "shape"))]
    kernel = cv2.getStructuringElement(shape, (ksize, ksize))
    result = _apply_morphology(img, morph_op, kernel, iterations)
    return {PIN_IMAGE_OUT: result}


def _apply_morphology(img: np.ndarray, morph_op: str,
                      kernel: np.ndarray, iterations: int) -> np.ndarray:
    """按操作类型分派执行（查表 + 卫语句，避免 if-elif 长链）。"""
    if morph_op == MORPH_ERODE:
        return cv2.erode(img, kernel, iterations=iterations)
    if morph_op == MORPH_DILATE:
        return cv2.dilate(img, kernel, iterations=iterations)
    ex_code = _MORPH_EX_MAP.get(morph_op)
    if ex_code is None:
        raise NodeExecutionError(f"未知形态学操作: {morph_op}")
    return cv2.morphologyEx(img, ex_code, kernel, iterations=iterations)
