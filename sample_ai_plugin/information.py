"""
示例 AI 插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class SampleAIPluginInfo(IPluginInfo):
    """示例 AI 插件元数据"""

    @property
    def version(self) -> PluginVersion:
        return PluginVersion.from_string("release.1.0.0")

    @property
    def developer(self) -> str:
        return "KKPIP-Tech"

    @property
    def developer_email(self) -> str:
        return "support@example.com"

    @property
    def developer_website(self) -> str:
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "示例AI插件演示LLMPluginService的完整集成方式：创建对话、发送消息（同步）、流式发送消息、工具调用"

    @property
    def service_api(self) -> Dict[str, Any]:
        def api(name, params, returns):
            return {"description": name, "parameters": params, "returns": returns}
        return {
            "get_available_providers": api("获取所有可用的 LLM Provider 列表", {}, {"type": "list", "description": "Provider 列表"}),
            "create_conversation": api("创建新对话", {"system_prompt": {"type": "str", "description": "系统提示词", "required": True}, "provider": {"type": "str", "description": "Provider 名称", "required": True}, "model": {"type": "str", "description": "模型名称", "required": True}}, {"type": "str", "description": "对话 ID"}),
            "send_message": api("同步发送消息到对话", {"conv_id": {"type": "str", "description": "对话 ID", "required": True}, "message": {"type": "str", "description": "消息内容", "required": True}}, {"type": "str", "description": "助手回复内容"})
        }

    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_MessageBoxInformation")

    @property
    def skill_description(self) -> str:
        return "LLMPluginService 演示插件"

    @property
    def tags(self) -> Optional[list[str]]:
        return ["ai", "llm", "demo"]

    @property
    def dependencies(self) -> Dict[str, str]:
        return {}

    @property
    def plugin_type_id(self) -> str:
        return "sample-ai-plugin"
