# -*- coding: utf-8 -*-
"""function/ops 全部 20 个节点 op 的单元测试。

覆盖范围：

- 正常路径：20 个 op 各自由小尺寸（32×32）测试图驱动，校验输出
  shape / dtype / 像素语义（翻转、旋转、反色、亮度等做像素级断言）；
- 灰度适配：threshold / adaptive_threshold 收到三通道图自动转灰度，
  grayscale 对单通道输入透传；
- 异常路径：输入未连接（全处理类 op 参数化）、非法图像数据、
  canny low > high、空路径 / 不存在文件 / 解码失败、非法颜色值、
  未知形态学操作、保存路径不可写。
"""

import cv2
import numpy as np
import pytest

from plugin.blueprint_opencv.function.constants import (
    NodeExecutionError,
    PIN_IMAGE_IN,
    PIN_IMAGE_OUT,
)
from plugin.blueprint_opencv.function import ops

#: 输入引脚缺失时的中文错误关键字
_UNCONNECTED_HINT = "输入未连接"

#: 各处理类 op 的最小合法 props（供「输入未连接」参数化用例）
_MINIMAL_PROPS = {
    "op_grayscale": {},
    "op_invert": {},
    "op_resize": {"scale_mode": "scale", "interpolation": "linear",
                  "scale": 1.0},
    "op_flip": {"direction": "horizontal"},
    "op_rotate": {"angle": "90_cw"},
    "op_gaussian_blur": {"ksize": 3, "sigma_x": 0.0},
    "op_median_blur": {"ksize": 3},
    "op_bilateral": {"d": 5, "sigma_color": 50.0, "sigma_space": 50.0},
    "op_threshold": {"thresh": 127, "max_value": 255, "thresh_type": "binary"},
    "op_adaptive_threshold": {"max_value": 255, "method": "mean",
                              "thresh_type": "binary", "block_size": 3,
                              "c": 2},
    "op_canny": {"low": 50, "high": 150},
    "op_morphology": {"op": "open", "ksize": 3, "iterations": 1,
                      "shape": "rect"},
    "op_brightness_contrast": {"alpha": 1.0, "beta": 0},
    "op_sharpen": {"strength": 1.0},
    "op_hsv_convert": {"direction": "to_hsv"},
    "op_preview": {},
    "op_save_image": {"file_path": "dummy.png"},
}


def _output(result: dict) -> np.ndarray:
    """取 op 返回 dict 中的图像输出。"""
    return result[PIN_IMAGE_OUT]


# ---------------------------------------------------------------------------
# 输入类 op
# ---------------------------------------------------------------------------

class TestLoadImage:
    """op_load_image：文件读取与中文错误路径。"""

    def test_load_ok(self, tmp_path, color_image):
        """正常路径：cv2.imwrite 写出的 PNG 能原样读回（BGR 三通道）。"""
        file_path = str(tmp_path / "in.png")
        assert cv2.imwrite(file_path, color_image)
        result = ops.op_load_image({}, {"file_path": file_path})
        img = _output(result)
        assert img.shape == color_image.shape
        assert img.dtype == np.uint8
        assert np.array_equal(img, color_image)

    def test_empty_path(self):
        """异常路径：空路径报「未设置图片路径」。"""
        with pytest.raises(NodeExecutionError, match="未设置图片路径"):
            ops.op_load_image({}, {"file_path": "   "})

    def test_missing_file(self, tmp_path):
        """异常路径：文件不存在报「图片文件不存在」。"""
        with pytest.raises(NodeExecutionError, match="图片文件不存在"):
            ops.op_load_image({}, {"file_path": str(tmp_path / "none.png")})

    def test_decode_failure(self, tmp_path):
        """异常路径：文件存在但不是有效图像，报「图片解码失败」。"""
        bad = tmp_path / "bad.png"
        bad.write_bytes(b"this is not an image")
        with pytest.raises(NodeExecutionError, match="图片解码失败"):
            ops.op_load_image({}, {"file_path": str(bad)})


class TestGenerateNoise:
    """op_generate_noise：三种噪声类型的形状 /  dtype / 取值域。"""

    @pytest.mark.parametrize("noise_type",
                             ["gaussian", "uniform", "salt_pepper"])
    def test_shape_and_dtype(self, noise_type):
        """正常路径：三种噪声都产出 H×W×3 uint8 图。"""
        props = {"width": 24, "height": 16, "noise_type": noise_type}
        img = _output(ops.op_generate_noise({}, props))
        assert img.shape == (16, 24, 3)
        assert img.dtype == np.uint8

    def test_salt_pepper_values(self):
        """椒盐噪声像素只允许 0 / 128 / 255 三档取值。"""
        props = {"width": 64, "height": 64, "noise_type": "salt_pepper"}
        img = _output(ops.op_generate_noise({}, props))
        assert set(np.unique(img).tolist()) <= {0, 128, 255}

    def test_unknown_type_falls_back_salt_pepper(self):
        """边界：未识别的 noise_type 走 else 分支（椒盐），仍产出合法图。"""
        props = {"width": 8, "height": 8, "noise_type": "unknown"}
        img = _output(ops.op_generate_noise({}, props))
        assert img.shape == (8, 8, 3)


class TestSolidColor:
    """op_solid_color：纯色生成与颜色格式校验。"""

    def test_pixel_value(self):
        """正常路径：#FF0000 生成纯红图（BGR = (0, 0, 255)）。"""
        props = {"width": 10, "height": 6, "color": "#FF0000"}
        img = _output(ops.op_solid_color({}, props))
        assert img.shape == (6, 10, 3)
        assert (img[0, 0] == [0, 0, 255]).all()
        assert (img == np.array([0, 0, 255], dtype=np.uint8)).all()

    @pytest.mark.parametrize("bad_color", ["red", "#12345", "#GGGGGG",
                                           "#1234567", ""])
    def test_invalid_color(self, bad_color):
        """异常路径：非法颜色格式报中文错误（应为 #RRGGBB）。"""
        props = {"width": 4, "height": 4, "color": bad_color}
        with pytest.raises(NodeExecutionError, match="颜色格式非法"):
            ops.op_solid_color({}, props)


# ---------------------------------------------------------------------------
# 基础类 op
# ---------------------------------------------------------------------------

class TestGrayscale:
    """op_grayscale：彩色转灰度与单通道透传。"""

    def test_color_to_gray(self, color_image):
        """三通道输入输出单通道灰度图（shape 一致、ndim 变 2）。"""
        img = _output(ops.op_grayscale({PIN_IMAGE_IN: color_image}, {}))
        assert img.ndim == 2
        assert img.shape == color_image.shape[:2]

    def test_gray_passthrough(self, gray_image):
        """已是单通道则原样透传（灰度适配，不报错）。"""
        img = _output(ops.op_grayscale({PIN_IMAGE_IN: gray_image}, {}))
        assert np.array_equal(img, gray_image)


class TestInvert:
    """op_invert：按位取反。"""

    def test_pixel_inverted(self, color_image):
        """像素级断言：输出 == 255 - 输入。"""
        img = _output(ops.op_invert({PIN_IMAGE_IN: color_image}, {}))
        expected = 255 - color_image.astype(np.int32)
        assert np.array_equal(img.astype(np.int32), expected)


class TestResize:
    """op_resize：scale / fixed 两种模式。"""

    def test_scale_mode(self, color_image):
        """scale 模式：0.5 倍率输出尺寸减半。"""
        props = {"scale_mode": "scale", "scale": 0.5,
                 "interpolation": "linear"}
        img = _output(ops.op_resize({PIN_IMAGE_IN: color_image}, props))
        assert img.shape == (16, 16, 3)

    def test_fixed_mode(self, color_image):
        """fixed 模式：输出尺寸等于目标宽高（宽 10 高 12）。"""
        props = {"scale_mode": "fixed", "width": 10, "height": 12,
                 "interpolation": "nearest"}
        img = _output(ops.op_resize({PIN_IMAGE_IN: color_image}, props))
        assert img.shape == (12, 10, 3)


class TestFlip:
    """op_flip：三个方向的像素级断言。"""

    def test_horizontal(self, color_image):
        """水平翻转：out[y, 0] == in[y, w-1]。"""
        props = {"direction": "horizontal"}
        img = _output(ops.op_flip({PIN_IMAGE_IN: color_image}, props))
        assert np.array_equal(img[:, 0], color_image[:, -1])

    def test_vertical(self, color_image):
        """垂直翻转：out[0, x] == in[h-1, x]。"""
        props = {"direction": "vertical"}
        img = _output(ops.op_flip({PIN_IMAGE_IN: color_image}, props))
        assert np.array_equal(img[0, :], color_image[-1, :])

    def test_both(self, color_image):
        """双向翻转：out[0, 0] == in[h-1, w-1]。"""
        props = {"direction": "both"}
        img = _output(ops.op_flip({PIN_IMAGE_IN: color_image}, props))
        assert np.array_equal(img[0, 0], color_image[-1, -1])


class TestRotate:
    """op_rotate：90° / 180° / 270° 的形状与像素断言。"""

    def test_rotate_90_cw(self):
        """90° 顺时针：非方阵宽高互换，out[0,0] == in[h-1,0]。"""
        src = np.arange(20 * 40 * 3, dtype=np.uint8).reshape(20, 40, 3)
        img = _output(ops.op_rotate({PIN_IMAGE_IN: src}, {"angle": "90_cw"}))
        assert img.shape == (40, 20, 3)
        assert np.array_equal(img[0, 0], src[-1, 0])

    def test_rotate_180(self):
        """180°：shape 不变，out[0,0] == in[h-1,w-1]。"""
        src = np.arange(20 * 40 * 3, dtype=np.uint8).reshape(20, 40, 3)
        img = _output(ops.op_rotate({PIN_IMAGE_IN: src}, {"angle": "180"}))
        assert img.shape == src.shape
        assert np.array_equal(img[0, 0], src[-1, -1])

    def test_rotate_90_ccw(self):
        """90° 逆时针：宽高互换，out[0,0] == in[0,w-1]。"""
        src = np.arange(20 * 40 * 3, dtype=np.uint8).reshape(20, 40, 3)
        img = _output(ops.op_rotate({PIN_IMAGE_IN: src}, {"angle": "90_ccw"}))
        assert img.shape == (40, 20, 3)
        assert np.array_equal(img[0, 0], src[0, -1])


# ---------------------------------------------------------------------------
# 滤波类 op
# ---------------------------------------------------------------------------

class TestFilters:
    """gaussian_blur / median_blur / bilateral 正常路径。"""

    def test_gaussian_blur(self, color_image):
        """高斯模糊：shape/dtype 不变，且模糊后与原图不同。"""
        props = {"ksize": 5, "sigma_x": 0.0}
        img = _output(ops.op_gaussian_blur({PIN_IMAGE_IN: color_image}, props))
        assert img.shape == color_image.shape
        assert img.dtype == np.uint8
        assert not np.array_equal(img, color_image)

    def test_median_blur_denoises(self):
        """中值模糊：椒盐噪点（128 基底）滤波后大部分像素回到 128。"""
        rng = np.random.default_rng(7)
        img = np.full((32, 32), 128, dtype=np.uint8)
        noise = rng.random((32, 32))
        img[noise < 0.05] = 0
        img[noise > 0.95] = 255
        result = _output(ops.op_median_blur({PIN_IMAGE_IN: img}, {"ksize": 3}))
        assert (result == 128).mean() > 0.9

    def test_bilateral(self, color_image):
        """双边滤波：shape/dtype 不变。"""
        props = {"d": 5, "sigma_color": 50.0, "sigma_space": 50.0}
        img = _output(ops.op_bilateral({PIN_IMAGE_IN: color_image}, props))
        assert img.shape == color_image.shape
        assert img.dtype == np.uint8


# ---------------------------------------------------------------------------
# 阈值与边缘类 op
# ---------------------------------------------------------------------------

class TestThresholdOps:
    """threshold / adaptive_threshold / canny 正常与异常路径。"""

    def test_threshold_binary_on_color(self, color_image):
        """固定阈值：三通道输入自动转灰度，输出单通道二值图。"""
        props = {"thresh": 127, "max_value": 255, "thresh_type": "binary"}
        img = _output(ops.op_threshold({PIN_IMAGE_IN: color_image}, props))
        assert img.ndim == 2
        assert set(np.unique(img).tolist()) <= {0, 255}

    @pytest.mark.parametrize("thresh_type",
                             ["binary", "binary_inv", "trunc", "tozero",
                              "tozero_inv"])
    def test_threshold_all_types(self, gray_image, thresh_type):
        """五种阈值类型都能对灰度图正常执行。"""
        props = {"thresh": 127, "max_value": 200,
                 "thresh_type": thresh_type}
        img = _output(ops.op_threshold({PIN_IMAGE_IN: gray_image}, props))
        assert img.shape == gray_image.shape

    @pytest.mark.parametrize("method", ["mean", "gaussian"])
    def test_adaptive_threshold(self, gray_image, method):
        """自适应阈值：两种方法输出单通道二值图（自动转灰度路径由
        三通道输入用例覆盖）。"""
        props = {"max_value": 255, "method": method,
                 "thresh_type": "binary", "block_size": 5, "c": 2}
        img = _output(ops.op_adaptive_threshold(
            {PIN_IMAGE_IN: gray_image}, props))
        assert img.ndim == 2
        assert set(np.unique(img).tolist()) <= {0, 255}

    def test_adaptive_threshold_on_color(self, color_image):
        """自适应阈值：三通道输入自动转灰度（灰度适配路径）。"""
        props = {"max_value": 255, "method": "mean",
                 "thresh_type": "binary", "block_size": 3, "c": 0}
        img = _output(ops.op_adaptive_threshold(
            {PIN_IMAGE_IN: color_image}, props))
        assert img.ndim == 2

    def test_canny_ok(self, gray_image):
        """Canny：输出同尺寸单通道 uint8 边缘图。"""
        props = {"low": 50, "high": 150}
        img = _output(ops.op_canny({PIN_IMAGE_IN: gray_image}, props))
        assert img.shape == gray_image.shape
        assert img.dtype == np.uint8

    def test_canny_low_greater_than_high(self, gray_image):
        """异常路径：low > high 报中文错误并包含两个阈值。"""
        props = {"low": 200, "high": 100}
        with pytest.raises(NodeExecutionError, match="低阈值 200 不能大于高阈值 100"):
            ops.op_canny({PIN_IMAGE_IN: gray_image}, props)


# ---------------------------------------------------------------------------
# 形态学 op
# ---------------------------------------------------------------------------

class TestMorphology:
    """op_morphology：七种操作分派与未知操作错误。"""

    @pytest.mark.parametrize("morph_op",
                             ["erode", "dilate", "open", "close",
                              "gradient", "tophat", "blackhat"])
    def test_all_ops(self, gray_image, morph_op):
        """七种形态学操作都能执行且 shape 不变。"""
        props = {"op": morph_op, "ksize": 3, "iterations": 1,
                 "shape": "rect"}
        img = _output(ops.op_morphology({PIN_IMAGE_IN: gray_image}, props))
        assert img.shape == gray_image.shape

    @pytest.mark.parametrize("shape", ["rect", "ellipse", "cross"])
    def test_all_shapes(self, gray_image, shape):
        """三种结构元形状都能执行。"""
        props = {"op": "dilate", "ksize": 3, "iterations": 2,
                 "shape": shape}
        img = _output(ops.op_morphology({PIN_IMAGE_IN: gray_image}, props))
        assert img.shape == gray_image.shape

    def test_erode_dilate_semantics(self):
        """像素语义：亮块腐蚀后缩小、膨胀后扩大。"""
        img = np.zeros((32, 32), dtype=np.uint8)
        img[12:20, 12:20] = 255
        base = {"ksize": 3, "iterations": 1, "shape": "rect"}
        eroded = _output(ops.op_morphology(
            {PIN_IMAGE_IN: img}, {**base, "op": "erode"}))
        dilated = _output(ops.op_morphology(
            {PIN_IMAGE_IN: img}, {**base, "op": "dilate"}))
        assert (eroded > 0).sum() < (img > 0).sum()
        assert (dilated > 0).sum() > (img > 0).sum()

    def test_unknown_op(self, gray_image):
        """异常路径：未在映射表中的 op 报「未知形态学操作」。"""
        props = {"op": "explode", "ksize": 3, "iterations": 1,
                 "shape": "rect"}
        with pytest.raises(NodeExecutionError, match="未知形态学操作"):
            ops.op_morphology({PIN_IMAGE_IN: gray_image}, props)


# ---------------------------------------------------------------------------
# 调整类 op
# ---------------------------------------------------------------------------

class TestAdjustOps:
    """brightness_contrast / sharpen / hsv_convert。"""

    def test_brightness_contrast_beta(self):
        """亮度调整：alpha=1、beta=+10 时像素整体 +10（未饱和区）。"""
        src = np.full((8, 8, 3), 100, dtype=np.uint8)
        props = {"alpha": 1.0, "beta": 10}
        img = _output(ops.op_brightness_contrast({PIN_IMAGE_IN: src}, props))
        assert (img == 110).all()

    def test_brightness_contrast_alpha(self):
        """对比度调整：alpha=2 时像素翻倍（未饱和区）。"""
        src = np.full((8, 8, 3), 50, dtype=np.uint8)
        props = {"alpha": 2.0, "beta": 0}
        img = _output(ops.op_brightness_contrast({PIN_IMAGE_IN: src}, props))
        assert (img == 100).all()

    def test_sharpen(self, color_image):
        """锐化：shape/dtype 不变。"""
        img = _output(ops.op_sharpen({PIN_IMAGE_IN: color_image},
                                     {"strength": 1.0}))
        assert img.shape == color_image.shape
        assert img.dtype == np.uint8

    def test_hsv_round_trip(self, color_image):
        """HSV 往返：to_hsv → from_hsv 后与原图近似。

        cv2 的 BGR↔HSV 转换为 8bit 量化（色相 0–179），往返存在少量
        量化误差：绝大多数像素误差 ≤2，个别极端色允许到 8。
        """
        hsv = _output(ops.op_hsv_convert({PIN_IMAGE_IN: color_image},
                                         {"direction": "to_hsv"}))
        assert hsv.shape == color_image.shape
        back = _output(ops.op_hsv_convert({PIN_IMAGE_IN: hsv},
                                          {"direction": "from_hsv"}))
        diff = np.abs(back.astype(np.int32) - color_image.astype(np.int32))
        assert float(diff.mean()) <= 1.0
        assert int(diff.max()) <= 8

    def test_hsv_accepts_gray(self, gray_image):
        """灰度适配：单通道输入先转 BGR 再转 HSV，输出三通道。"""
        img = _output(ops.op_hsv_convert({PIN_IMAGE_IN: gray_image},
                                         {"direction": "to_hsv"}))
        assert img.ndim == 3 and img.shape[2] == 3


# ---------------------------------------------------------------------------
# 输出类 op
# ---------------------------------------------------------------------------

class TestOutputOps:
    """preview 透传与 save_image 写盘。"""

    def test_preview_passthrough(self, color_image):
        """preview：原样透传输入图像（同一对象 / 内容一致）。"""
        img = _output(ops.op_preview({PIN_IMAGE_IN: color_image}, {}))
        assert np.array_equal(img, color_image)

    def test_save_image_ok(self, tmp_path, color_image):
        """正常路径：写出 PNG 文件可读回，op 返回空 dict（无图像输出）。"""
        file_path = str(tmp_path / "out.png")
        result = ops.op_save_image({PIN_IMAGE_IN: color_image},
                                   {"file_path": file_path})
        assert result == {}
        loaded = cv2.imread(file_path, cv2.IMREAD_COLOR)
        assert loaded is not None
        assert np.array_equal(loaded, color_image)

    def test_save_image_empty_path(self, color_image):
        """异常路径：空保存路径报「未设置保存路径」。"""
        with pytest.raises(NodeExecutionError, match="未设置保存路径"):
            ops.op_save_image({PIN_IMAGE_IN: color_image}, {"file_path": ""})

    def test_save_image_unwritable(self, tmp_path, color_image):
        """异常路径：目录不存在导致写入失败，报「图片写入失败」。"""
        bad_path = str(tmp_path / "no_such_dir" / "out.png")
        with pytest.raises(NodeExecutionError, match="图片写入失败"):
            ops.op_save_image({PIN_IMAGE_IN: color_image},
                              {"file_path": bad_path})


# ---------------------------------------------------------------------------
# 通用防御性校验（require_input_image）
# ---------------------------------------------------------------------------

class TestRequireInput:
    """输入未连接 / 数据非法的统一中文错误（覆盖全部处理类 op）。"""

    @pytest.mark.parametrize("op_name", sorted(_MINIMAL_PROPS))
    def test_unconnected_input(self, op_name):
        """所有依赖 image_in 的 op 在输入未连接时报「输入未连接」。"""
        op = getattr(ops, op_name)
        with pytest.raises(NodeExecutionError, match=_UNCONNECTED_HINT):
            op({}, dict(_MINIMAL_PROPS[op_name]))

    def test_invalid_image_data(self):
        """空数组输入报「输入图像数据非法」。"""
        empty = np.array([], dtype=np.uint8)
        with pytest.raises(NodeExecutionError, match="输入图像数据非法"):
            ops.op_grayscale({PIN_IMAGE_IN: empty}, {})
