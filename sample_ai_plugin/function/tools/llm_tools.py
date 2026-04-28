"""
LLM 工具定义

展示如何注册工具供 LLM 调用。
"""

from core.llm import get_llm_plugin_service


def calculate(expression: str) -> str:
    """执行数学表达式计算"""
    try:
        result = eval(expression)
        return str(result)
    except Exception as e:
        return f"计算错误: {e}"


def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _calculate_tool():
    return {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "执行数学表达式计算。输入为标准数学表达式字符串，如 '2+3*4'。",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "数学表达式，如 '2+3*4'"}},
                "required": ["expression"],
            },
        }
    }


def _time_tool():
    return {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "获取当前系统时间。无需参数。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }
    }


def get_sample_tools() -> list:
    """返回示例工具定义列表（OpenAI function calling 格式）"""
    return [_calculate_tool(), _time_tool()]


def register_sample_tools():
    """注册示例工具到共享工具注册表"""
    svc = get_llm_plugin_service()
    registry = svc.get_shared_tool_registry()
    calc_params = {"type": "object", "properties": {"expression": {"type": "string", "description": "数学表达式，如 '2+3*4'"}}, "required": ["expression"]}
    time_params = {"type": "object", "properties": {}, "required": []}
    registry.register(name="calculate", description="执行数学表达式计算。输入为标准数学表达式字符串。", parameters=calc_params, handler=calculate)
    registry.register(name="get_current_time", description="获取当前系统时间。无需参数。", parameters=time_params, handler=get_current_time)
