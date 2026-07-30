"""
Framework API Demo 插件元数据

展示 InstructionX 框架提供的所有核心 API 接口的使用方法。
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class FrameworkAPIDemoPluginInfo(IPluginInfo):
    """Framework API Demo 插件元数据"""

    @property
    def version(self) -> PluginVersion:
        """插件版本"""
        return PluginVersion.from_string("release.1.2.0")

    @property
    def developer(self) -> str:
        """开发者名称"""
        return "InstructionX"

    @property
    def developer_email(self) -> str:
        """开发者邮箱"""
        return "support@instructionx.dev"

    @property
    def developer_website(self) -> str:
        """开发者网站"""
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        """是否免费"""
        return True

    @property
    def description(self) -> str:
        """插件详细描述"""
        return """
        Framework API Demo 插件用于演示 InstructionX 框架提供的所有核心 API 接口。

        演示的接口包括：
        - DataProvider: 数据持久化、发布/订阅、资源管理、活跃实例查询
        - BackgroundTaskManager: 同步/异步/定时/长期任务、取消与状态查询
        - ILLMService（llm_facade）: Provider/模型查询、聊天、流式聊天、嵌入、
          会话管理（创建/发送/流式/查询/删除）、工具调用（ToolRegistry/chat_with_tools）、
          多模态（图片生成/语音合成）、用量统计与 Provider 校验
        - PluginManager: 插件查询、API 注册与调用、Function Tools 导出
        - MCPManager / MCPClientManager: 内置 MCP Server 生命周期、
          service_api 自动桥接工具、远程 MCP Server 连接
        - 框架工具: LoggerManager 五级日志、thread_utils 线程封送、
          FontMap 字体查询、image_utils 图片转 Base64、ThemeManager 主题跟随

        该插件是一个学习工具，帮助开发者了解如何使用框架的各种功能。
        """

    @property
    def service_api(self) -> Dict[str, Any]:
        """Service API 定义"""
        return {
            "demo_data_operation": self._api(
                "演示 DataProvider 数据操作",
                {
                    "operation": {
                        "type": "str",
                        "description": "操作类型: read/write/list",
                        "required": True,
                    },
                    "key": {
                        "type": "str",
                        "description": "数据键名",
                        "required": False,
                    },
                    "value": {
                        "type": "any",
                        "description": "数据值",
                        "required": False,
                    },
                },
                {"type": "any", "description": "操作结果"},
            ),
            "demo_task_operation": self._api(
                "演示任务操作",
                {
                    "operation": {
                        "type": "str",
                        "description": "操作类型: create/query/cancel",
                        "required": True,
                    },
                    "task_type": {
                        "type": "str",
                        "description": "任务类型: sync/async/scheduled（仅 create 使用）",
                        "required": False,
                    },
                    "task_id": {
                        "type": "str",
                        "description": "目标任务 ID（cancel 操作必填）",
                        "required": False,
                    },
                },
                {"type": "any", "description": "操作结果"},
            ),
            "get_framework_info": self._api(
                "获取框架信息",
                {},
                {"type": "dict", "description": "框架信息字典"},
            ),
        }

    def _api(self, desc: str, params: Dict, returns: Dict) -> Dict:
        return {"description": desc, "parameters": params, "returns": returns}

    @property
    def skill_icon(self) -> PluginIcon:
        """插件图标配置"""
        return PluginIcon.builtin("SP_VistaShield")

    @property
    def skill_description(self) -> str:
        """插件简短描述"""
        return "演示框架所有 API 接口"

    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["demo", "api", "framework", "learning"]

    @property
    def dependencies(self) -> Dict[str, str]:
        """依赖项"""
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符

        用于代码层面的插件识别，应保持稳定不随显示名称变化。
        建议使用小写字母、数字、连字符格式。
        """
        return "framework-api-demo"
