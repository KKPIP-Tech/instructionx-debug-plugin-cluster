"""
Framework API Demo LLM 演示服务

演示 ILLMService（llm_facade）接口：Provider 实例列表、模型列表、
聊天（含流式）与嵌入调用，统一经基类解析的 self.llm（插件侧门面）访问。
流式聊天为阻塞调用，经 BackgroundTaskManager 放到工作线程执行，
片段/完成事件经基类 notifier 上抛，由 UI 层自行线程封送。
"""

from typing import Any, Callable, Dict, List, Optional

from core.llm.types import ProviderInfo
from utils.logging_tools import get_name

from .base import Service

# 默认实例引用（语义等同 core.llm.types.DEFAULT_PROVIDER，字面量演示 ILLMService 约定）
DEFAULT_PROVIDER_REF = "default"

# 流式聊天后台任务名（register_sync_task 的 name 参数）
STREAM_TASK_NAME = "llm_stream_chat"
# notifier 事件前缀：UI 依此区分片段增量刷新 / 完成 / 失败三类事件
STREAM_CHUNK_PREFIX = "[流式片段] "
STREAM_DONE_EVENT = "[流式完成]"
STREAM_ERROR_PREFIX = "[流式失败] "


class LLMDemoService(Service):
    """演示 ILLMService（llm_facade）接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        # 最近一次流式聊天的聚合结果（工作线程写入，UI 在完成事件后读取）
        self._last_stream_result: Optional[Dict[str, Any]] = None

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

    # ------------------------------------------------------------------
    #  流式聊天演示
    # ------------------------------------------------------------------

    def send_chat_stream(self, message: str = "你好", provider: str = DEFAULT_PROVIDER_REF) -> Dict[str, Any]:
        """演示 ILLMService.stream_chat 与 last_stream_response

        stream_chat 是阻塞调用（callback 在调用线程同步逐块触发），
        直接在 UI 线程调用会卡界面，因此经 register_sync_task 放到
        工作线程执行；本方法立即返回任务已发起，最终结果经完成回调
        + notifier 上抛（UI 再经 get_last_stream_result 拉取展示）。
        """
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=STREAM_TASK_NAME,
                func=self._run_stream_chat, args=(message, provider),
                callback=self._on_stream_task_done,
            )
            return {"success": True, "task_id": task_id, "message": "流式聊天已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起流式聊天失败(provider={provider}): {e}")
            return {"success": False, "error": str(e)}

    def get_last_stream_result(self) -> Dict[str, Any]:
        """返回最近一次流式聊天的聚合结果（供 UI 在完成事件后拉取展示）"""
        return {"success": True, "result": self._last_stream_result}

    def _run_stream_chat(self, message: str, provider: str) -> Dict[str, Any]:
        """在工作线程执行流式聊天：callback 逐块收集并上抛片段事件，返回聚合结果"""
        chunks: List[str] = []
        messages: List[Dict[str, str]] = [{"role": "user", "content": message}]
        full_text = self.llm.stream_chat(
            messages, self._make_stream_callback(chunks), provider=provider,
        )
        result = self._build_stream_result(full_text, provider, len(chunks))
        self._last_stream_result = result
        return result

    def _make_stream_callback(self, chunks: List[str]) -> Callable[[str, bool], None]:
        """构造流式回调 (chunk, done)：收集增量片段并经 notifier 上抛，异常仅记日志"""

        def on_chunk(chunk: str, done: bool) -> None:
            try:
                chunks.append(chunk)
                if chunk:
                    self._notify_event(f"{STREAM_CHUNK_PREFIX}{chunk}")
            except Exception as e:
                self.logger.error(get_name(), f"[{self.plugin_id}] 流式回调处理失败: {e}")

        return on_chunk

    def _build_stream_result(self, full_text: str, provider: str, chunk_count: int) -> Dict[str, Any]:
        """汇总 stream_chat 返回的完整文本与 last_stream_response（model/usage 等）"""
        result: Dict[str, Any] = {
            "success": True,
            "response": full_text,
            "chunk_count": chunk_count,
            "provider": self.llm.resolve_provider_id(provider),
        }
        last = self.llm.last_stream_response
        if last is not None:
            result["model"] = last.model
            if last.usage is not None:
                result["usage"] = {
                    "input_tokens": last.usage.input_tokens,
                    "output_tokens": last.usage.output_tokens,
                    "total_tokens": last.usage.total_tokens,
                    "total_cost": last.usage.total_cost,
                }
        return result

    def _on_stream_task_done(self, task_id: str, status, result, error) -> None:
        """流式任务完成回调（工作线程）：经 notifier 上抛完成/失败事件，异常不外抛"""
        try:
            if error:
                self._notify_event(f"{STREAM_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 流式聊天任务失败({task_id}): {error}")
                return
            self._notify_event(STREAM_DONE_EVENT)
            self.logger.info(get_name(), f"[{self.plugin_id}] 流式聊天任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 流式完成回调处理失败: {e}")
