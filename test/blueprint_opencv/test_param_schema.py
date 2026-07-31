# -*- coding: utf-8 -*-
"""param_schema.resolve_props / require_prop 的单元测试。

覆盖范围：

- 默认值合并：空 props 按 schema default 补齐；
- 类型转换：字符串数字转 int / float，None 转空字符串；
- 奇数修正：int(odd) 偶数输入自动 +1；
- 范围校验：越界抛中文错误（下限 / 上限）；
- choice / color 取值校验与中文错误文案；
- 未知参数类型、多余键忽略、require_prop 缺失键兜底。
"""

import pytest

from plugin.blueprint_opencv.function.constants import NodeExecutionError
from plugin.blueprint_opencv.function.node_catalog import defs_by_type
from plugin.blueprint_opencv.function.param_schema import (
    choice_param,
    color_param,
    file_path_param,
    float_param,
    int_param,
    require_prop,
    resolve_props,
    str_param,
)


@pytest.fixture()
def gaussian_schema():
    """gaussian_blur 节点的真实参数 schema（含 int(odd) 的 ksize）。"""
    return defs_by_type()["gaussian_blur"].param_schema


class TestDefaultMerge:
    """默认值合并：缺失键由 schema default 补齐。"""

    def test_empty_props_filled_with_defaults(self, gaussian_schema):
        """空 props 解析出 schema 声明的默认值（ksize=5, sigma_x=0.0）。"""
        resolved = resolve_props(gaussian_schema, {})
        assert resolved == {"ksize": 5, "sigma_x": 0.0}

    def test_extra_keys_ignored(self, gaussian_schema):
        """schema 未声明的多余键被忽略，不出现在结果中。"""
        resolved = resolve_props(gaussian_schema,
                                 {"ksize": 3, "unknown_key": 1})
        assert resolved == {"ksize": 3, "sigma_x": 0.0}
        assert "unknown_key" not in resolved


class TestTypeConversion:
    """类型转换：字符串数字、None、int→float 等。"""

    def test_int_from_string(self, gaussian_schema):
        """字符串 "7" 转为 int 7。"""
        resolved = resolve_props(gaussian_schema, {"ksize": "7"})
        assert resolved["ksize"] == 7
        assert isinstance(resolved["ksize"], int)

    def test_float_from_string(self, gaussian_schema):
        """字符串 "1.5" 转为 float 1.5。"""
        resolved = resolve_props(gaussian_schema, {"sigma_x": "1.5"})
        assert resolved["sigma_x"] == 1.5
        assert isinstance(resolved["sigma_x"], float)

    def test_str_none_becomes_empty(self):
        """str 参数收到 None 归一为空字符串。"""
        schema = [str_param("note", "备注")]
        assert resolve_props(schema, {"note": None}) == {"note": ""}

    def test_file_path_none_becomes_empty(self):
        """file_path 参数收到 None 归一为空字符串。"""
        schema = [file_path_param("file_path", "路径")]
        assert resolve_props(schema, {"file_path": None}) == {"file_path": ""}


class TestOddCorrection:
    """int(odd) 奇数修正：偶数自动 +1。"""

    def test_even_corrected_to_odd(self, gaussian_schema):
        """偶数 4 修正为 5。"""
        resolved = resolve_props(gaussian_schema, {"ksize": 4})
        assert resolved["ksize"] == 5

    def test_odd_unchanged(self, gaussian_schema):
        """奇数 9 保持不变。"""
        resolved = resolve_props(gaussian_schema, {"ksize": 9})
        assert resolved["ksize"] == 9

    def test_correction_then_range_check(self):
        """边界：先奇数修正再范围检查（偶数上限 10 修正为 11 后越界）。"""
        schema = [int_param("k", "核大小", 5, 1, 9, odd=True)]
        with pytest.raises(NodeExecutionError, match="大于上限 9"):
            resolve_props(schema, {"k": 10})
        resolved = resolve_props(schema, {"k": 8})
        assert resolved["k"] == 9


class TestRangeValidation:
    """数值范围校验（中文错误文案）。"""

    def test_below_min(self, gaussian_schema):
        """低于下限报「小于下限」且包含参数 label。

        用 -1 而非 0：int(odd) 会先对偶数做 +1 修正（0→1 恰好合法），
        奇数 -1 不触发修正、直接命中下限检查。
        """
        with pytest.raises(NodeExecutionError,
                           match="参数「核大小」小于下限 1"):
            resolve_props(gaussian_schema, {"ksize": -1})

    def test_above_max(self, gaussian_schema):
        """高于上限报「大于上限」。"""
        with pytest.raises(NodeExecutionError,
                           match="参数「Sigma X」大于上限 50"):
            resolve_props(gaussian_schema, {"sigma_x": 99.0})

    def test_boundary_values_accepted(self):
        """边界：恰好等于上下限时合法。"""
        schema = [int_param("v", "取值", 5, 1, 10)]
        assert resolve_props(schema, {"v": 1}) == {"v": 1}
        assert resolve_props(schema, {"v": 10}) == {"v": 10}


class TestValueValidation:
    """int / float / choice / color 的取值校验与中文错误。"""

    def test_invalid_int(self, gaussian_schema):
        """非数字字符串报「不是有效整数」。"""
        with pytest.raises(NodeExecutionError,
                           match="参数「核大小」不是有效整数"):
            resolve_props(gaussian_schema, {"ksize": "abc"})

    def test_invalid_float(self, gaussian_schema):
        """非数字字符串报「不是有效数值」。"""
        with pytest.raises(NodeExecutionError,
                           match="参数「Sigma X」不是有效数值"):
            resolve_props(gaussian_schema, {"sigma_x": "abc"})

    def test_invalid_choice(self):
        """choice 取值不在 options 内报「取值非法」并列出可选项。"""
        schema = [choice_param("direction", "方向", "horizontal",
                               ["horizontal", "vertical"])]
        with pytest.raises(NodeExecutionError,
                           match="参数「方向」取值非法: diagonal"):
            resolve_props(schema, {"direction": "diagonal"})

    @pytest.mark.parametrize("color", ["#FF0080", "#abcdef", "#ABCDEF"])
    def test_valid_color(self, color):
        """合法 #RRGGBB（含大小写 hex）原样通过。"""
        schema = [color_param("color", "颜色", "#000000")]
        assert resolve_props(schema, {"color": color}) == {"color": color}

    @pytest.mark.parametrize("bad", ["#12345", "FF0080", "#GGGGGG", ""])
    def test_invalid_color(self, bad):
        """非法颜色报「颜色格式非法」中文错误。"""
        schema = [color_param("color", "颜色", "#000000")]
        with pytest.raises(NodeExecutionError,
                           match="参数「颜色」颜色格式非法"):
            resolve_props(schema, {"color": bad})


class TestFallbacks:
    """未知类型与 require_prop 兜底。"""

    def test_unknown_param_type(self):
        """schema 声明未知 type 报「未知参数类型」。"""
        schema = [{"key": "x", "label": "X", "type": "bool", "default": True}]
        with pytest.raises(NodeExecutionError, match="未知参数类型: bool"):
            resolve_props(schema, {})

    def test_require_prop_missing(self):
        """require_prop 缺失键报「缺少参数」。"""
        with pytest.raises(NodeExecutionError, match="缺少参数: ksize"):
            require_prop({}, "ksize")

    def test_require_prop_present(self):
        """require_prop 命中时原样返回值（含假值 0）。"""
        assert require_prop({"k": 0}, "k") == 0


class TestRealCatalogSchemas:
    """真实节点目录 schema 的端到端默认值解析（抽查代表性节点）。"""

    def test_solid_color_defaults(self):
        """solid_color 默认 640×480、颜色 #3B82F6。"""
        schema = defs_by_type()["solid_color"].param_schema
        resolved = resolve_props(schema, {})
        assert resolved == {"width": 640, "height": 480,
                            "color": "#3B82F6"}

    def test_morphology_defaults(self):
        """morphology 默认 open / 核 3 / 迭代 1 / 矩形结构元。"""
        schema = defs_by_type()["morphology"].param_schema
        resolved = resolve_props(schema, {})
        assert resolved == {"op": "open", "ksize": 3, "iterations": 1,
                            "shape": "rect"}

    def test_adaptive_block_size_odd_correction(self):
        """adaptive_threshold 的 block_size 偶数自动 +1。"""
        schema = defs_by_type()["adaptive_threshold"].param_schema
        resolved = resolve_props(schema, {"block_size": 10})
        assert resolved["block_size"] == 11
