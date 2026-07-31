"""Framework API Demo 演示工具

提供两个纯函数演示工具及其 OpenAI function calling 格式定义：
- get_current_time：返回当前时间字符串；
- calculate：对四则运算表达式做 AST 白名单安全求值（禁止 eval）。

本模块为 function/ 业务层，不依赖 PySide6。
工具 handler 约定：非法输入返回错误字符串而非抛出异常
（ToolCallExecutor 会把 handler 异常转成错误文本回传模型，
这里主动返回错误字符串可给出更友好的中文提示）。
"""

import ast
import operator
from datetime import datetime
from typing import Any, Callable, Dict, List

# 时间字符串展示格式
TIME_DISPLAY_FORMAT = "%Y-%m-%d %H:%M:%S"

# 算术运算 AST 节点到运算符的白名单映射（仅 +-*/ 与取负）
_BINARY_OPERATORS: Dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}
_UNARY_OPERATORS: Dict[type, Callable[[float], float]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

TOOL_NAME_GET_CURRENT_TIME = "get_current_time"
TOOL_NAME_CALCULATE = "calculate"


def get_current_time() -> str:
    """返回当前时间字符串（无参数工具，演示 LLM 获取实时信息）"""
    return datetime.now().strftime(TIME_DISPLAY_FORMAT)


def calculate(expression: str) -> str:
    """对四则运算表达式做 AST 白名单安全求值

    参数:
        expression: 仅含数字、+-*/ 与括号的表达式字符串

    返回:
        str: 计算结果字符串；表达式非法或不支持时返回错误说明字符串
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as e:
        return f"错误: 表达式无法解析: {e}"
    try:
        value = _eval_node(tree.body)
    except ValueError as e:
        return f"错误: {e}"
    except ArithmeticError as e:
        # 除零等算术错误（ZeroDivisionError 等）同样按约定转为中文错误串，
        # 不得穿透 handler 抛给 ToolCallExecutor
        return f"错误: 算术运算失败: {e}"
    return str(value)


def _eval_node(node: ast.AST) -> float:
    """递归求值白名单内的 AST 节点，越界节点抛 ValueError"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        return _BINARY_OPERATORS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_eval_node(node.operand))
    raise ValueError(f"不支持的表达式元素: {ast.dump(node)}")


# OpenAI function calling 格式的工具定义列表（IPlugin.llm_tools 契约同款）
DEMO_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": TOOL_NAME_GET_CURRENT_TIME,
            "description": "获取当前日期和时间",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": TOOL_NAME_CALCULATE,
            "description": "计算四则运算表达式（支持 +-*/ 与括号），例如 12*(3+4)",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "仅含数字、+-*/ 与括号的数学表达式",
                    },
                },
                "required": ["expression"],
            },
        },
    },
]

# 工具名 → handler 映射（注册进 ToolRegistry 时按名取用）
DEMO_TOOL_HANDLERS: Dict[str, Callable[..., Any]] = {
    TOOL_NAME_GET_CURRENT_TIME: get_current_time,
    TOOL_NAME_CALCULATE: calculate,
}
