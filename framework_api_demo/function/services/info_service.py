"""
Framework API Demo 框架信息服务

提供框架版本与可用 API 清单信息。
"""

from typing import Any, Dict

from core.version import get_instructionx_version_string

from .base import Service


class FrameworkInfoService(Service):
    """获取框架信息的服务类"""

    def get_framework_info(self) -> Dict[str, Any]:
        """获取框架信息"""
        return {
            "framework": "InstructionX",
            "version": get_instructionx_version_string(),
            "apis": [
                "DataProvider",
                "BackgroundTaskManager",
                "LLMProvider",
                "PluginManager",
                "LoggerManager",
            ],
        }
