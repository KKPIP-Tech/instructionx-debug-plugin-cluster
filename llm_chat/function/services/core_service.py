"""
LLM Chat 服务层 - 处理 LLM 调用逻辑
"""

import base64
import json
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.llm import get_llm_provider
from core.llm.exceptions import (
    LLMException,
    ConfigurationError,
    AuthenticationError,
    APIError,
    RateLimitError,
    TimeoutError,
    ConnectionError,
    InvalidRequestError,
)
from core.llm.provider_interface import Message, ModelInfo
from core.data.data_provider import DataProvider, DataNamespace

from utils.logging_tools import LoggerManager, get_name


# ========== 配置常量 ==========

def _load_config() -> Dict[str, Any]:
    config_path = Path(__file__).parent.parent.parent / "config" / "default.json"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


_CONFIG = _load_config()
_LLM_CONFIG = _CONFIG.get("llm", {})

# 默认值常量
DEFAULT_TEMPERATURE = _LLM_CONFIG.get("default_temperature", 0.7)
DEFAULT_MAX_TOKENS_OPTIONS = _LLM_CONFIG.get("max_tokens_options", [256, 512, 1024, 2048, 4096])

# 数据 key 常量
_KEY_CHAT_HISTORY = "chat_history"
_KEY_LAST_PROVIDER = "last_provider"
_KEY_LAST_MODEL_PREFIX = "last_model_"
_KEY_SYSTEM_LLM = "__app_llm__"
_KEY_LLM_PROVIDER = "provider"
_KEY_LLM_MODEL = "model"


class LLMChatService:
    """LLM Chat 服务类"""

    _logger = LoggerManager()

    def __init__(self, plugin_id: str, data_provider: Optional[DataProvider] = None):
        self.plugin_id = plugin_id
        self.data_provider = data_provider or DataProvider()
        self._llm_provider = None

    @property
    def llm_provider(self):
        """获取 LLM Provider 单例"""
        if self._llm_provider is None:
            self._llm_provider = get_llm_provider()
        return self._llm_provider

    def get_providers(self) -> List[str]:
        """获取所有可用的 Provider 列表"""
        try:
            providers = self.llm_provider.get_enabled_providers("chat")
            return list(providers.keys())
        except Exception as e:
            self._logger.error(get_name(), f'获取 Provider 列表失败: {e}')
            return []

    def get_all_providers(self) -> Dict[str, Any]:
        """获取所有 Provider（包括未启用的）"""
        try:
            return self.llm_provider.get_all_providers()
        except Exception as e:
            self._logger.error(get_name(), f'获取所有 Provider 失败: {e}')
            return {}

    def get_models(self, provider: str) -> List[ModelInfo]:
        """获取指定 Provider 的模型列表"""
        try:
            # 优先从缓存获取
            cached_models = self.llm_provider.get_cached_models(provider)
            if cached_models:
                return cached_models

            # 从 Provider 获取
            provider_instance = self.llm_provider.get_provider(provider)
            if provider_instance:
                return provider_instance.get_models()
            return []
        except Exception as e:
            self._logger.error(get_name(), f'获取模型列表失败: {e}')
            return []

    def get_provider_config(self, provider: str) -> Optional[Dict[str, Any]]:
        """获取 Provider 配置"""
        try:
            config = self.llm_provider.config.get_provider(provider)
            if config:
                return config.to_dict()
            return None
        except Exception as e:
            self._logger.error(get_name(), f'获取 Provider 配置失败: {e}')
            return None

    def _validate_provider_instance(self, provider: str):
        """验证 Provider 实例"""
        provider_instance = self.llm_provider.get_provider(provider)
        if not provider_instance:
            return {"valid": False, "message": f"Provider '{provider}' 不存在", "supports_vision": False}
        if not provider_instance.validate_config():
            return {"valid": False, "message": "API Key 或 Base URL 未配置", "supports_vision": False}
        models = self.get_models(provider)
        supports_vision = any(getattr(m, "support_vision", False) for m in models)
        return {"valid": True, "message": "配置有效", "supports_vision": supports_vision}

    def validate_provider(self, provider: str) -> Dict[str, Any]:
        """验证 Provider 配置是否有效"""
        self._logger.debug(get_name(), f"Validating provider: {provider}")
        try:
            return self._validate_provider_instance(provider)
        except Exception as e:
            return {"valid": False, "message": f"验证失败: {str(e)}", "supports_vision": False}

    def _build_messages(self, message: str, images: Optional[List[str]],
                          history: Optional[List[Dict[str, str]]]) -> List[Message]:
        """构建消息列表"""
        messages = []
        if history:
            for msg in history:
                messages.append(Message(
                    role=msg.get("role", "user"),
                    content=msg.get("content", ""),
                    images=msg.get("images") or [],
                ))
        messages.append(Message(role="user", content=message, images=images or []))
        return messages

    def _map_error(self, e: Exception, error_type: str, default_msg: str) -> Dict[str, Any]:
        """映射异常到错误响应"""
        return {"success": False, "error": default_msg, "error_type": error_type}

    _ERROR_MAP = {
        AuthenticationError: ("authentication", "认证失败: API Key 无效或已过期。请检查 LLM 设置。"),
        RateLimitError: ("rate_limit", "请求频率超限: API 调用过于频繁，请稍后重试。"),
        TimeoutError: ("timeout", "请求超时: 服务器响应时间过长，请检查网络或稍后重试。"),
        InvalidRequestError: ("invalid_request", None),
        ConfigurationError: ("configuration", None),
        APIError: ("api", None),
    }

    def send_message(self, message: str, provider: str, model: Optional[str] = None,
                     temperature: float = DEFAULT_TEMPERATURE, max_tokens: Optional[int] = None,
                     images: Optional[List[str]] = None,
                     history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """发送消息并获取回复"""
        self._logger.debug(get_name(), f"Provider: {provider}, Model: {model}")
        try:
            messages = self._build_messages(message, images, history)
            response = self.llm_provider.chat(messages=messages, provider=provider, model=model, temperature=temperature, max_tokens=max_tokens)
            return {"success": True, "response": response.content, "model": response.model,
                    "reasoning": getattr(response, "reasoning_content", ""), "tool_calls": getattr(response, "tool_calls", [])}
        except ConnectionError as e:
            msg = f"连接失败: 无法连接到 API 服务器{(' (Provider: '+e.provider+')') if hasattr(e,'provider') else ''} - {str(e)}"
            return {"success": False, "error": msg, "error_type": "connection"}
        except Exception as e:
            for exc_type, (err_type, default_msg) in self._ERROR_MAP.items():
                if isinstance(e, exc_type):
                    return {"success": False, "error": default_msg or f"错误: {str(e)}", "error_type": err_type}
            return {"success": False, "error": f"未知错误: {str(e)}", "error_type": "unknown"}

    def _stream_iterate(self, responses):
        """遍历流式响应并 yield"""
        full_response = ""
        for response in responses:
            content = response.content or ""
            full_response += content
            self._logger.debug(get_name(), f"Chunk: {len(content)} chars")
            yield {"chunk": content, "done": False, "model": response.model}
        yield {"chunk": "", "done": True, "full_response": full_response}

    _STREAM_ERROR_MAP = {
        AuthenticationError: ("authentication", "认证失败: API Key 无效或已过期。"),
        RateLimitError: ("rate_limit", "请求频率超限: API 调用过于频繁。"),
        TimeoutError: ("timeout", "请求超时: 服务器响应时间过长。"),
    }

    def stream_send_message(self, message: str, provider: str, model: Optional[str] = None,
                            temperature: float = DEFAULT_TEMPERATURE, max_tokens: Optional[int] = None,
                            images: Optional[List[str]] = None,
                            history: Optional[List[Dict[str, str]]] = None):
        """流式发送消息（生成器）"""
        self._logger.debug(get_name(), f"Provider: {provider}, Model: {model}")
        try:
            messages = self._build_messages(message, images, history)
            responses = self.llm_provider.stream_chat(messages=messages, provider=provider, model=model, temperature=temperature, max_tokens=max_tokens)
            yield from self._stream_iterate(responses)
        except ConnectionError as e:
            yield {"chunk": "", "done": True, "error": f"连接失败: 无法连接到 API 服务器 - {str(e)}", "error_type": "connection"}
        except Exception as e:
            for exc_type, (err_type, default_msg) in self._STREAM_ERROR_MAP.items():
                if isinstance(e, exc_type):
                    yield {"chunk": "", "done": True, "error": default_msg, "error_type": err_type}
                    return
            import traceback
            self._logger.debug(get_name(), f"Exception: {e}\n{traceback.format_exc()}")
            yield {"chunk": "", "done": True, "error": f"错误: {str(e)}", "error_type": "unknown"}

    def load_image_as_base64(self, image_path: str) -> Optional[str]:
        """
        将图片文件转换为 base64 字符串

        Args:
            image_path: 图片文件路径

        Returns:
            base64 字符串，失败返回 None
        """
        try:
            path = Path(image_path)
            if not path.exists():
                return None

            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception as e:
            self._logger.error(get_name(), f'读取图片失败: {e}')
            return None

    # ========== 数据持久化 ==========

    def save_preference(self, key: str, value: Any):
        """保存偏好设置"""
        self.data_provider.set_plugin_data(
            self.plugin_id,
            key,
            value,
            DataNamespace.PRIVATE,
        )

    def load_preference(self, key: str, default: Any = None) -> Any:
        """加载偏好设置"""
        return self.data_provider.get_plugin_data(
            self.plugin_id,
            key,
            DataNamespace.PRIVATE,
            default,
        )

    def save_chat_history(self, history: List[Dict[str, Any]]):
        """保存对话历史"""
        self.save_preference(_KEY_CHAT_HISTORY, history)

    def load_chat_history(self) -> List[Dict[str, Any]]:
        """加载对话历史"""
        return self.load_preference(_KEY_CHAT_HISTORY, [])

    def get_current_llm_preference(self) -> tuple:
        """获取当前全局 LLM 选择（供其他插件使用）

        从 DataProvider 读取系统级 LLM Provider/Model 选择。

        Returns:
            tuple: (provider_name, model_name)
        """
        provider = self.data_provider.get_plugin_data(
            _KEY_SYSTEM_LLM, _KEY_LLM_PROVIDER, DataNamespace.PRIVATE, ""
        )
        model = self.data_provider.get_plugin_data(
            _KEY_SYSTEM_LLM, _KEY_LLM_MODEL, DataNamespace.PRIVATE, ""
        )
        return provider, model
