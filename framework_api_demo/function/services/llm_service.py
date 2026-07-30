"""
Framework API Demo LLM 演示服务

演示 ILLMService（llm_facade）接口：Provider 实例列表、模型列表、
聊天（含流式）、嵌入调用与会话管理（创建/发送/流式发送/查询/删除），
统一经基类解析的 self.llm（插件侧门面）访问。
流式聊天为阻塞调用，经 BackgroundTaskManager 放到工作线程执行，
片段/完成事件经基类 notifier 上抛，由 UI 层自行线程封送。
"""

from typing import Any, Callable, Dict, List, Optional

from core.llm.types import Conversation, ProviderInfo, StreamChunk
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

# 会话消息后台任务名（register_sync_task 的 name 参数）
CONV_SEND_TASK_NAME = "llm_conversation_send"
CONV_STREAM_TASK_NAME = "llm_conversation_stream"
# 会话演示 notifier 事件前缀（沿用流式聊天的片段/完成/失败协议风格，
# 前缀独立以便 UI 区分聊天测试与会话演示两个输出区）
CONV_REPLY_PREFIX = "[会话回复] "
CONV_ERROR_PREFIX = "[会话失败] "
CONV_STREAM_CHUNK_PREFIX = "[会话流式片段] "
CONV_STREAM_DONE_EVENT = "[会话流式完成]"
CONV_STREAM_ERROR_PREFIX = "[会话流式失败] "


class LLMDemoService(Service):
    """演示 ILLMService（llm_facade）接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        # 最近一次流式聊天的聚合结果（工作线程写入，UI 在完成事件后读取）
        self._last_stream_result: Optional[Dict[str, Any]] = None
        # 本插件创建的会话 id 记录（卸载 cleanup 时据此清理）
        self._conversation_ids: List[str] = []
        # 最近一次会话流式发送的聚合结果（工作线程写入，UI 在完成事件后读取）
        self._last_conv_stream_result: Optional[Dict[str, Any]] = None

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

    # ------------------------------------------------------------------
    #  会话管理演示
    # ------------------------------------------------------------------

    def create_conversation_demo(self, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """演示 ILLMService.create_conversation：创建会话并记录 id（供卸载清理）"""
        try:
            conversation_id = self.llm.create_conversation(system_prompt=system_prompt or None)
            self._conversation_ids.append(conversation_id)
            return {"success": True, "conversation_id": conversation_id}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 创建会话失败: {e}")
            return {"success": False, "error": str(e)}

    def send_conversation_message(self, conversation_id: str, content: str) -> Dict[str, Any]:
        """演示 ILLMService.send_message（阻塞调用，经后台任务执行）

        send_message 内部同步等待 LLM 响应，直接在 UI 线程调用会卡界面，
        因此经 register_sync_task 放到工作线程执行；本方法立即返回任务已发起，
        最终回复文本经完成回调 + notifier 上抛（CONV_REPLY_PREFIX 事件）。
        """
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=CONV_SEND_TASK_NAME,
                func=self._run_conv_send, args=(conversation_id, content),
                callback=self._on_conv_send_done,
            )
            return {"success": True, "task_id": task_id, "message": "会话消息已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起会话消息失败({conversation_id}): {e}")
            return {"success": False, "error": str(e)}

    def stream_conversation_message(self, conversation_id: str, content: str) -> Dict[str, Any]:
        """演示 ILLMService.stream_send_message（阻塞调用，经后台任务执行）

        StreamChunk 回调逐段经 notifier 上抛（CONV_STREAM_CHUNK_PREFIX 事件），
        完整文本在完成事件后由 UI 经 get_last_conversation_stream_result 拉取。
        """
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=CONV_STREAM_TASK_NAME,
                func=self._run_conv_stream, args=(conversation_id, content),
                callback=self._on_conv_stream_done,
            )
            return {"success": True, "task_id": task_id, "message": "会话流式消息已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起会话流式消息失败({conversation_id}): {e}")
            return {"success": False, "error": str(e)}

    def get_last_conversation_stream_result(self) -> Dict[str, Any]:
        """返回最近一次会话流式发送的聚合结果（供 UI 在完成事件后拉取展示）"""
        return {"success": True, "result": self._last_conv_stream_result}

    def list_conversations_demo(self) -> Dict[str, Any]:
        """演示 ILLMService.list_conversations：返回会话摘要列表"""
        try:
            conversations = self.llm.list_conversations()
            return {
                "success": True,
                "conversations": [self._conversation_to_summary(c) for c in conversations],
            }
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 获取会话列表失败: {e}")
            return {"success": False, "error": str(e)}

    def get_conversation_demo(self, conversation_id: str) -> Dict[str, Any]:
        """演示 ILLMService.get_conversation：返回会话详情（含消息历史）"""
        try:
            conversation = self.llm.get_conversation(conversation_id)
            if conversation is None:
                return {"success": False, "error": f"会话不存在: {conversation_id}"}
            detail = self._conversation_to_summary(conversation)
            detail["messages"] = conversation.messages
            return {"success": True, "conversation": detail}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 获取会话详情失败({conversation_id}): {e}")
            return {"success": False, "error": str(e)}

    def delete_conversation_demo(self, conversation_id: str) -> Dict[str, Any]:
        """演示 ILLMService.delete_conversation：删除会话并从本地记录移除"""
        try:
            deleted = self.llm.delete_conversation(conversation_id)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 删除会话失败({conversation_id}): {e}")
            return {"success": False, "error": str(e)}
        if conversation_id in self._conversation_ids:
            self._conversation_ids.remove(conversation_id)
        if not deleted:
            return {"success": False, "error": f"删除会话失败: {conversation_id}"}
        return {"success": True, "conversation_id": conversation_id}

    @staticmethod
    def _conversation_to_summary(conversation: Conversation) -> Dict[str, Any]:
        """将 Conversation 转换为展示用摘要字典（时间转 ISO 字符串保证可序列化）"""
        return {
            "id": conversation.id,
            "message_count": len(conversation.messages),
            "provider": conversation.provider,
            "model": conversation.model,
            "system_prompt": conversation.system_prompt,
            "total_tokens": conversation.total_tokens,
            "total_cost": conversation.total_cost,
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "metadata": conversation.metadata,
        }

    def _run_conv_send(self, conversation_id: str, content: str) -> Dict[str, Any]:
        """在工作线程执行 send_message，返回回复文本"""
        reply = self.llm.send_message(conversation_id, content)
        return {"success": True, "conversation_id": conversation_id, "response": reply}

    def _on_conv_send_done(self, task_id: str, status, result, error) -> None:
        """会话消息任务完成回调（工作线程）：经 notifier 上抛回复/失败事件"""
        try:
            if error:
                self._notify_event(f"{CONV_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 会话消息任务失败({task_id}): {error}")
                return
            response = (result or {}).get("response", "")
            self._notify_event(f"{CONV_REPLY_PREFIX}{response}")
            self.logger.info(get_name(), f"[{self.plugin_id}] 会话消息任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 会话消息完成回调处理失败: {e}")

    def _run_conv_stream(self, conversation_id: str, content: str) -> Dict[str, Any]:
        """在工作线程执行 stream_send_message：StreamChunk 逐段上抛，返回聚合结果"""
        chunks: List[str] = []
        full_text = self.llm.stream_send_message(
            conversation_id, content, callback=self._make_conv_stream_callback(chunks),
        )
        result: Dict[str, Any] = {
            "success": True,
            "conversation_id": conversation_id,
            "response": full_text,
            "chunk_count": len(chunks),
        }
        self._last_conv_stream_result = result
        return result

    def _make_conv_stream_callback(self, chunks: List[str]) -> Callable[[StreamChunk], None]:
        """构造会话流式回调（StreamChunk）：收集增量片段并经 notifier 上抛，异常仅记日志"""

        def on_chunk(chunk: StreamChunk) -> None:
            try:
                if chunk.content:
                    chunks.append(chunk.content)
                    self._notify_event(f"{CONV_STREAM_CHUNK_PREFIX}{chunk.content}")
            except Exception as e:
                self.logger.error(get_name(), f"[{self.plugin_id}] 会话流式回调处理失败: {e}")

        return on_chunk

    def _on_conv_stream_done(self, task_id: str, status, result, error) -> None:
        """会话流式任务完成回调（工作线程）：经 notifier 上抛完成/失败事件"""
        try:
            if error:
                self._notify_event(f"{CONV_STREAM_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 会话流式任务失败({task_id}): {error}")
                return
            self._notify_event(CONV_STREAM_DONE_EVENT)
            self.logger.info(get_name(), f"[{self.plugin_id}] 会话流式任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 会话流式完成回调处理失败: {e}")

    # ------------------------------------------------------------------
    #  卸载清理
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """卸载清理：删除本插件创建的全部会话（逐项容错，异常仅记日志）"""
        for conversation_id in list(self._conversation_ids):
            self._delete_one_conversation(conversation_id)
        self._conversation_ids.clear()

    def _delete_one_conversation(self, conversation_id: str) -> None:
        """删除单个会话，失败仅记日志不中断其余清理"""
        try:
            self.llm.delete_conversation(conversation_id)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 卸载清理：删除会话失败({conversation_id}): {e}")
