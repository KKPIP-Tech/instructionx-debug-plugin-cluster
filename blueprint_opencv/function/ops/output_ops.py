# -*- coding: utf-8 -*-
"""输出类节点 op 实现：preview / save_image。

preview 只透传图像，PNG 编码与 on_preview 回调由执行引擎在求值
完成后触发（SPEC §4.2.4），本模块不做编码。
"""

from typing import Any, Dict

import cv2
import numpy as np

from ..constants import NodeExecutionError, PIN_IMAGE_OUT
from ..param_schema import require_prop
from ._common import require_input_image


def op_preview(inputs: Dict[str, np.ndarray],
               props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """预览：原样透传输入图像（引擎随后编码 PNG 字节上抛 UI）。"""
    return {PIN_IMAGE_OUT: require_input_image(inputs)}


def op_save_image(inputs: Dict[str, np.ndarray],
                  props: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """保存图片到文件路径；无图像输出（返回空 dict）。

    异常:
        NodeExecutionError: 路径为空 / 写入失败。
    """
    img = require_input_image(inputs)
    file_path = str(require_prop(props, "file_path")).strip()
    if not file_path:
        raise NodeExecutionError("未设置保存路径，请在属性面板选择保存位置")
    if not cv2.imwrite(file_path, img):
        raise NodeExecutionError(f"图片写入失败（路径不可写或格式不支持）: {file_path}")
    return {}
