"""
LLM Chat 服务接口层
仅作为接口层，代理到具体服务实现。禁止在此文件中写业务逻辑和 UI 操作代码。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.data.data_provider import DataProvider


class Service:
    """LLM Chat 服务接口层（仅代理，不含业务逻辑）"""

    def __init__(self, plugin_id: str, data_provider: "DataProvider | None" = None):
        from .function.services.core_service import LLMChatService

        self._impl = LLMChatService(plugin_id, data_provider)

    def __getattr__(self, name: str):
        return getattr(self._impl, name)
