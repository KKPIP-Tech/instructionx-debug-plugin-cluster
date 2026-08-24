# -*- coding: utf-8 -*-
"""节点类型注册目录：NODE_DEFINITIONS 注册表与查询入口（纯数据，无 Qt）。

本模块只做「定义」，不写 cv2 逻辑（op 引用自 ``ops/``），也不 import
InstructionX_UIKit —— function 层禁止依赖 Qt / UIKit。注册动作在
ui 层 ``ui/node_bootstrap.ensure_node_types_registered()``（幂等 +
同名异定义纠正，热重载安全）；执行引擎经 ``defs_by_type()`` 查表。

主路径::

    ui/node_bootstrap.py
        → ensure_node_types_registered()  读 NODE_DEFINITIONS 注册进 UIKit
    function/executor.py / pipeline_controller.py
        → defs_by_type()                  查 op / param_schema

注意：SPEC §1.5 曾约定本模块提供 ``register_all_node_types()`` /
``registration_payloads()``；因 function 层不得 import UIKit，注册动作
上移到 ui 层后注册载荷由 node_bootstrap 直接组装，两者均已移除。
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List

from . import ops
from .constants import (CATEGORY_ADJUST, CATEGORY_BASIC, CATEGORY_FILTER,
                        CATEGORY_INPUT, CATEGORY_MORPHOLOGY, CATEGORY_OUTPUT,
                        CATEGORY_THRESHOLD, PIN_DATA_TYPE_EXEC,
                        PIN_DATA_TYPE_IMAGE, PIN_EXEC_IN, PIN_EXEC_OUT,
                        PIN_IMAGE_IN, PIN_IMAGE_OUT)
from .param_schema import (choice_param, color_param, file_path_param,
                           float_param, int_param)


@dataclass(frozen=True)
class NodeDefinition:
    """节点类型定义（SPEC §3.8 契约，冻结 dataclass）。

    参数:
        type_name: 唯一类型名（register_node_type 的键）。
        title: 显示标题。
        category: 分类（决定右键菜单分组与 accent）。
        inputs / outputs: Blueprint 引脚定义 dict 列表
            （``{"id","name","data_type","multi"?}``）。
        param_schema: 参数 schema 列表（供属性面板与引擎校验）。
        op: ``ops/`` 中的 op 函数引用。
        description: 节点一句话说明（菜单提示）。
    """

    type_name: str
    title: str
    category: str
    inputs: List[dict]
    outputs: List[dict]
    param_schema: List[dict]
    op: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]
    description: str


# ---------------------------------------------------------------------------
# 引脚定义模板（SPEC §3.0 通用约定）
# ---------------------------------------------------------------------------

_PIN_EXEC_IN = {"id": PIN_EXEC_IN, "name": "执行", "data_type": PIN_DATA_TYPE_EXEC}
_PIN_EXEC_OUT = {"id": PIN_EXEC_OUT, "name": "执行", "data_type": PIN_DATA_TYPE_EXEC}
_PIN_IMAGE_IN = {"id": PIN_IMAGE_IN, "name": "图像", "data_type": PIN_DATA_TYPE_IMAGE}
_PIN_IMAGE_OUT = {"id": PIN_IMAGE_OUT, "name": "图像", "data_type": PIN_DATA_TYPE_IMAGE}


def _pins(*templates: dict) -> List[dict]:
    """按模板生成引脚 dict 列表（逐份拷贝，避免共享可变对象）。"""
    return [dict(t) for t in templates]


def _standard_inputs() -> List[dict]:
    """处理类节点标准输入：exec_in + image_in。"""
    return _pins(_PIN_EXEC_IN, _PIN_IMAGE_IN)


def _standard_outputs() -> List[dict]:
    """处理类节点标准输出：exec_out + image_out。"""
    return _pins(_PIN_EXEC_OUT, _PIN_IMAGE_OUT)


def _source_inputs() -> List[dict]:
    """输入类节点输入：仅 exec_in。"""
    return _pins(_PIN_EXEC_IN)


def _source_outputs() -> List[dict]:
    """输入类节点输出：exec_out + image_out。"""
    return _pins(_PIN_EXEC_OUT, _PIN_IMAGE_OUT)


# ---------------------------------------------------------------------------
# 参数 schema 片段（跨节点复用）
# ---------------------------------------------------------------------------

def _size_params(default_width: int, default_height: int) -> List[dict]:
    """宽高参数对（1–4096，SPEC §3 统一约束）。"""
    return [
        int_param("width", "宽度", default_width, 1, 4096),
        int_param("height", "高度", default_height, 1, 4096),
    ]


# ---------------------------------------------------------------------------
# 节点定义表（SPEC §3.1–§3.7，共 20 个）
# ---------------------------------------------------------------------------

NODE_DEFINITIONS: List[NodeDefinition] = [
    # ---- 输入（§3.1）----
    NodeDefinition(
        "load_image", "加载图片", CATEGORY_INPUT,
        _source_inputs(), _source_outputs(),
        [file_path_param("file_path", "图片路径")],
        ops.op_load_image,
        "从文件路径读取图片（BGR 三通道）",
    ),
    NodeDefinition(
        "generate_noise", "生成噪声", CATEGORY_INPUT,
        _source_inputs(), _source_outputs(),
        _size_params(640, 480) + [
            choice_param("noise_type", "噪声类型", ops.input_ops.NOISE_GAUSSIAN,
                         [ops.input_ops.NOISE_GAUSSIAN,
                          ops.input_ops.NOISE_UNIFORM,
                          ops.input_ops.NOISE_SALT_PEPPER]),
        ],
        ops.op_generate_noise,
        "生成高斯 / 均匀 / 椒盐噪声图",
    ),
    NodeDefinition(
        "solid_color", "纯色图像", CATEGORY_INPUT,
        _source_inputs(), _source_outputs(),
        _size_params(640, 480) + [
            color_param("color", "颜色", "#3B82F6"),
        ],
        ops.op_solid_color,
        "生成指定颜色的纯色图",
    ),
    # ---- 基础（§3.2）----
    NodeDefinition(
        "grayscale", "灰度化", CATEGORY_BASIC,
        _standard_inputs(), _standard_outputs(),
        [],
        ops.op_grayscale,
        "彩色图转单通道灰度图",
    ),
    NodeDefinition(
        "invert", "反色", CATEGORY_BASIC,
        _standard_inputs(), _standard_outputs(),
        [],
        ops.op_invert,
        "按位取反，生成负片效果",
    ),
    NodeDefinition(
        "resize", "缩放", CATEGORY_BASIC,
        _standard_inputs(), _standard_outputs(),
        [
            choice_param("scale_mode", "缩放模式", ops.basic_ops.SCALE_MODE_SCALE,
                         [ops.basic_ops.SCALE_MODE_FIXED,
                          ops.basic_ops.SCALE_MODE_SCALE]),
        ] + _size_params(640, 480) + [
            float_param("scale", "缩放倍率", 1.0, 0.01, 10.0),
            choice_param("interpolation", "插值方式", ops.basic_ops.INTERP_LINEAR,
                         [ops.basic_ops.INTERP_NEAREST,
                          ops.basic_ops.INTERP_LINEAR,
                          ops.basic_ops.INTERP_CUBIC,
                          ops.basic_ops.INTERP_AREA]),
        ],
        ops.op_resize,
        "按倍率或目标宽高缩放图像",
    ),
    NodeDefinition(
        "flip", "翻转", CATEGORY_BASIC,
        _standard_inputs(), _standard_outputs(),
        [
            choice_param("direction", "方向", ops.basic_ops.FLIP_HORIZONTAL,
                         [ops.basic_ops.FLIP_HORIZONTAL,
                          ops.basic_ops.FLIP_VERTICAL,
                          ops.basic_ops.FLIP_BOTH]),
        ],
        ops.op_flip,
        "水平 / 垂直 / 双向翻转图像",
    ),
    NodeDefinition(
        "rotate", "旋转", CATEGORY_BASIC,
        _standard_inputs(), _standard_outputs(),
        [
            choice_param("angle", "角度", ops.basic_ops.ROTATE_90_CW,
                         [ops.basic_ops.ROTATE_90_CW,
                          ops.basic_ops.ROTATE_180,
                          ops.basic_ops.ROTATE_90_CCW]),
        ],
        ops.op_rotate,
        "90° 顺时针 / 180° / 90° 逆时针旋转",
    ),
    # ---- 滤波（§3.3）----
    NodeDefinition(
        "gaussian_blur", "高斯模糊", CATEGORY_FILTER,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("ksize", "核大小", 5, 1, 99, odd=True),
            float_param("sigma_x", "Sigma X", 0.0, 0.0, 50.0),
        ],
        ops.op_gaussian_blur,
        "高斯加权平滑（sigma 为 0 时由核大小推导）",
    ),
    NodeDefinition(
        "median_blur", "中值模糊", CATEGORY_FILTER,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("ksize", "核大小", 5, 3, 99, odd=True),
        ],
        ops.op_median_blur,
        "中值滤波去噪（对椒盐噪声效果好）",
    ),
    NodeDefinition(
        "bilateral", "双边滤波", CATEGORY_FILTER,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("d", "邻域直径", 9, 1, 50),
            float_param("sigma_color", "颜色 Sigma", 75.0, 1.0, 300.0),
            float_param("sigma_space", "空间 Sigma", 75.0, 1.0, 300.0),
        ],
        ops.op_bilateral,
        "保边平滑滤波",
    ),
    # ---- 阈值与边缘（§3.4）----
    NodeDefinition(
        "threshold", "固定阈值", CATEGORY_THRESHOLD,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("thresh", "阈值", 127, 0, 255),
            int_param("max_value", "最大值", 255, 1, 255),
            choice_param("thresh_type", "阈值类型",
                         ops.threshold_ops.THRESH_BINARY,
                         [ops.threshold_ops.THRESH_BINARY,
                          ops.threshold_ops.THRESH_BINARY_INV,
                          ops.threshold_ops.THRESH_TRUNC,
                          ops.threshold_ops.THRESH_TOZERO,
                          ops.threshold_ops.THRESH_TOZERO_INV]),
        ],
        ops.op_threshold,
        "固定阈值二值化（自动转灰度）",
    ),
    NodeDefinition(
        "adaptive_threshold", "自适应阈值", CATEGORY_THRESHOLD,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("max_value", "最大值", 255, 1, 255),
            choice_param("method", "自适应方法",
                         ops.threshold_ops.ADAPTIVE_GAUSSIAN,
                         [ops.threshold_ops.ADAPTIVE_MEAN,
                          ops.threshold_ops.ADAPTIVE_GAUSSIAN]),
            choice_param("thresh_type", "阈值类型",
                         ops.threshold_ops.THRESH_BINARY,
                         [ops.threshold_ops.THRESH_BINARY,
                          ops.threshold_ops.THRESH_BINARY_INV]),
            int_param("block_size", "邻域块大小", 11, 3, 99, odd=True),
            int_param("c", "常数 C", 5, -50, 50),
        ],
        ops.op_adaptive_threshold,
        "按局部邻域自适应二值化（自动转灰度）",
    ),
    NodeDefinition(
        "canny", "Canny 边缘", CATEGORY_THRESHOLD,
        _standard_inputs(), _standard_outputs(),
        [
            int_param("low", "低阈值", 50, 0, 255),
            int_param("high", "高阈值", 150, 0, 255),
        ],
        ops.op_canny,
        "Canny 边缘检测",
    ),
    # ---- 形态学（§3.5）----
    NodeDefinition(
        "morphology", "形态学操作", CATEGORY_MORPHOLOGY,
        _standard_inputs(), _standard_outputs(),
        [
            choice_param("op", "操作", ops.morphology_ops.MORPH_OPEN,
                         [ops.morphology_ops.MORPH_ERODE,
                          ops.morphology_ops.MORPH_DILATE,
                          ops.morphology_ops.MORPH_OPEN,
                          ops.morphology_ops.MORPH_CLOSE,
                          ops.morphology_ops.MORPH_GRADIENT,
                          ops.morphology_ops.MORPH_TOPHAT,
                          ops.morphology_ops.MORPH_BLACKHAT]),
            int_param("ksize", "核大小", 3, 1, 31),
            int_param("iterations", "迭代次数", 1, 1, 10),
            choice_param("shape", "结构元形状", ops.morphology_ops.SHAPE_RECT,
                         [ops.morphology_ops.SHAPE_RECT,
                          ops.morphology_ops.SHAPE_ELLIPSE,
                          ops.morphology_ops.SHAPE_CROSS]),
        ],
        ops.op_morphology,
        "腐蚀 / 膨胀 / 开闭 / 梯度 / 顶帽 / 黑帽",
    ),
    # ---- 调整（§3.6）----
    NodeDefinition(
        "brightness_contrast", "亮度对比度", CATEGORY_ADJUST,
        _standard_inputs(), _standard_outputs(),
        [
            float_param("alpha", "对比度", 1.0, 0.1, 3.0),
            int_param("beta", "亮度", 0, -255, 255),
        ],
        ops.op_brightness_contrast,
        "线性调整亮度与对比度",
    ),
    NodeDefinition(
        "sharpen", "锐化", CATEGORY_ADJUST,
        _standard_inputs(), _standard_outputs(),
        [
            float_param("strength", "强度", 1.0, 0.0, 3.0),
        ],
        ops.op_sharpen,
        "反锐化掩模锐化",
    ),
    NodeDefinition(
        "hsv_convert", "HSV 转换", CATEGORY_ADJUST,
        _standard_inputs(), _standard_outputs(),
        [
            choice_param("direction", "方向", ops.adjust_ops.HSV_TO_HSV,
                         [ops.adjust_ops.HSV_TO_HSV,
                          ops.adjust_ops.HSV_FROM_HSV]),
        ],
        ops.op_hsv_convert,
        "BGR 与 HSV 色彩空间互转",
    ),
    # ---- 输出（§3.7）----
    NodeDefinition(
        "preview", "预览", CATEGORY_OUTPUT,
        _standard_inputs(), _standard_outputs(),
        [],
        ops.op_preview,
        "透传图像并把结果上抛到预览面板",
    ),
    NodeDefinition(
        "save_image", "保存图片", CATEGORY_OUTPUT,
        _standard_inputs(), _pins(_PIN_EXEC_OUT),
        [file_path_param("file_path", "保存路径")],
        ops.op_save_image,
        "把图像写入指定文件路径",
    ),
]


# ---------------------------------------------------------------------------
# 查询入口
# ---------------------------------------------------------------------------

def defs_by_type() -> Dict[str, NodeDefinition]:
    """返回 ``type_name -> NodeDefinition`` 映射（执行引擎查表用）。"""
    return {definition.type_name: definition for definition in NODE_DEFINITIONS}
