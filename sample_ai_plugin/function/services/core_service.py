"""
示例 AI 插件核心业务逻辑

封装 LLMPluginService 调用，提供对话管理和消息发送能力。
"""

from core.llm import get_llm_plugin_service


class CoreService:
    """示例 AI 插件核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._llm = get_llm_plugin_service()

    def get_available_providers(self):
        """获取可用 Provider 列表"""
        return self._llm.get_available_providers()

    def create_conversation(self, system_prompt: str, provider: str, model: str) -> str:
        """创建对话"""
        return self._llm.create_conversation(
            system_prompt=system_prompt,
            provider=provider,
            model=model,
        )

    def send_message(self, conv_id: str, message: str) -> str:
        """同步发送消息"""
        return self._llm.send_message(conv_id, message)

    def stream_send_message(self, conv_id: str, message: str, callback):
        """流式发送消息"""
        return self._llm.stream_send_message(conv_id, message, callback=callback)

    def get_tool_executor(self):
        """获取工具执行器"""
        return self._llm.get_tool_executor()

    def register_tools(self):
        """注册示例工具到共享工具注册表"""
        from ..tools.llm_tools import register_sample_tools
        register_sample_tools()
