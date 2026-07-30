# -*- coding: utf-8 -*-
"""LLM 演示 Tab。

演示 Provider 列表、模型列表、聊天（含流式）与嵌入调用。
流式片段经服务 notifier 上抛（工作线程），一律 run_in_ui_thread 封送后刷新。
槽函数仅取输入、调用 LLMDemoService、显示结果，业务逻辑在服务层。
"""

from typing import Callable

from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, ListWidget, Message, TextArea
from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab
from ...function.services.llm_service import (
    STREAM_CHUNK_PREFIX,
    STREAM_DONE_EVENT,
    STREAM_ERROR_PREFIX,
)


class LLMTab(BaseTab):
    """LLM 演示 Tab

    职责：构建 LLM 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
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
        """流式事件通知（工作线程）：按事件类型封送到 UI 线程分发处理"""
        run_in_ui_thread(self._dispatch_stream_event, message)

    def _dispatch_stream_event(self, message: str):
        """UI 线程分发流式事件：片段增量刷新 / 完成展示 / 失败提示"""
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

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 LLM Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_llm_provider_group())
        layout.addWidget(self._build_llm_chat_group())
        layout.addWidget(self._build_llm_embed_group())
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
