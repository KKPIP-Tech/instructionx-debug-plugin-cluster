# -*- coding: utf-8 -*-
"""输入类节点 op 实现：load_image / generate_noise / solid_color。

本模块同时定义 noise_type 等 choice 参数的取值常量，作为节点 schema
options 的唯一来源（node_catalog 从这里引用，避免魔法字符串）。
"""

import os
from typing import Any, Dict

import cv2
import numpy as np

from ..constants import NodeExecutionError, PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import hex_to_bgr, image_size

# noise_type 可选值（schema options 唯一来源）
NOISE_GAUSSIAN = "gaussian"
NOISE_UNIFORM = "uniform"
NOISE_SALT_PEPPER = "salt_pepper"

# 高斯噪声参数（均值 / 标准差，SPEC §3.1）
_GAUSSIAN_MEAN = 128.0
_GAUSSIAN_SIGMA = 32.0
#: 均匀噪声上限（uint8 最大值 + 1，rng.integers 上界为开区间）
_UNIFORM_HIGH = 256
# 椒盐噪声参数：基底灰度与黑白点总占比（SPEC §3.1：5% 黑白点）
_SALT_PEPPER_BASE = 128
_SALT_PEPPER_RATIO = 0.05


def op_load_image(inputs: Dict[str, np.ndarray],
                  props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """从文件路径读取图片（BGR 三通道）。

    异常:
        NodeExecutionError: 路径为空 / 文件不存在 / 解码失败。
    """
    file_path = str(require_prop(props, "file_path")).strip()
    if not file_path:
        raise NodeExecutionError("未设置图片路径，请在属性面板选择图片文件")
    if not os.path.exists(file_path):
        raise NodeExecutionError(f"图片文件不存在: {file_path}")
    img = cv2.imread(file_path, cv2.IMREAD_COLOR)
    if img is None:
        raise NodeExecutionError(f"图片解码失败（文件损坏或格式不支持）: {file_path}")
    return {PIN_IMAGE_OUT: img}


def op_generate_noise(inputs: Dict[str, np.ndarray],
                      props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """按类型生成 H×W×3 uint8 噪声图（高斯 / 均匀 / 椒盐）。"""
    width, height = image_size(props, "width", "height")
    noise_type = str(require_prop(props, "noise_type"))
    rng = np.random.default_rng()
    shape = (height, width, 3)
    if noise_type == NOISE_GAUSSIAN:
        data = rng.normal(_GAUSSIAN_MEAN, _GAUSSIAN_SIGMA, shape)
        img = np.clip(data, 0, 255).astype(np.uint8)
    elif noise_type == NOISE_UNIFORM:
        img = rng.integers(0, _UNIFORM_HIGH, shape, dtype=np.uint8)
    else:
        img = _salt_pepper(rng, height, width)
    return {PIN_IMAGE_OUT: img}


def _salt_pepper(rng: np.random.Generator, height: int,
                 width: int) -> np.ndarray:
    """生成椒盐噪声：中灰基底 + 各半的黑点 / 白点。"""
    img = np.full((height, width, 3), _SALT_PEPPER_BASE, dtype=np.uint8)
    rand = rng.random((height, width))
    half = _SALT_PEPPER_RATIO / 2
    img[rand < half] = 0
    img[(rand >= half) & (rand < _SALT_PEPPER_RATIO)] = 255
    return img


def op_solid_color(inputs: Dict[str, np.ndarray],
                   props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """生成 H×W×3 纯色图（color 为 #RRGGBB，非法时由 schema/转换报错）。"""
    width, height = image_size(props, "width", "height")
    bgr = hex_to_bgr(str(require_prop(props, "color")))
    return {PIN_IMAGE_OUT: np.full((height, width, 3), bgr, dtype=np.uint8)}
