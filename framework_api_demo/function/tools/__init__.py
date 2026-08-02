"""Framework API Demo 演示工具包

导出演示工具定义（OpenAI function 格式）与对应 handler 映射，
供服务层注册进共享 ToolRegistry、入口层经 IPlugin.llm_tools 声明。
"""

from .demo_tools import (
    DEMO_TOOL_DEFINITIONS,
    DEMO_TOOL_HANDLERS,
    calculate,
    get_current_time,
)

__all__ = [
    "DEMO_TOOL_DEFINITIONS",
    "DEMO_TOOL_HANDLERS",
    "calculate",
    "get_current_time",
]
