"""
Framework API Demo LLM 演示服务

演示 ILLMService（llm_facade）接口：Provider 实例列表、模型列表、
聊天（含流式）、嵌入调用、会话管理（创建/发送/流式发送/查询/删除）
与工具调用（共享 ToolRegistry 注册/注销 + chat_with_tools 多轮循环），
统一经基类解析的 self.llm（插件侧门面）访问。
流式聊天为阻塞调用，经 BackgroundTaskManager 放到工作线程执行，
片段/完成事件经基类 notifier 上抛，由 UI 层自行线程封送。
"""

import base64
from typing import Any, Callable, Dict, List, Optional

from core.llm.types import (
    AudioResult,
    Conversation,
    ImageResult,
    ProviderInfo,
    StreamChunk,
    ToolChatResult,
    ToolResult,
    UsageStats,
)
from utils.logging_tools import get_name

from ..tools.demo_tools import DEMO_TOOL_DEFINITIONS, DEMO_TOOL_HANDLERS
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

# 工具调用后台任务名（register_sync_task 的 name 参数）
TOOL_CHAT_TASK_NAME = "llm_tool_chat"
# 工具调用演示的最大工具调用轮数（防无限循环，与框架默认一致）
TOOL_CHAT_MAX_TURNS = 5
# 工具调用演示 notifier 事件前缀（前缀独立，避免与聊天/会话事件串台）
TOOL_DONE_EVENT = "[工具对话完成]"
TOOL_ERROR_PREFIX = "[工具对话失败] "

# 多模态后台任务名（register_sync_task 的 name 参数）
IMAGE_TASK_NAME = "llm_generate_image"
TTS_TASK_NAME = "llm_text_to_speech"
# 多模态演示 notifier 事件前缀（前缀独立，避免与聊天/会话/工具事件串台）
IMAGE_DONE_EVENT = "[图片生成完成]"
IMAGE_ERROR_PREFIX = "[图片生成失败] "
TTS_DONE_EVENT = "[语音合成完成]"
TTS_ERROR_PREFIX = "[语音合成失败] "
# save_asset 落盘文件名：ImageResult.base64 解码为 PNG 字节，AudioResult.audio_data 为 MP3 字节
IMAGE_ASSET_FILENAME = "demo_image.png"
AUDIO_ASSET_FILENAME = "demo_audio.mp3"


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
        # 最近一次工具对话的聚合结果（工作线程写入，UI 在完成事件后读取）
        self._last_tool_chat_result: Optional[Dict[str, Any]] = None
        # 最近一次图片生成 / 语音合成的聚合结果（工作线程写入，UI 在完成事件后读取）
        self._last_image_result: Optional[Dict[str, Any]] = None
        self._last_audio_result: Optional[Dict[str, Any]] = None

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
    #  工具调用演示
    # ------------------------------------------------------------------

    def register_demo_tools(self) -> Dict[str, Any]:
        """演示 ILLMService.get_shared_tool_registry().register：注册全部演示工具

        共享 ToolRegistry 默认重名抛 ValueError，replace=True 覆盖同名旧注册；
        这里逐个用 replace=True，保证幂等（重复点击注册不报错）。
        """
        try:
            registry = self.llm.get_shared_tool_registry()
            registered = self._register_all_demo_tools(registry)
            return {"success": True, "registered": registered}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 注册演示工具失败: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _register_all_demo_tools(registry) -> List[str]:
        """把 DEMO_TOOL_DEFINITIONS 逐个注册进注册表（replace 覆盖），返回工具名列表"""
        registered: List[str] = []
        for definition in DEMO_TOOL_DEFINITIONS:
            func = definition["function"]
            name = func["name"]
            registry.register(
                name=name,
                description=func["description"],
                parameters=func["parameters"],
                handler=DEMO_TOOL_HANDLERS[name],
                replace=True,
            )
            registered.append(name)
        return registered

    def unregister_demo_tools(self) -> Dict[str, Any]:
        """演示 ToolRegistry.unregister：注销全部演示工具"""
        try:
            registry = self.llm.get_shared_tool_registry()
            removed = [n for n in DEMO_TOOL_HANDLERS if registry.unregister(n)]
            return {"success": True, "unregistered": removed}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 注销演示工具失败: {e}")
            return {"success": False, "error": str(e)}

    def list_registered_tools(self) -> Dict[str, Any]:
        """演示 ToolRegistry.list_tools / get_tools：展示共享注册表全貌"""
        try:
            registry = self.llm.get_shared_tool_registry()
            definitions = registry.get_tools()
            return {
                "success": True,
                "tool_names": registry.list_tools(),
                "tool_descriptions": {
                    d["function"]["name"]: d["function"]["description"] for d in definitions
                },
            }
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 查询已注册工具失败: {e}")
            return {"success": False, "error": str(e)}

    def chat_with_tools_demo(self, message: str) -> Dict[str, Any]:
        """演示 ILLMService.chat_with_tools（阻塞多轮调用，经后台任务执行）

        调用前确保演示工具已注册（幂等）；chat_with_tools 内部为
        LLM → 工具调用 → 结果回传 的多轮阻塞循环，经 register_sync_task
        放到工作线程执行，聚合结果经完成回调 + notifier 上抛。
        """
        try:
            registry = self.llm.get_shared_tool_registry()
            self._register_all_demo_tools(registry)
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=TOOL_CHAT_TASK_NAME,
                func=self._run_tool_chat, args=(message,),
                callback=self._on_tool_chat_done,
            )
            return {"success": True, "task_id": task_id, "message": "工具对话已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起工具对话失败: {e}")
            return {"success": False, "error": str(e)}

    def get_last_tool_chat_result(self) -> Dict[str, Any]:
        """返回最近一次工具对话的聚合结果（供 UI 在完成事件后拉取展示）"""
        return {"success": True, "result": self._last_tool_chat_result}

    def _run_tool_chat(self, message: str) -> Dict[str, Any]:
        """在工作线程执行 chat_with_tools 多轮循环，返回聚合结果"""
        messages: List[Dict[str, str]] = [{"role": "user", "content": message}]
        chat_result = self.llm.chat_with_tools(
            messages, provider=DEFAULT_PROVIDER_REF, max_turns=TOOL_CHAT_MAX_TURNS,
        )
        result = self._build_tool_chat_result(chat_result)
        self._last_tool_chat_result = result
        return result

    @staticmethod
    def _build_tool_chat_result(chat_result: ToolChatResult) -> Dict[str, Any]:
        """汇总 ToolChatResult 为展示用字典（最终文本 + 各轮工具调用明细）"""
        return {
            "success": True,
            "final_text": chat_result.final_text,
            "turn_count": len(chat_result.tool_results),
            "tool_results": [
                LLMDemoService._tool_result_to_dict(r) for r in chat_result.tool_results
            ],
            "message_count": len(chat_result.messages),
        }

    @staticmethod
    def _tool_result_to_dict(tool_result: ToolResult) -> Dict[str, Any]:
        """将 ToolResult 转换为展示用字典（工具名/参数/结果/错误）"""
        return {
            "tool_name": tool_result.tool_name,
            "arguments": tool_result.arguments,
            "result": str(tool_result.result),
            "error": tool_result.error,
        }

    def _on_tool_chat_done(self, task_id: str, status, result, error) -> None:
        """工具对话任务完成回调（工作线程）：经 notifier 上抛完成/失败事件"""
        try:
            if error:
                self._notify_event(f"{TOOL_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 工具对话任务失败({task_id}): {error}")
                return
            self._notify_event(TOOL_DONE_EVENT)
            self.logger.info(get_name(), f"[{self.plugin_id}] 工具对话任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 工具对话完成回调处理失败: {e}")

    # ------------------------------------------------------------------
    #  多模态演示（图像生成 / 语音合成）
    # ------------------------------------------------------------------

    def generate_image_demo(self, prompt: str, provider: str = DEFAULT_PROVIDER_REF) -> Dict[str, Any]:
        """演示 ILLMService.generate_image（阻塞调用，经后台任务执行）

        generate_image 为同步 HTTP 请求，经 register_sync_task 放到工作线程；
        聚合结果在完成事件后由 UI 经 get_last_image_result 拉取展示。
        """
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=IMAGE_TASK_NAME,
                func=self._run_generate_image, args=(prompt, provider),
                callback=self._on_image_task_done,
            )
            return {"success": True, "task_id": task_id, "message": "图片生成已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起图片生成失败(provider={provider}): {e}")
            return {"success": False, "error": str(e)}

    def get_last_image_result(self) -> Dict[str, Any]:
        """返回最近一次图片生成的聚合结果（供 UI 在完成事件后拉取展示）"""
        return {"success": True, "result": self._last_image_result}

    def _run_generate_image(self, prompt: str, provider: str) -> Dict[str, Any]:
        """在工作线程执行 generate_image，返回聚合结果（base64 数据经 save_asset 落盘）"""
        image = self.llm.generate_image(prompt, provider=provider)
        result = self._build_image_result(image)
        self._last_image_result = result
        return result

    def _build_image_result(self, image: ImageResult) -> Dict[str, Any]:
        """汇总 ImageResult 为展示用字典；base64 数据落盘为资源文件并返回路径"""
        result: Dict[str, Any] = {
            "success": True,
            "model": image.model,
            "provider": image.provider,
            "url": image.url,
            "revised_prompt": image.revised_prompt,
            "has_base64": image.base64 is not None,
        }
        if image.base64 is not None:
            result.update(self._save_base64_asset(image.base64, IMAGE_ASSET_FILENAME))
        return result

    def _save_base64_asset(self, base64_data: str, filename: str) -> Dict[str, Any]:
        """base64 解码后经 DataProvider.save_asset 落盘；保存失败容错返回错误字段"""
        try:
            content = base64.b64decode(base64_data)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] base64 解码失败({filename}): {e}")
            return {"asset_save_error": f"base64 解码失败: {e}"}
        return self._save_bytes_asset(content, filename)

    def _save_bytes_asset(self, content: bytes, filename: str) -> Dict[str, Any]:
        """经 DataProvider.save_asset 保存字节内容；失败容错返回错误字段（不中断演示）"""
        try:
            path = self.dp.save_asset(self.plugin_id, filename, content)
            return {"asset_path": path, "asset_size": len(content)}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 保存资源文件失败({filename}): {e}")
            return {"asset_save_error": str(e)}

    def text_to_speech_demo(self, text: str, provider: str = DEFAULT_PROVIDER_REF) -> Dict[str, Any]:
        """演示 ILLMService.text_to_speech（阻塞调用，经后台任务执行）

        与 generate_image_demo 同模式：工作线程执行，完成事件后由 UI 经
        get_last_audio_result 拉取聚合结果（音频字节经 save_asset 落盘）。
        """
        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=TTS_TASK_NAME,
                func=self._run_text_to_speech, args=(text, provider),
                callback=self._on_tts_task_done,
            )
            return {"success": True, "task_id": task_id, "message": "语音合成已发起（后台任务执行）"}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 发起语音合成失败(provider={provider}): {e}")
            return {"success": False, "error": str(e)}

    def get_last_audio_result(self) -> Dict[str, Any]:
        """返回最近一次语音合成的聚合结果（供 UI 在完成事件后拉取展示）"""
        return {"success": True, "result": self._last_audio_result}

    def _run_text_to_speech(self, text: str, provider: str) -> Dict[str, Any]:
        """在工作线程执行 text_to_speech，返回聚合结果（音频字节经 save_asset 落盘）"""
        audio = self.llm.text_to_speech(text, provider=provider)
        result = self._build_audio_result(audio)
        self._last_audio_result = result
        return result

    def _build_audio_result(self, audio: AudioResult) -> Dict[str, Any]:
        """汇总 AudioResult 为展示用字典；audio_data 字节落盘为资源文件并返回路径"""
        result: Dict[str, Any] = {
            "success": True,
            "model": audio.model,
            "provider": audio.provider,
            "url": audio.url,
            "duration_seconds": audio.duration_seconds,
            "has_audio_data": audio.audio_data is not None,
        }
        if audio.audio_data is not None:
            result.update(self._save_bytes_asset(audio.audio_data, AUDIO_ASSET_FILENAME))
        return result

    def _on_image_task_done(self, task_id: str, status, result, error) -> None:
        """图片生成任务完成回调（工作线程）：经 notifier 上抛完成/失败事件"""
        try:
            if error:
                self._notify_event(f"{IMAGE_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 图片生成任务失败({task_id}): {error}")
                return
            self._notify_event(IMAGE_DONE_EVENT)
            self.logger.info(get_name(), f"[{self.plugin_id}] 图片生成任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 图片生成完成回调处理失败: {e}")

    def _on_tts_task_done(self, task_id: str, status, result, error) -> None:
        """语音合成任务完成回调（工作线程）：经 notifier 上抛完成/失败事件"""
        try:
            if error:
                self._notify_event(f"{TTS_ERROR_PREFIX}{error}")
                self.logger.error(get_name(), f"[{self.plugin_id}] 语音合成任务失败({task_id}): {error}")
                return
            self._notify_event(TTS_DONE_EVENT)
            self.logger.info(get_name(), f"[{self.plugin_id}] 语音合成任务完成({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 语音合成完成回调处理失败: {e}")

    # ------------------------------------------------------------------
    #  用量统计与 Provider 校验演示
    # ------------------------------------------------------------------

    def get_usage_stats_demo(self, conversation_id: Optional[str] = None) -> Dict[str, Any]:
        """演示 ILLMService.get_usage_stats（同步快速调用，直接返回统计字段）"""
        try:
            stats = self.llm.get_usage_stats(conversation_id)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 获取用量统计失败({conversation_id}): {e}")
            return {"success": False, "error": str(e)}
        if stats is None:
            return {"success": False, "error": f"会话不存在: {conversation_id}"}
        return {
            "success": True,
            "conversation_id": conversation_id,
            "stats": self._usage_stats_to_dict(stats),
        }

    @staticmethod
    def _usage_stats_to_dict(stats: UsageStats) -> Dict[str, Any]:
        """将 UsageStats 转换为展示用字典（token / 费用 / 请求数 / 分 Provider 费用）"""
        return {
            "total_input_tokens": stats.total_input_tokens,
            "total_output_tokens": stats.total_output_tokens,
            "total_tokens": stats.total_tokens,
            "total_cost": stats.total_cost,
            "request_count": stats.request_count,
            "by_provider": stats.by_provider,
        }

    def validate_provider_demo(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """演示 ILLMService.validate_provider；provider 为空时取默认 chat 实例"""
        target = provider or self.llm.get_default_provider_id(feature="chat")
        if not target:
            return {"success": False, "error": "未指定 Provider 且无可用默认实例"}
        try:
            valid, message = self.llm.validate_provider(target)
            return {"success": True, "provider": target, "valid": valid, "message": message}
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 校验 Provider 失败({target}): {e}")
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  卸载清理
    # ------------------------------------------------------------------

    def cleanup(self) -> None:
        """卸载清理：注销演示工具并删除本插件创建的全部会话（逐项容错）"""
        self._cleanup_demo_tools()
        for conversation_id in list(self._conversation_ids):
            self._delete_one_conversation(conversation_id)
        self._conversation_ids.clear()

    def _cleanup_demo_tools(self) -> None:
        """注销共享注册表中的演示工具，失败仅记日志不中断其余清理"""
        try:
            registry = self.llm.get_shared_tool_registry()
            for name in DEMO_TOOL_HANDLERS:
                registry.unregister(name)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 卸载清理：注销演示工具失败: {e}")

    def _delete_one_conversation(self, conversation_id: str) -> None:
        """删除单个会话，失败仅记日志不中断其余清理"""
        try:
            self.llm.delete_conversation(conversation_id)
        except Exception as e:
            self.logger.error(get_name(), f"[{self.plugin_id}] 卸载清理：删除会话失败({conversation_id}): {e}")
