# -*- coding: utf-8 -*-
"""LLM 演示 Tab。

演示 Provider 列表、模型列表、聊天（含流式）、嵌入调用、会话管理、
多模态（图片生成/语音合成）与用量统计/Provider 校验。
流式片段经服务 notifier 上抛（工作线程），一律 run_in_ui_thread 封送后刷新。
槽函数仅取输入、调用 LLMDemoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QListWidgetItem, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, ListWidget, Message, TextArea
from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab
from .llm_tab_groups import LLMMediaStatsGroupsMixin
from ...function.services.llm_service import (
    CONV_ERROR_PREFIX,
    CONV_REPLY_PREFIX,
    CONV_STREAM_CHUNK_PREFIX,
    CONV_STREAM_DONE_EVENT,
    CONV_STREAM_ERROR_PREFIX,
    STREAM_CHUNK_PREFIX,
    STREAM_DONE_EVENT,
    STREAM_ERROR_PREFIX,
    TOOL_DONE_EVENT,
    TOOL_ERROR_PREFIX,
)

# 会话列表中会话 id 的展示长度（完整 id 存于 UserRole）
CONV_ID_DISPLAY_LEN = 8

# 工具对话演示的默认输入消息（触发两个演示工具）
TOOL_DEMO_DEFAULT_MESSAGE = "现在几点了？帮我算一下 12*(3+4)"


class LLMTab(LLMMediaStatsGroupsMixin, BaseTab):
    """LLM 演示 Tab

    职责：构建 LLM 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    多模态与统计校验分组由 LLMMediaStatsGroupsMixin 提供（体量拆分）。
    """

    def __init__(self, llm_service, display_result: Callable, append_log: Callable):
        """初始化 LLM 演示 Tab

        参数:
            llm_service: LLMDemoService 实例（LLM 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
        self.llm_service = llm_service
        # 流式回调在工作线程触发，经 run_in_ui_thread 封送到 UI 线程刷新界面
        self.llm_service.set_event_notifier(self._on_stream_notify)

    def _on_stream_notify(self, message: str):
        """服务事件通知（工作线程）：按事件类型封送到 UI 线程分发处理"""
        run_in_ui_thread(self._dispatch_stream_event, message)

    def _dispatch_stream_event(self, message: str):
        """UI 线程分发服务事件：多模态 / 工具调用 / 会话演示 / 聊天流式分别处理"""
        if self._dispatch_multimodal_event(message):
            return
        if self._dispatch_tool_event(message):
            return
        if self._dispatch_conversation_event(message):
            return
        self._dispatch_chat_stream_event(message)

    def _dispatch_tool_event(self, message: str) -> bool:
        """UI 线程分发工具调用事件；命中工具协议返回 True，否则返回 False"""
        if message == TOOL_DONE_EVENT:
            self._show_tool_chat_result()
            return True
        if message.startswith(TOOL_ERROR_PREFIX):
            error = message[len(TOOL_ERROR_PREFIX):]
            self._display_result("工具对话失败", error, is_error=True)
            return True
        return False

    def _dispatch_chat_stream_event(self, message: str):
        """UI 线程分发聊天流式事件：片段增量刷新 / 完成展示 / 失败提示"""
        if message.startswith(STREAM_CHUNK_PREFIX):
            chunk = message[len(STREAM_CHUNK_PREFIX):]
            self.chat_result_text.insertPlainText(chunk)
            return
        if message == STREAM_DONE_EVENT:
            self._show_stream_result()
            return
        if message.startswith(STREAM_ERROR_PREFIX):
            error = message[len(STREAM_ERROR_PREFIX):]
            self._display_result("流式聊天失败", error, is_error=True)
            self.chat_result_text.setPlainText(f"错误: {error}")
            return
        self._log(f"流式事件: {message}")

    def _dispatch_conversation_event(self, message: str) -> bool:
        """UI 线程分发会话演示事件；命中会话协议返回 True，否则返回 False"""
        if message.startswith(CONV_STREAM_CHUNK_PREFIX):
            chunk = message[len(CONV_STREAM_CHUNK_PREFIX):]
            self.conv_result_text.insertPlainText(chunk)
            return True
        if message == CONV_STREAM_DONE_EVENT:
            self._show_conversation_stream_result()
            return True
        if message.startswith(CONV_STREAM_ERROR_PREFIX):
            self._show_conversation_error("会话流式发送失败", message[len(CONV_STREAM_ERROR_PREFIX):])
            return True
        if message.startswith(CONV_REPLY_PREFIX):
            reply = message[len(CONV_REPLY_PREFIX):]
            self.conv_result_text.setPlainText(reply)
            self._display_result("会话回复", reply)
            return True
        if message.startswith(CONV_ERROR_PREFIX):
            self._show_conversation_error("会话消息失败", message[len(CONV_ERROR_PREFIX):])
            return True
        return False

    def _show_conversation_error(self, title: str, error: str):
        """统一展示会话演示失败：结果面板 + 会话回复区"""
        self._display_result(title, error, is_error=True)
        self.conv_result_text.setPlainText(f"错误: {error}")

    def _show_conversation_stream_result(self):
        """会话流式完成事件后拉取服务聚合结果，在结果面板展示完整响应"""
        result = self.llm_service.get_last_conversation_stream_result().get("result") or {}
        content = (
            f"会话: {result.get('conversation_id', 'unknown')}\n"
            f"片段数: {result.get('chunk_count', 0)}\n\n"
            f"{result.get('response', '')}"
        )
        self._display_result("会话流式响应", content)

    def _show_stream_result(self):
        """完成事件后拉取服务聚合结果，在结果面板展示完整响应"""
        result = self.llm_service.get_last_stream_result().get("result") or {}
        usage = result.get("usage") or {}
        content = (
            f"模型: {result.get('model', 'unknown')}\n"
            f"Provider: {result.get('provider', 'unknown')}\n"
            f"片段数: {result.get('chunk_count', 0)}  Tokens: {usage.get('total_tokens', 'N/A')}\n\n"
            f"{result.get('response', '')}"
        )
        self._display_result("流式聊天响应", content)

    def _show_tool_chat_result(self):
        """工具对话完成事件后拉取服务聚合结果，在结果面板展示最终回复与调用明细"""
        result = self.llm_service.get_last_tool_chat_result().get("result") or {}
        content = (
            f"工具调用轮次: {result.get('turn_count', 0)}\n\n"
            f"{self._format_tool_results(result.get('tool_results', []))}"
            f"\n最终回复:\n{result.get('final_text', '')}"
        )
        self._display_result("工具对话响应", content)

    @staticmethod
    def _format_tool_results(tool_results: list) -> str:
        """把各轮工具调用明细格式化为展示文本（无调用时返回空串）"""
        lines = []
        for item in tool_results:
            detail = item.get("error") or item.get("result", "")
            lines.append(f"[{item.get('tool_name', '?')}]({item.get('arguments', {})}) -> {detail}")
        return "工具调用明细:\n" + "\n".join(lines) + "\n" if lines else ""

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 LLM Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_llm_provider_group())
        layout.addWidget(self._build_llm_chat_group())
        layout.addWidget(self._build_llm_conversation_group())
        layout.addWidget(self._build_llm_tool_group())
        layout.addWidget(self._build_llm_embed_group())
        layout.addWidget(self._build_llm_multimodal_group())
        layout.addWidget(self._build_llm_stats_group())
        layout.addStretch()
        return scroll

    def _build_llm_provider_group(self) -> QGroupBox:
        group = QGroupBox("Provider 信息")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_providers_btn = Button("获取 Provider 列表", variant="primary")
        self.get_providers_btn.clicked.connect(self._on_get_providers)
        layout.addWidget(self.get_providers_btn)

        self.providers_list = ListWidget()
        self.providers_list.setMaximumHeight(80)
        layout.addWidget(self.providers_list)

        self.get_models_btn = Button("获取模型列表", variant="primary")
        self.get_models_btn.clicked.connect(self._on_get_models)
        layout.addWidget(self.get_models_btn)

        self.models_list = ListWidget()
        self.models_list.setMaximumHeight(80)
        layout.addWidget(self.models_list)

        group.setLayout(layout)
        return group

    def _build_llm_chat_group(self) -> QGroupBox:
        group = QGroupBox("聊天测试")
        form = QFormLayout()
        form.setSpacing(6)

        self.chat_message_input = LineEdit(text="你好，请介绍一下自己")
        form.addRow("消息:", self.chat_message_input)

        self.chat_btn = Button("发送聊天", variant="primary")
        self.chat_btn.clicked.connect(self._on_send_chat)
        form.addRow("", self.chat_btn)

        self.chat_stream_btn = Button("流式发送", variant="primary")
        self.chat_stream_btn.clicked.connect(self._on_send_chat_stream)
        form.addRow("", self.chat_stream_btn)

        self.chat_result_text = TextArea()
        self.chat_result_text.setReadOnly(True)
        self.chat_result_text.setMaximumHeight(80)
        form.addRow("结果:", self.chat_result_text)

        group.setLayout(form)
        return group

    def _build_llm_conversation_group(self) -> QGroupBox:
        """构建「会话管理」分组（创建/列表/发送/详情/删除）"""
        group = QGroupBox("会话管理")
        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.addLayout(self._build_conv_create_form())
        layout.addLayout(self._build_conv_list_row())
        layout.addLayout(self._build_conv_send_form())
        group.setLayout(layout)
        return group

    def _build_conv_create_form(self) -> QFormLayout:
        """构建会话创建子块：系统提示词输入 + 创建按钮"""
        form = QFormLayout()
        form.setSpacing(6)
        self.conv_system_prompt_input = LineEdit(placeholder="系统提示词（可留空）")
        form.addRow("系统提示词:", self.conv_system_prompt_input)
        self.conv_create_btn = Button("创建会话", variant="primary")
        self.conv_create_btn.clicked.connect(self._on_create_conversation)
        form.addRow("", self.conv_create_btn)
        return form

    def _build_conv_list_row(self) -> QHBoxLayout:
        """构建会话列表子块：列表（conversation_id 存 UserRole）+ 操作按钮列"""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.conv_list = ListWidget()
        self.conv_list.setMaximumHeight(100)
        row.addWidget(self.conv_list, stretch=1)
        row.addLayout(self._build_conv_buttons_column())
        return row

    def _build_conv_buttons_column(self) -> QVBoxLayout:
        """构建会话操作按钮列：刷新 / 查看详情 / 删除"""
        column = QVBoxLayout()
        column.setSpacing(6)
        self.conv_refresh_btn = Button("刷新会话列表")
        self.conv_refresh_btn.clicked.connect(self._on_refresh_conversations)
        column.addWidget(self.conv_refresh_btn)
        self.conv_detail_btn = Button("查看详情")
        self.conv_detail_btn.clicked.connect(self._on_show_conversation_detail)
        column.addWidget(self.conv_detail_btn)
        self.conv_delete_btn = Button("删除会话", variant="danger")
        self.conv_delete_btn.clicked.connect(self._on_delete_conversation)
        column.addWidget(self.conv_delete_btn)
        column.addStretch()
        return column

    def _build_conv_send_form(self) -> QFormLayout:
        """构建会话消息发送子块：消息输入 + 发送/流式发送 + 回复区"""
        form = QFormLayout()
        form.setSpacing(6)
        self.conv_message_input = LineEdit(placeholder="发送给选中会话的消息")
        form.addRow("消息:", self.conv_message_input)
        send_row = QHBoxLayout()
        send_row.setSpacing(8)
        self.conv_send_btn = Button("发送", variant="primary")
        self.conv_send_btn.clicked.connect(self._on_send_conversation)
        send_row.addWidget(self.conv_send_btn)
        self.conv_stream_btn = Button("流式发送", variant="primary")
        self.conv_stream_btn.clicked.connect(self._on_stream_conversation)
        send_row.addWidget(self.conv_stream_btn)
        form.addRow("", send_row)
        self.conv_result_text = TextArea()
        self.conv_result_text.setReadOnly(True)
        self.conv_result_text.setMaximumHeight(100)
        form.addRow("回复:", self.conv_result_text)
        return form

    def _build_llm_tool_group(self) -> QGroupBox:
        """构建「工具调用」分组（注册/注销/查看工具 + 工具对话）"""
        group = QGroupBox("工具调用")
        form = QFormLayout()
        form.setSpacing(6)
        form.addRow("", self._build_tool_buttons_row())
        self.tool_message_input = LineEdit(text=TOOL_DEMO_DEFAULT_MESSAGE)
        form.addRow("消息:", self.tool_message_input)
        self.tool_chat_btn = Button("工具对话", variant="primary")
        self.tool_chat_btn.clicked.connect(self._on_tool_chat)
        form.addRow("", self.tool_chat_btn)
        group.setLayout(form)
        return group

    def _build_tool_buttons_row(self) -> QHBoxLayout:
        """构建工具注册表操作按钮行：注册 / 注销 / 查看已注册工具"""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.tool_register_btn = Button("注册演示工具")
        self.tool_register_btn.clicked.connect(self._on_register_tools)
        row.addWidget(self.tool_register_btn)
        self.tool_unregister_btn = Button("注销演示工具", variant="danger")
        self.tool_unregister_btn.clicked.connect(self._on_unregister_tools)
        row.addWidget(self.tool_unregister_btn)
        self.tool_list_btn = Button("查看已注册工具")
        self.tool_list_btn.clicked.connect(self._on_list_tools)
        row.addWidget(self.tool_list_btn)
        return row

    def _build_llm_embed_group(self) -> QGroupBox:
        group = QGroupBox("嵌入测试")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.embed_text_input = LineEdit(text="Hello world")
        row.addWidget(self.embed_text_input)

        self.embed_btn = Button("发送嵌入", variant="primary")
        self.embed_btn.clicked.connect(self._on_send_embed)
        row.addWidget(self.embed_btn)

        group.setLayout(row)
        return group

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_get_providers(self):
        result = self.llm_service.get_providers()
        self._log(f"获取Provider: {result}")

        self.providers_list.clear()
        if result.get("success"):
            for p in result.get("providers", []):
                self.providers_list.addItem(p)
            self._display_result("Provider 列表", "\n".join(result.get("providers", [])))
        else:
            self.providers_list.addItem(f"错误: {result.get('error')}")
            self._display_result("获取 Provider 失败", result.get("error", ""), is_error=True)

    def _on_get_models(self):
        result = self.llm_service.get_models()
        self._log(f"获取模型: {result}")

        self.models_list.clear()
        if result.get("success"):
            lines = self._collect_model_lines(result.get("models", {}))
            self._display_result("模型列表", "\n".join(lines))
        else:
            self.models_list.addItem(f"错误: {result.get('error')}")
            self._display_result("获取模型失败", result.get("error", ""), is_error=True)

    def _collect_model_lines(self, models) -> list:
        """收集模型展示行并填充模型列表（服务层统一返回 List[dict]）"""
        lines = []
        for m in models:
            name = m.get("name", m.get("id", "unknown"))
            lines.append(name)
            self.models_list.addItem(name)
        return lines

    def _on_send_chat(self):
        message = self.chat_message_input.text()
        result = self.llm_service.send_chat(message)
        self._log(f"聊天结果: {result}")

        if result.get("success"):
            content = (
                f"模型: {result.get('model', 'unknown')}\n"
                f"Provider: {result.get('provider', 'unknown')}\n\n"
                f"{result.get('response', '')}"
            )
            self._display_result("聊天响应", content)
            self.chat_result_text.setPlainText(result.get("response", ""))
        else:
            self._display_result("聊天失败", result.get("error", ""), is_error=True)
            self.chat_result_text.setPlainText(f"错误: {result.get('error')}")

    def _on_send_chat_stream(self):
        message = self.chat_message_input.text()
        self.chat_result_text.clear()
        result = self.llm_service.send_chat_stream(message)
        self._log(f"流式聊天: {result}")
        if not result.get("success"):
            self._display_result("流式聊天发起失败", result.get("error", ""), is_error=True)

    # ------------------------------------------------------------------
    #  会话管理事件
    # ------------------------------------------------------------------

    def _on_create_conversation(self):
        system_prompt = self.conv_system_prompt_input.text().strip() or None
        result = self.llm_service.create_conversation_demo(system_prompt)
        self._show_conv_op_result("创建会话", result)
        self._on_refresh_conversations()

    def _on_refresh_conversations(self):
        result = self.llm_service.list_conversations_demo()
        self._log(f"会话列表: {result}")
        self._populate_conversation_list(result)

    def _on_send_conversation(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        self.conv_result_text.clear()
        self._request_conversation_send(conversation_id, stream=False)

    def _on_stream_conversation(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        self.conv_result_text.clear()
        self._request_conversation_send(conversation_id, stream=True)

    def _on_show_conversation_detail(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        result = self.llm_service.get_conversation_demo(conversation_id)
        self._show_conv_detail_result(result)

    def _on_delete_conversation(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        result = self.llm_service.delete_conversation_demo(conversation_id)
        self._show_conv_op_result("删除会话", result)
        self._on_refresh_conversations()

    def _request_conversation_send(self, conversation_id: str, stream: bool):
        """按模式调用服务发起会话消息（均为后台任务，结果经 notifier 上抛）"""
        content = self.conv_message_input.text()
        if stream:
            result = self.llm_service.stream_conversation_message(conversation_id, content)
        else:
            result = self.llm_service.send_conversation_message(conversation_id, content)
        self._log(f"会话消息发起: {result}")
        if not result.get("success"):
            self._show_conversation_error("会话消息发起失败", result.get("error", ""))

    def _selected_conversation_id(self) -> Optional[str]:
        """取当前会话列表选中项的 conversation_id；无选中时弹提示"""
        item = self.conv_list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        Message.warning(self._message_parent, "请先在会话列表中选中一个会话")
        return None

    def _populate_conversation_list(self, result: dict):
        """填充会话列表，conversation_id 存入 item 的 UserRole 数据"""
        self.conv_list.clear()
        if not result.get("success"):
            self.conv_list.addItem(f"错误: {result.get('error')}")
            self._display_result("获取会话列表失败", result.get("error", ""), is_error=True)
            return
        for conv in result.get("conversations", []):
            self._add_conversation_item(conv)

    def _add_conversation_item(self, conv: dict):
        """向会话列表添加一行，并把 conversation_id 绑定到 UserRole"""
        short_id = conv["id"][:CONV_ID_DISPLAY_LEN]
        text = f"{short_id} [{conv['provider']}/{conv['model']}] 消息数:{conv['message_count']}"
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, conv["id"])
        self.conv_list.addItem(item)

    def _show_conv_op_result(self, title: str, result: dict):
        """统一展示会话操作结果（成功/失败）"""
        self._log(f"{title}: {result}")
        if result.get("success"):
            self._display_result(f"{title}成功", str(result))
            return
        self._display_result(f"{title}失败", result.get("error", ""), is_error=True)

    def _show_conv_detail_result(self, result: dict):
        """展示会话详情（含消息历史，JSON 格式化）"""
        self._log(f"会话详情: {result}")
        if not result.get("success"):
            self._display_result("查看会话详情失败", result.get("error", ""), is_error=True)
            return
        content = json.dumps(result.get("conversation", {}), ensure_ascii=False, indent=2)
        self._display_result("会话详情", content)

    # ------------------------------------------------------------------
    #  工具调用事件
    # ------------------------------------------------------------------

    def _on_register_tools(self):
        result = self.llm_service.register_demo_tools()
        self._log(f"注册演示工具: {result}")
        if result.get("success"):
            self._display_result("注册演示工具", "\n".join(result.get("registered", [])))
        else:
            self._display_result("注册演示工具失败", result.get("error", ""), is_error=True)

    def _on_unregister_tools(self):
        result = self.llm_service.unregister_demo_tools()
        self._log(f"注销演示工具: {result}")
        self._show_tool_op_result("注销演示工具", result, "unregistered")

    def _on_list_tools(self):
        result = self.llm_service.list_registered_tools()
        self._log(f"已注册工具: {result}")
        if not result.get("success"):
            self._display_result("查看已注册工具失败", result.get("error", ""), is_error=True)
            return
        descriptions = result.get("tool_descriptions", {})
        lines = [f"{name}: {desc}" for name, desc in descriptions.items()]
        self._display_result("共享 ToolRegistry 已注册工具", "\n".join(lines))

    def _on_tool_chat(self):
        message = self.tool_message_input.text()
        result = self.llm_service.chat_with_tools_demo(message)
        self._log(f"工具对话发起: {result}")
        if not result.get("success"):
            self._display_result("工具对话发起失败", result.get("error", ""), is_error=True)

    def _show_tool_op_result(self, title: str, result: dict, key: str):
        """统一展示工具注册表操作结果（成功列名 / 失败弹错误）"""
        if result.get("success"):
            self._display_result(title, "\n".join(result.get(key, [])) or "（无）")
            return
        self._display_result(f"{title}失败", result.get("error", ""), is_error=True)

    def _on_send_embed(self):
        text = self.embed_text_input.text()
        result = self.llm_service.send_embedding(text)
        self._log(f"嵌入结果: {result}")
        if result.get("success"):
            self._display_result(
                "嵌入成功",
                f"维度: {result.get('embedding_size', 0)}\nProvider: {result.get('provider', 'unknown')}"
            )
        else:
            self._display_result("嵌入失败", result.get("error", ""), is_error=True)
        Message.info(self._message_parent, str(result))
