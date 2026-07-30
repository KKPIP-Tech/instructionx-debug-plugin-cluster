"""
Framework API Demo LLM 演示服务

演示 ILLMService（llm_facade）接口：Provider 实例列表、模型列表、
聊天与嵌入调用，统一经基类解析的 self.llm（插件侧门面）访问。
"""

from typing import Any, Dict, List, Optional

from core.llm.types import ProviderInfo

from .base import Service

# 默认实例引用（语义等同 core.llm.types.DEFAULT_PROVIDER，字面量演示 ILLMService 约定）
DEFAULT_PROVIDER_REF = "default"


class LLMDemoService(Service):
    """演示 ILLMService（llm_facade）接口的服务类"""

    def get_providers(self) -> Dict[str, Any]:
        """演示 ILLMService.list_providers / get_default_provider_id / resolve_provider_id"""
        try:
            providers = self.llm.list_providers()
            return {
                "success": True,
                "providers": [p.instance_id for p in providers],
                "provider_details": [self._provider_to_dict(p) for p in providers],
                "default_chat_provider": self.llm.get_default_provider_id(feature="chat"),
                "resolved_default": self.llm.resolve_provider_id(DEFAULT_PROVIDER_REF),
            }
        except Exception as e:
            self.logger.error(f"[{self.plugin_id}] 获取 Provider 列表失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _provider_to_dict(provider: ProviderInfo) -> Dict[str, Any]:
        """将 ProviderInfo 转换为展示用字典（实例 id、名称、启用状态等）"""
        return {
            "instance_id": provider.instance_id,
            "name": provider.name,
            "adapter": provider.adapter,
            "enabled_chat": provider.enabled_chat,
            "enabled_embedding": provider.enabled_embedding,
            "is_healthy": provider.is_healthy,
        }

    def get_models(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """演示 ILLMService.get_models（provider 缺省时用 "default" 默认实例）"""
        target = provider or DEFAULT_PROVIDER_REF
        try:
            models = self.llm.get_models(provider=target)
            return {
                "success": True,
                "models": [{"id": m.id, "name": m.name} for m in models],
                "provider": self.llm.resolve_provider_id(target),
            }
        except Exception as e:
            self.logger.error(f"[{self.plugin_id}] 获取模型列表失败(provider={target}): {e}")
            return {"success": False, "error": str(e)}

    def send_chat(self, message: str = "你好", provider: str = DEFAULT_PROVIDER_REF) -> Dict[str, Any]:
        """演示 ILLMService.chat（messages 字典列表，返回 ChatResponse）"""
        try:
            messages: List[Dict[str, str]] = [{"role": "user", "content": message}]
            response = self.llm.chat(messages, provider=provider)
            return {
                "success": True,
                "response": response.content,
                "model": response.model,
                "provider": self.llm.resolve_provider_id(provider),
            }
        except Exception as e:
            self.logger.error(f"[{self.plugin_id}] 聊天请求失败(provider={provider}): {e}")
            return {"success": False, "error": str(e)}

    def send_embedding(self, text: str = "Hello world", provider: str = DEFAULT_PROVIDER_REF) -> Dict[str, Any]:
        """演示 ILLMService.embed（texts 支持 str 或 List[str]，返回 List[EmbeddingResponse]）"""
        try:
            response = self.llm.embed(texts=[text], provider=provider)
            return {
                "success": True,
                "embedding_size": len(response[0].embedding) if response else 0,
                "provider": self.llm.resolve_provider_id(provider),
            }
        except Exception as e:
            self.logger.error(f"[{self.plugin_id}] 嵌入请求失败(provider={provider}): {e}")
            return {"success": False, "error": str(e)}
