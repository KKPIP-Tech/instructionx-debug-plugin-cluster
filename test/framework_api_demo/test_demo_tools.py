# -*- coding: utf-8 -*-
"""demo_tools 演示工具测试。

覆盖 function/tools/demo_tools.py：
- calculate 的 AST 白名单求值：四则运算、括号优先级、一元正负、浮点；
- calculate 的拒绝路径：__import__/属性访问/函数调用/幂运算/字符串常量/语法错误/空表达式；
- get_current_time 的时间格式；
- DEMO_TOOL_DEFINITIONS 与 DEMO_TOOL_HANDLERS 的一致性。
"""

import re
from datetime import datetime

import pytest

from plugin.framework_api_demo.function.tools.demo_tools import (
    DEMO_TOOL_DEFINITIONS,
    DEMO_TOOL_HANDLERS,
    TIME_DISPLAY_FORMAT,
    TOOL_NAME_CALCULATE,
    TOOL_NAME_GET_CURRENT_TIME,
    calculate,
    get_current_time,
)

# 错误返回串的统一前缀（handler 约定：非法输入返回错误字符串而非抛出）
ERROR_PREFIX = "错误"


class TestCalculateArithmetic:
    """calculate 白名单内的正常求值路径"""

    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("1+2", "3"),
            ("1+2*3", "7"),          # 乘法优先级高于加法
            ("(1+2)*3", "9"),        # 括号改变优先级
            ("10/4", "2.5"),         # 真除法
            ("10-4-3", "3"),         # 左结合
            ("2*-3", "-6"),          # 二元乘一元负
            ("-5+3", "-2"),          # 一元负号
            ("+5", "5"),             # 一元正号
            ("--5", "5"),            # 双重否定
            ("1.5*2", "3.0"),        # 浮点运算
            ("((2+3)*(4-1))/5", "3.0"),  # 多层括号混合运算
        ],
    )
    def test_valid_expressions(self, expression, expected):
        """白名单内表达式应返回正确计算结果字符串"""
        assert calculate(expression) == expected

    def test_result_is_plain_number_string(self):
        """返回值为 str 且不含错误前缀"""
        result = calculate("6*7")
        assert isinstance(result, str)
        assert not result.startswith(ERROR_PREFIX)
        assert result == "42"


class TestCalculateRejection:
    """calculate 的拒绝路径：越白名单元素与语法错误返回错误字符串"""

    @pytest.mark.parametrize(
        "expression",
        [
            "__import__('os')",      # 函数调用（危险内建）
            "os.system('ls')",       # 属性访问 + 调用
            "abs(-1)",               # 普通函数调用同样拒绝
            "2**3",                  # 幂运算不在白名单
            "5%2",                   # 取余不在白名单
            "'abc'",                 # 字符串常量不是数值
            "[1,2][0]",              # 下标访问
            "x + 1",                 # 未定义变量名
        ],
    )
    def test_unsupported_elements_return_error(self, expression):
        """白名单外的 AST 元素应返回「不支持的表达式元素」错误串"""
        result = calculate(expression)
        assert result.startswith(ERROR_PREFIX)
        assert "不支持的表达式元素" in result

    @pytest.mark.parametrize(
        "expression",
        [
            "1 +",                   # 尾部缺操作数
            "(1+2",                  # 括号未闭合
            "",                      # 空表达式
            "1 2",                   # 非法 token 序列
        ],
    )
    def test_syntax_error_returns_error(self, expression):
        """语法错误应返回「表达式无法解析」错误串"""
        result = calculate(expression)
        assert result.startswith(ERROR_PREFIX)
        assert "无法解析" in result

    @pytest.mark.xfail(
        strict=True,
        reason="已知缺陷：calculate('1/0') 抛出 ZeroDivisionError 而非按约定返回错误字符串",
    )
    def test_division_by_zero_returns_error(self):
        """除零应按 handler 约定返回错误字符串（当前实现会抛 ZeroDivisionError）"""
        result = calculate("1/0")
        assert result.startswith(ERROR_PREFIX)


class TestGetCurrentTime:
    """get_current_time 格式校验"""

    def test_matches_display_format(self):
        """返回串应符合 %Y-%m-%d %H:%M:%S 格式且可被 strptime 解析"""
        result = get_current_time()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", result)
        parsed = datetime.strptime(result, TIME_DISPLAY_FORMAT)
        assert isinstance(parsed, datetime)


class TestToolDefinitions:
    """工具定义与 handler 映射的一致性"""

    def test_definitions_cover_both_tools(self):
        """定义列表应恰好包含 get_current_time 与 calculate 两个工具"""
        names = {d["function"]["name"] for d in DEMO_TOOL_DEFINITIONS}
        assert names == {TOOL_NAME_GET_CURRENT_TIME, TOOL_NAME_CALCULATE}

    def test_handlers_match_definitions(self):
        """handler 映射的键集合应与定义列表一致且均可调用"""
        assert set(DEMO_TOOL_HANDLERS) == {
            d["function"]["name"] for d in DEMO_TOOL_DEFINITIONS
        }
        for handler in DEMO_TOOL_HANDLERS.values():
            assert callable(handler)

    def test_calculate_definition_requires_expression(self):
        """calculate 的工具定义应声明 expression 为必填参数"""
        definition = next(
            d for d in DEMO_TOOL_DEFINITIONS
            if d["function"]["name"] == TOOL_NAME_CALCULATE
        )
        params = definition["function"]["parameters"]
        assert params["required"] == ["expression"]
        assert "expression" in params["properties"]
