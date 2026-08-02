# -*- coding: utf-8 -*-
"""ops 包 - 汇总导出全部 20 个节点 op 函数。

op 统一签名：``op(inputs: Dict[str, np.ndarray], props: Dict[str, Any])
-> Dict[str, np.ndarray]``，纯函数、不触碰 Qt。
"""

from .adjust_ops import (op_brightness_contrast, op_hsv_convert, op_sharpen)
from .basic_ops import (op_flip, op_grayscale, op_invert, op_resize,
                        op_rotate)
from .filter_ops import op_bilateral, op_gaussian_blur, op_median_blur
from .input_ops import op_generate_noise, op_load_image, op_solid_color
from .morphology_ops import op_morphology
from .output_ops import op_preview, op_save_image
from .threshold_ops import (op_adaptive_threshold, op_canny, op_threshold)

__all__ = [
    # 输入
    "op_load_image",
    "op_generate_noise",
    "op_solid_color",
    # 基础
    "op_grayscale",
    "op_invert",
    "op_resize",
    "op_flip",
    "op_rotate",
    # 滤波
    "op_gaussian_blur",
    "op_median_blur",
    "op_bilateral",
    # 阈值与边缘
    "op_threshold",
    "op_adaptive_threshold",
    "op_canny",
    # 形态学
    "op_morphology",
    # 调整
    "op_brightness_contrast",
    "op_sharpen",
    "op_hsv_convert",
    # 输出
    "op_preview",
    "op_save_image",
]
