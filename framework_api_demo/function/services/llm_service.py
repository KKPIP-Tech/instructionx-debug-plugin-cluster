"""
Framework API Demo LLM 演示服务

演示 LLM 能力（Provider/模型列表、聊天、嵌入）。
注意：本批次仍经 LLMProvider 单例调用，后续批次统一迁移至 llm_facade；
构造已改为经基类解析，预留 self.llm_facade 供迁移使用。
"""

from typing import Any, Dict

from core.llm.llm_provider import LLMProvider

from .base import Service


class LLMDemoService(Service):
    """演示 LLMProvider 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        # 预留：下一批次 LLM 调用统一迁移至 self.llm_facade（ILLMService 契约）
        self.llm_facade = self.llm
        self.llm_provider = LLMProvider()

    def get_providers(self) -> Dict[str, Any]:
        """演示获取 Provider 列表"""
        try:
            providers = self.llm_provider.get_all_providers()
            return {
                "success": True,
                "providers": list(providers.keys()),
                "enabled": list(self.llm_provider.get_enabled_providers().keys()),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_models(self, provider: str = None) -> Dict[str, Any]:
        """演示获取模型列表"""
        try:
            if provider:
                return self._get_models_by_provider(provider)
            return self._get_all_models()
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_models_by_provider(self, provider: str) -> Dict[str, Any]:
        """按 Provider 获取模型"""
        models = self.llm_provider.get_cached_models(provider)
        return {
            "success": True,
            "models": [{"id": m.id, "name": m.name} for m in models],
        }

    def _get_all_models(self) -> Dict[str, Any]:
        """获取所有 Provider 的模型"""
        models_dict = self.llm_provider.get_models()
        return {
            "success": True,
            "models": {
                k: [{"id": m.id, "name": m.name} for m in v]
                for k, v in models_dict.items()
            },
        }

    def send_chat(self, message: str = "你好", provider: str = "default") -> Dict[str, Any]:
        """演示发送聊天请求"""
        try:
            messages = [{"role": "user", "content": message}]
            response = self.llm_provider.chat(messages, provider=provider)
            return {
                "success": True,
                "response": response.content,
                "model": response.model,
                "provider": provider,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_embedding(self, text: str = "Hello world", provider: str = "default") -> Dict[str, Any]:
        """演示发送嵌入请求"""
        try:
            response = self.llm_provider.embed(texts=text, provider=provider)
            return {
                "success": True,
                "embedding_size": len(response[0].embedding) if response else 0,
                "provider": provider,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
