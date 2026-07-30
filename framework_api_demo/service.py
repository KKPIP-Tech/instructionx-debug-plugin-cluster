"""
Framework API Demo 服务接口层

作为 PluginManager API 自动注册的入口，
实际业务逻辑委托给 function.services 包。
"""

from .function.services import (
    DataDemoService,
    TaskDemoService,
    LLMDemoService,
    APIDemoService,
    FrameworkInfoService,
)

__all__ = [
    "DataDemoService",
    "TaskDemoService",
    "LLMDemoService",
    "APIDemoService",
    "FrameworkInfoService",
]
