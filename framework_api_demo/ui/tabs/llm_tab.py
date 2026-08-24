# -*- coding: utf-8 -*-
"""LLM 演示 Tab。

演示 Provider 列表、模型列表、聊天（含流式）、嵌入调用、会话管理、
多模态（图片生成/语音合成）与用量统计/Provider 校验。
流式片段经服务 notifier 上抛（工作线程），一律 run_in_ui_thread 封送后刷新。
槽函数仅取输入、调用 LLMDemoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

import json
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QListWidgetItem, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, ListWidget, Message, TextArea

from core.interfaces import ILocalizationFacade
from utils.thread_utils import run_in_ui_thread

from ..metrics import (
    CHAT_RESULT_MAX_HEIGHT, CONV_LIST_MAX_HEIGHT, CONV_RESULT_MAX_HEIGHT,
    FORM_SPACING, GROUP_SPACING, LIST_BOX_MAX_HEIGHT, ROW_SPACING,
)
from .base_tab import BaseTab
from .llm_tab_groups import LLMMediaStatsGroupsMixin
from ...function.services.llm_service import (
    CHAT_DONE_EVENT,
    CHAT_ERROR_PREFIX,
    CONV_ERROR_PREFIX,
    CONV_REPLY_PREFIX,
    CONV_STREAM_CHUNK_PREFIX,
    CONV_STREAM_DONE_EVENT,
    CONV_STREAM_ERROR_PREFIX,
    EMBED_DONE_EVENT,
    EMBED_ERROR_PREFIX,
    STREAM_CHUNK_PREFIX,
    STREAM_DONE_EVENT,
    STREAM_ERROR_PREFIX,
    TOOL_DONE_EVENT,
    TOOL_ERROR_PREFIX,
    TOOL_STREAM_CHUNK_PREFIX,
    TOOL_STREAM_DONE_EVENT,
    TOOL_STREAM_ERROR_PREFIX,
)

# 会话列表中会话 id 的展示长度（完整 id 存于 UserRole）
CONV_ID_DISPLAY_LEN = 8

# 结果面板展示 JSON 的缩进宽度
_JSON_INDENT = 2


class LLMTab(LLMMediaStatsGroupsMixin, BaseTab):
    """LLM 演示 Tab

    职责：构建 LLM 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    多模态与统计校验分组由 LLMMediaStatsGroupsMixin 提供（体量拆分）。
    """

    def __init__(self, llm_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化 LLM 演示 Tab

        参数:
            llm_service: LLMDemoService 实例（LLM 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
        self.llm_service = llm_service
        # 流式回调在工作线程触发，经 run_in_ui_thread 封送到 UI 线程刷新界面
        self.llm_service.set_event_notifier(self._on_stream_notify)

    def _on_stream_notify(self, message: str):
        """服务事件通知（工作线程）：按事件类型封送到 UI 线程分发处理"""
        run_in_ui_thread(self._dispatch_stream_event, message)

    # ------------------------------------------------------------------
    #  请求防重入（发起期间禁用触发按钮，结果/错误事件到达后恢复）
    # ------------------------------------------------------------------

    def _begin_llm_request(self, button: Button) -> None:
        """请求发起前置：禁用触发按钮，防止后台请求进行中重复提交"""
        button.setEnabled(False)

    def _end_llm_request(self, button: Button) -> None:
        """请求结束（完成/失败事件到达，或发起即失败）：恢复触发按钮可用"""
        button.setEnabled(True)

    # ------------------------------------------------------------------
    #  notifier 事件分发
    # ------------------------------------------------------------------

    def _dispatch_stream_event(self, message: str):
        """UI 线程分发服务事件：聊天/嵌入 / 多模态 / 工具调用 / 会话演示 / 聊天流式分别处理"""
        if self._dispatch_chat_result_event(message):
            return
        if self._dispatch_multimodal_event(message):
            return
        if self._dispatch_tool_event(message):
            return
        if self._dispatch_conversation_event(message):
            return
        self._dispatch_chat_stream_event(message)

    def _dispatch_chat_result_event(self, message: str) -> bool:
        """UI 线程分发聊天/嵌入完成事件；命中对应协议返回 True，否则返回 False"""
        if message == CHAT_DONE_EVENT:
            self._end_llm_request(self.chat_btn)
            self._show_chat_result()
            return True
        if message.startswith(CHAT_ERROR_PREFIX):
            self._end_llm_request(self.chat_btn)
            self._show_chat_error(message[len(CHAT_ERROR_PREFIX):])
            return True
        if message == EMBED_DONE_EVENT:
            self._end_llm_request(self.embed_btn)
            self._show_embed_result()
            return True
        if message.startswith(EMBED_ERROR_PREFIX):
            self._end_llm_request(self.embed_btn)
            self._display_result(self._tr("tab_llm", "title.embed_fail"),
                                 message[len(EMBED_ERROR_PREFIX):], is_error=True)
            return True
        return False

    def _show_chat_result(self):
        """聊天完成事件后拉取服务聚合结果展示（复用成功展示分支）"""
        result = self.llm_service.get_last_chat_result().get("result") or {}
        self._show_chat_success(result)

    def _show_chat_error(self, error: str):
        """聊天失败事件：结果面板弹错误，聊天区写错误前缀"""
        self._display_result(self._tr("tab_llm", "title.chat_fail"),
                             error, is_error=True)
        self.chat_result_text.setPlainText(
            self._tr("common", "error.prefix", error=error))

    def _show_embed_result(self):
        """嵌入完成事件后拉取服务聚合结果展示"""
        result = self.llm_service.get_last_embed_result().get("result") or {}
        self._display_result(self._tr("tab_llm", "title.embed_ok"), self._tr(
            "tab_llm", "msg.embed_result",
            size=result.get("embedding_size", 0),
            provider=result.get("provider", "unknown")))

    def _dispatch_tool_event(self, message: str) -> bool:
        """UI 线程分发工具调用事件；命中工具协议返回 True，否则返回 False"""
        if self._dispatch_tool_stream_event(message):
            return True
        if message == TOOL_DONE_EVENT:
            self._end_llm_request(self.tool_chat_btn)
            self._show_tool_chat_result()
            return True
        if message.startswith(TOOL_ERROR_PREFIX):
            self._end_llm_request(self.tool_chat_btn)
            error = message[len(TOOL_ERROR_PREFIX):]
            self._display_result(self._tr("tab_llm", "title.tool_chat_fail"),
                                 error, is_error=True)
            return True
        return False

    def _dispatch_tool_stream_event(self, message: str) -> bool:
        """UI 线程分发工具流式对话事件：片段增量刷新 / 完成展示 / 失败提示"""
        if message.startswith(TOOL_STREAM_CHUNK_PREFIX):
            self.tool_result_text.insertPlainText(message[len(TOOL_STREAM_CHUNK_PREFIX):])
            return True
        if message == TOOL_STREAM_DONE_EVENT:
            self._end_llm_request(self.tool_stream_btn)
            self._show_tool_stream_result()
            return True
        if message.startswith(TOOL_STREAM_ERROR_PREFIX):
            self._end_llm_request(self.tool_stream_btn)
            error = message[len(TOOL_STREAM_ERROR_PREFIX):]
            self._display_result(self._tr("tab_llm", "title.tool_stream_fail"),
                                 error, is_error=True)
            self.tool_result_text.setPlainText(
                self._tr("common", "error.prefix", error=error))
            return True
        return False

    def _show_tool_stream_result(self):
        """工具流式完成事件后拉取聚合结果，在结果面板展示（含片段数对照）"""
        result = self.llm_service.get_last_tool_stream_result().get("result") or {}
        content = self._tr("tab_llm", "msg.tool_stream_result",
                           turns=result.get("turn_count", 0),
                           chunks=result.get("chunk_count", 0),
                           final=result.get("final_text", ""))
        self._display_result(self._tr("tab_llm", "title.tool_stream_result"), content)

    def _dispatch_chat_stream_event(self, message: str):
        """UI 线程分发聊天流式事件：片段增量刷新 / 完成展示 / 失败提示"""
        if message.startswith(STREAM_CHUNK_PREFIX):
            self.chat_result_text.insertPlainText(message[len(STREAM_CHUNK_PREFIX):])
            return
        if message == STREAM_DONE_EVENT:
            self._end_llm_request(self.chat_stream_btn)
            self._show_stream_result()
            return
        if message.startswith(STREAM_ERROR_PREFIX):
            self._end_llm_request(self.chat_stream_btn)
            error = message[len(STREAM_ERROR_PREFIX):]
            self._display_result(self._tr("tab_llm", "title.stream_fail"),
                                 error, is_error=True)
            self.chat_result_text.setPlainText(
                self._tr("common", "error.prefix", error=error))
            return
        self._log(self._tr("tab_llm", "log.stream_event", message=message))

    def _dispatch_conversation_event(self, message: str) -> bool:
        """UI 线程分发会话演示事件；命中会话协议返回 True，否则返回 False"""
        if message.startswith(CONV_STREAM_CHUNK_PREFIX):
            self.conv_result_text.insertPlainText(message[len(CONV_STREAM_CHUNK_PREFIX):])
            return True
        if message == CONV_STREAM_DONE_EVENT:
            # 流式发送的两个入口按钮（普通/带图）都在此处恢复，幂等无害
            self._end_llm_request(self.conv_stream_btn)
            self._end_llm_request(self.conv_stream_img_btn)
            self._show_conversation_stream_result()
            return True
        if message.startswith(CONV_STREAM_ERROR_PREFIX):
            self._end_llm_request(self.conv_stream_btn)
            self._end_llm_request(self.conv_stream_img_btn)
            self._show_conversation_error("title.conv_stream_fail",
                                          message[len(CONV_STREAM_ERROR_PREFIX):])
            return True
        if message.startswith(CONV_REPLY_PREFIX):
            self._end_llm_request(self.conv_send_btn)
            self._show_conversation_reply(message[len(CONV_REPLY_PREFIX):])
            return True
        if message.startswith(CONV_ERROR_PREFIX):
            self._end_llm_request(self.conv_send_btn)
            self._show_conversation_error("title.conv_msg_fail",
                                          message[len(CONV_ERROR_PREFIX):])
            return True
        return False

    def _show_conversation_reply(self, reply: str):
        """会话非流式回复事件：会话回复区与结果面板同步展示"""
        self.conv_result_text.setPlainText(reply)
        self._display_result(self._tr("tab_llm", "title.conv_reply"), reply)

    # ------------------------------------------------------------------
    #  聚合结果展示
    # ------------------------------------------------------------------

    def _show_conversation_error(self, title_key: str, error: str):
        """统一展示会话演示失败：结果面板 + 会话回复区"""
        self._display_result(self._tr("tab_llm", title_key), error, is_error=True)
        self.conv_result_text.setPlainText(
            self._tr("common", "error.prefix", error=error))

    def _show_conversation_stream_result(self):
        """会话流式完成事件后拉取服务聚合结果，在结果面板展示完整响应"""
        result = self.llm_service.get_last_conversation_stream_result().get("result") or {}
        content = self._tr("tab_llm", "msg.conv_stream_result",
                           id=result.get("conversation_id", "unknown"),
                           chunks=result.get("chunk_count", 0),
                           response=result.get("response", ""))
        self._display_result(self._tr("tab_llm", "title.conv_stream_result"), content)

    def _show_stream_result(self):
        """完成事件后拉取服务聚合结果，在结果面板展示完整响应"""
        result = self.llm_service.get_last_stream_result().get("result") or {}
        usage = result.get("usage") or {}
        content = self._tr("tab_llm", "msg.stream_result",
                           model=result.get("model", "unknown"),
                           provider=result.get("provider", "unknown"),
                           chunks=result.get("chunk_count", 0),
                           tokens=usage.get("total_tokens", "N/A"),
                           response=result.get("response", ""))
        self._display_result(self._tr("tab_llm", "title.stream_result"), content)

    def _show_tool_chat_result(self):
        """工具对话完成事件后拉取服务聚合结果，在结果面板展示最终回复与调用明细"""
        result = self.llm_service.get_last_tool_chat_result().get("result") or {}
        content = self._tr("tab_llm", "msg.tool_chat_result",
                           turns=result.get("turn_count", 0),
                           details=self._format_tool_results(
                               result.get("tool_results", [])),
                           final=result.get("final_text", ""))
        self._display_result(self._tr("tab_llm", "title.tool_chat_result"), content)

    def _format_tool_results(self, tool_results: list) -> str:
        """把各轮工具调用明细格式化为展示文本（无调用时返回空串）"""
        lines = []
        for item in tool_results:
            detail = item.get("error") or item.get("result", "")
            lines.append(f"[{item.get('tool_name', '?')}]({item.get('arguments', {})})"
                         f" -> {detail}")
        if not lines:
            return ""
        return self._tr("tab_llm", "msg.tool_details", lines="\n".join(lines))

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

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_llm 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_llm", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_llm 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_llm", key, slot, variant=variant)

    def _make_tab_label(self, key: str):
        """创建本 Tab 表单标签（取 tab_llm 分组 label.* 键并登记绑定）"""
        return self._make_label("tab_llm", key)

    def _build_llm_provider_group(self) -> QGroupBox:
        group = self._make_group("group.provider")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.get_providers_btn = self._make_button(
            "btn.get_providers", self._on_get_providers, variant="primary")
        layout.addWidget(self.get_providers_btn)
        self.providers_list = self._make_list_box(layout)
        self.get_models_btn = self._make_button(
            "btn.get_models", self._on_get_models, variant="primary")
        layout.addWidget(self.get_models_btn)
        self.models_list = self._make_list_box(layout)
        group.setLayout(layout)
        return group

    @staticmethod
    def _make_list_box(layout: QVBoxLayout) -> ListWidget:
        """创建限高列表框并加入布局（Provider/模型列表共用）"""
        list_widget = ListWidget()
        list_widget.setMaximumHeight(LIST_BOX_MAX_HEIGHT)
        layout.addWidget(list_widget)
        return list_widget

    def _build_llm_chat_group(self) -> QGroupBox:
        group = self._make_group("group.chat")
        form = QFormLayout()
        form.setSpacing(FORM_SPACING)
        self.chat_message_input = LineEdit(
            text=self._tr("tab_llm", "default.chat_message"))
        form.addRow(self._make_tab_label("label.message"), self.chat_message_input)
        self.chat_btn = self._make_button("btn.send", self._on_send_chat,
                                          variant="primary")
        form.addRow("", self.chat_btn)
        self.chat_stream_btn = self._make_button("btn.stream", self._on_send_chat_stream,
                                                 variant="primary")
        form.addRow("", self.chat_stream_btn)
        self.chat_result_text = self._make_result_area(CHAT_RESULT_MAX_HEIGHT)
        form.addRow(self._make_label("common", "label.result"), self.chat_result_text)
        group.setLayout(form)
        return group

    @staticmethod
    def _make_result_area(max_height: int) -> TextArea:
        """创建只读结果展示区（限高）"""
        area = TextArea()
        area.setReadOnly(True)
        area.setMaximumHeight(max_height)
        return area

    def _build_llm_conversation_group(self) -> QGroupBox:
        """构建「会话管理」分组（创建/列表/发送/详情/删除）"""
        group = self._make_group("group.conversation")
        layout = QVBoxLayout()
        layout.setSpacing(FORM_SPACING)
        layout.addLayout(self._build_conv_create_form())
        layout.addLayout(self._build_conv_list_row())
        layout.addLayout(self._build_conv_send_form())
        group.setLayout(layout)
        return group

    def _build_conv_create_form(self) -> QFormLayout:
        """构建会话创建子块：系统提示词输入 + 创建按钮"""
        form = QFormLayout()
        form.setSpacing(FORM_SPACING)
        self.conv_system_prompt_input = self._make_placeholder_input(
            "placeholder.system_prompt")
        form.addRow(self._make_tab_label("label.system_prompt"),
                    self.conv_system_prompt_input)
        self.conv_create_btn = self._make_button(
            "btn.create_conv", self._on_create_conversation, variant="primary")
        form.addRow("", self.conv_create_btn)
        return form

    def _make_placeholder_input(self, key: str) -> LineEdit:
        """创建占位提示取词并登记重翻译绑定的输入框"""
        edit = LineEdit(placeholder=self._tr("tab_llm", key))
        self._bind(edit, "tab_llm", key, setter="setPlaceholderText")
        return edit

    def _build_conv_list_row(self) -> QHBoxLayout:
        """构建会话列表子块：列表（conversation_id 存 UserRole）+ 操作按钮列"""
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        self.conv_list = ListWidget()
        self.conv_list.setMaximumHeight(CONV_LIST_MAX_HEIGHT)
        row.addWidget(self.conv_list, stretch=1)
        row.addLayout(self._build_conv_buttons_column())
        return row

    def _build_conv_buttons_column(self) -> QVBoxLayout:
        """构建会话操作按钮列：刷新 / 查看详情 / 删除"""
        column = QVBoxLayout()
        column.setSpacing(FORM_SPACING)
        self.conv_refresh_btn = self._make_button("btn.refresh_conv",
                                                  self._on_refresh_conversations)
        column.addWidget(self.conv_refresh_btn)
        self.conv_detail_btn = self._make_button("btn.conv_detail",
                                                 self._on_show_conversation_detail)
        column.addWidget(self.conv_detail_btn)
        self.conv_delete_btn = self._make_button("btn.delete_conv",
                                                 self._on_delete_conversation,
                                                 variant="danger")
        column.addWidget(self.conv_delete_btn)
        column.addStretch()
        return column

    def _build_conv_send_form(self) -> QFormLayout:
        """构建会话消息发送子块：消息输入 + 发送/流式发送 + 回复区"""
        form = QFormLayout()
        form.setSpacing(FORM_SPACING)
        self.conv_message_input = self._make_placeholder_input("placeholder.conv_message")
        form.addRow(self._make_tab_label("label.message"), self.conv_message_input)
        form.addRow("", self._build_conv_send_buttons())
        self.conv_result_text = self._make_result_area(CONV_RESULT_MAX_HEIGHT)
        form.addRow(self._make_tab_label("label.reply"), self.conv_result_text)
        return form

    def _build_conv_send_buttons(self) -> QHBoxLayout:
        """构建会话发送按钮行：发送 / 流式发送 / 流式发送（带图，images 多模态演示）"""
        send_row = QHBoxLayout()
        send_row.setSpacing(ROW_SPACING)
        self.conv_send_btn = self._make_button("btn.send_msg", self._on_send_conversation,
                                               variant="primary")
        send_row.addWidget(self.conv_send_btn)
        self.conv_stream_btn = self._make_button("btn.stream", self._on_stream_conversation,
                                                 variant="primary")
        send_row.addWidget(self.conv_stream_btn)
        self.conv_stream_img_btn = self._make_button(
            "btn.stream_img", self._on_stream_conversation_with_image)
        send_row.addWidget(self.conv_stream_img_btn)
        return send_row

    def _build_llm_tool_group(self) -> QGroupBox:
        """构建「工具调用」分组（注册/注销/查看工具 + 工具对话/工具流式对话）"""
        group = self._make_group("group.tool")
        form = QFormLayout()
        form.setSpacing(FORM_SPACING)
        for row in self._build_tool_buttons_rows():
            form.addRow("", row)
        self.tool_message_input = LineEdit(
            text=self._tr("tab_llm", "default.tool_message"))
        form.addRow(self._make_tab_label("label.message"), self.tool_message_input)
        self.tool_chat_btn = self._make_button("btn.tool_chat", self._on_tool_chat,
                                               variant="primary")
        form.addRow("", self.tool_chat_btn)
        self.tool_stream_btn = self._make_button(
            "btn.tool_chat_stream", self._on_tool_chat_stream, variant="primary")
        form.addRow("", self.tool_stream_btn)
        self.tool_result_text = self._make_result_area(CHAT_RESULT_MAX_HEIGHT)
        form.addRow(self._make_label("common", "label.result"), self.tool_result_text)
        group.setLayout(form)
        return group

    def _build_tool_buttons_rows(self) -> list:
        """构建工具注册表操作按钮行（拆为两行，适配收窄后的面板宽度）"""
        manage_row = QHBoxLayout()
        manage_row.setSpacing(ROW_SPACING)
        self.tool_register_btn = self._make_button("btn.register_tools",
                                                   self._on_register_tools)
        manage_row.addWidget(self.tool_register_btn)
        self.tool_unregister_btn = self._make_button("btn.unregister_tools",
                                                     self._on_unregister_tools,
                                                     variant="danger")
        manage_row.addWidget(self.tool_unregister_btn)
        list_row = QHBoxLayout()
        self.tool_list_btn = self._make_button("btn.list_tools", self._on_list_tools)
        list_row.addWidget(self.tool_list_btn)
        list_row.addStretch()
        return [manage_row, list_row]

    def _build_llm_embed_group(self) -> QGroupBox:
        group = self._make_group("group.embed")
        row = QHBoxLayout()
        row.setSpacing(ROW_SPACING)
        self.embed_text_input = LineEdit(text=self._tr("tab_llm", "default.embed_text"))
        row.addWidget(self.embed_text_input)
        self.embed_btn = self._make_button("btn.embed", self._on_send_embed,
                                           variant="primary")
        row.addWidget(self.embed_btn)
        group.setLayout(row)
        return group

    # ------------------------------------------------------------------
    #  Provider / 聊天事件
    # ------------------------------------------------------------------

    def _on_get_providers(self):
        result = self.llm_service.get_providers()
        self._log(self._tr("tab_llm", "log.providers", result=result))
        self.providers_list.clear()
        if result.get("success"):
            for p in result.get("providers", []):
                self.providers_list.addItem(p)
            self._display_result(self._tr("tab_llm", "title.providers"),
                                 "\n".join(result.get("providers", [])))
        else:
            self._show_list_error(self.providers_list, "title.providers_fail", result)

    def _on_get_models(self):
        result = self.llm_service.get_models()
        self._log(self._tr("tab_llm", "log.models", result=result))
        self.models_list.clear()
        if result.get("success"):
            lines = self._collect_model_lines(result.get("models", {}))
            self._display_result(self._tr("tab_llm", "title.models"), "\n".join(lines))
        else:
            self._show_list_error(self.models_list, "title.models_fail", result)

    def _show_list_error(self, list_widget: ListWidget, title_key: str, result: dict):
        """列表型查询失败统一处理：列表写错误行 + 结果面板弹错误"""
        error = result.get("error", "")
        list_widget.addItem(self._tr("common", "error.prefix", error=error))
        self._display_result(self._tr("tab_llm", title_key), error, is_error=True)

    def _collect_model_lines(self, models) -> list:
        """收集模型展示行并填充模型列表（附 capability_label 本地化能力标签）"""
        lines = []
        for m in models:
            name = m.get("name", m.get("id", "unknown"))
            text = self._format_model_line(name, m.get("capabilities", []))
            lines.append(text)
            self.models_list.addItem(text)
        return lines

    def _format_model_line(self, name: str, capabilities: list) -> str:
        """格式化模型展示行：有能力标签时追加 [标签1/标签2]"""
        if not capabilities:
            return name
        return self._tr("tab_llm", "item.model", name=name,
                        capabilities="/".join(str(c) for c in capabilities))

    def _on_send_chat(self):
        """发起聊天（后台任务执行，完成/失败经 notifier 事件上抛；进行中禁用按钮防重入）"""
        message = self.chat_message_input.text()
        self._begin_llm_request(self.chat_btn)
        result = self.llm_service.send_chat(message)
        self._log(self._tr("tab_llm", "log.chat", result=result))
        if not result.get("success"):
            self._end_llm_request(self.chat_btn)
            self._show_chat_error(result.get("error", ""))

    def _show_chat_success(self, result: dict):
        """展示聊天成功结果：结果面板含模型信息，聊天区仅显示回复正文"""
        content = self._tr("tab_llm", "msg.chat_result",
                           model=result.get("model", "unknown"),
                           provider=result.get("provider", "unknown"),
                           response=result.get("response", ""))
        self._display_result(self._tr("tab_llm", "title.chat_result"), content)
        self.chat_result_text.setPlainText(result.get("response", ""))

    def _on_send_chat_stream(self):
        message = self.chat_message_input.text()
        self.chat_result_text.clear()
        self._begin_llm_request(self.chat_stream_btn)
        result = self.llm_service.send_chat_stream(message)
        self._log(self._tr("tab_llm", "log.stream", result=result))
        if not result.get("success"):
            self._end_llm_request(self.chat_stream_btn)
            self._display_result(self._tr("tab_llm", "title.stream_start_fail"),
                                 result.get("error", ""), is_error=True)

    # ------------------------------------------------------------------
    #  会话管理事件
    # ------------------------------------------------------------------

    def _on_create_conversation(self):
        system_prompt = self.conv_system_prompt_input.text().strip() or None
        result = self.llm_service.create_conversation_demo(system_prompt)
        self._show_conv_op_result("op.create_conv", result)
        self._on_refresh_conversations()

    def _on_refresh_conversations(self):
        result = self.llm_service.list_conversations_demo()
        self._log(self._tr("tab_llm", "log.conv_list", result=result))
        self._populate_conversation_list(result)

    def _on_send_conversation(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        self.conv_result_text.clear()
        self._request_conversation_send(conversation_id, self.conv_send_btn, stream=False)

    def _on_stream_conversation(self):
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        self.conv_result_text.clear()
        self._request_conversation_send(conversation_id, self.conv_stream_btn, stream=True)

    def _on_stream_conversation_with_image(self):
        """流式发送并附带演示图片（stream_send_message 的 images 多模态参数演示）"""
        conversation_id = self._selected_conversation_id()
        if conversation_id is None:
            return
        self.conv_result_text.clear()
        self._request_conversation_send(conversation_id, self.conv_stream_img_btn,
                                        stream=True, with_image=True)

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
        self._show_conv_op_result("op.delete_conv", result)
        self._on_refresh_conversations()

    def _request_conversation_send(self, conversation_id: str, button: Button,
                                   stream: bool, with_image: bool = False):
        """按模式调用服务发起会话消息（均为后台任务，结果经 notifier 上抛）

        参数:
            button: 触发按钮，请求进行中禁用防重入，结果/错误事件到达后恢复
        """
        content = self.conv_message_input.text()
        self._begin_llm_request(button)
        if stream:
            result = self.llm_service.stream_conversation_message(
                conversation_id, content, with_image=with_image)
        else:
            result = self.llm_service.send_conversation_message(conversation_id, content)
        self._log(self._tr("tab_llm", "log.conv_send", result=result))
        if not result.get("success"):
            self._end_llm_request(button)
            self._show_conversation_error("title.conv_start_fail",
                                          result.get("error", ""))

    def _selected_conversation_id(self) -> Optional[str]:
        """取当前会话列表选中项的 conversation_id；无选中时弹提示"""
        item = self.conv_list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        Message.warning(self._message_parent,
                        self._tr("tab_llm", "warn.select_conv"))
        return None

    def _populate_conversation_list(self, result: dict):
        """填充会话列表，conversation_id 存入 item 的 UserRole 数据"""
        self.conv_list.clear()
        if not result.get("success"):
            error = result.get("error", "")
            self.conv_list.addItem(self._tr("common", "error.prefix", error=error))
            self._display_result(self._tr("tab_llm", "title.conv_list_fail"),
                                 error, is_error=True)
            return
        for conv in result.get("conversations", []):
            self._add_conversation_item(conv)

    def _add_conversation_item(self, conv: dict):
        """向会话列表添加一行，并把 conversation_id 绑定到 UserRole"""
        short_id = conv["id"][:CONV_ID_DISPLAY_LEN]
        text = self._tr("tab_llm", "item.conv", short_id=short_id,
                        provider=conv["provider"], model=conv["model"],
                        count=conv["message_count"])
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, conv["id"])
        self.conv_list.addItem(item)

    def _show_conv_op_result(self, title_key: str, result: dict):
        """统一展示会话操作结果（成功/失败标题模板取词）"""
        title = self._tr("tab_llm", title_key)
        self._log(f"{title}: {result}")
        if result.get("success"):
            self._display_result(self._tr("common", "result.success", title=title),
                                 str(result))
            return
        self._display_result(self._tr("common", "result.fail", title=title),
                             result.get("error", ""), is_error=True)

    def _show_conv_detail_result(self, result: dict):
        """展示会话详情（含消息历史，JSON 格式化）"""
        self._log(self._tr("tab_llm", "log.conv_detail", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.conv_detail_fail"),
                                 result.get("error", ""), is_error=True)
            return
        content = json.dumps(result.get("conversation", {}), ensure_ascii=False,
                             indent=_JSON_INDENT)
        self._display_result(self._tr("tab_llm", "title.conv_detail"), content)

    # ------------------------------------------------------------------
    #  工具调用事件
    # ------------------------------------------------------------------

    def _on_register_tools(self):
        result = self.llm_service.register_demo_tools()
        self._log(self._tr("tab_llm", "log.register_tools", result=result))
        if result.get("success"):
            self._display_result(self._tr("tab_llm", "title.register_tools"),
                                 "\n".join(result.get("registered", [])))
        else:
            self._display_result(self._tr("tab_llm", "title.register_tools_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_unregister_tools(self):
        result = self.llm_service.unregister_demo_tools()
        self._log(self._tr("tab_llm", "log.unregister_tools", result=result))
        self._show_tool_op_result(self._tr("tab_llm", "title.unregister_tools"),
                                  result, "unregistered")

    def _on_list_tools(self):
        result = self.llm_service.list_registered_tools()
        self._log(self._tr("tab_llm", "log.list_tools", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.list_tools_fail"),
                                 result.get("error", ""), is_error=True)
            return
        descriptions = result.get("tool_descriptions", {})
        lines = [f"{name}: {desc}" for name, desc in descriptions.items()]
        self._display_result(self._tr("tab_llm", "title.tool_registry"),
                             "\n".join(lines))

    def _on_tool_chat(self):
        message = self.tool_message_input.text()
        self._begin_llm_request(self.tool_chat_btn)
        result = self.llm_service.chat_with_tools_demo(message)
        self._log(self._tr("tab_llm", "log.tool_chat", result=result))
        if not result.get("success"):
            self._end_llm_request(self.tool_chat_btn)
            self._display_result(self._tr("tab_llm", "title.tool_chat_start_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_tool_chat_stream(self):
        """发起工具流式对话（后台任务，StreamChunk 片段经 notifier 上抛）"""
        message = self.tool_message_input.text()
        self.tool_result_text.clear()
        self._begin_llm_request(self.tool_stream_btn)
        result = self.llm_service.chat_with_tools_stream_demo(message)
        self._log(self._tr("tab_llm", "log.tool_stream", result=result))
        if not result.get("success"):
            self._end_llm_request(self.tool_stream_btn)
            self._display_result(self._tr("tab_llm", "title.tool_stream_start_fail"),
                                 result.get("error", ""), is_error=True)

    def _show_tool_op_result(self, title: str, result: dict, key: str):
        """统一展示工具注册表操作结果（成功列名 / 失败弹错误）"""
        if result.get("success"):
            content = "\n".join(result.get(key, [])) or self._tr("common", "msg.none")
            self._display_result(title, content)
            return
        self._display_result(self._tr("common", "result.fail", title=title),
                             result.get("error", ""), is_error=True)

    def _on_send_embed(self):
        """发起嵌入（后台任务执行，完成/失败经 notifier 事件上抛；进行中禁用按钮防重入）"""
        text = self.embed_text_input.text()
        self._begin_llm_request(self.embed_btn)
        result = self.llm_service.send_embedding(text)
        self._log(self._tr("tab_llm", "log.embed", result=result))
        if not result.get("success"):
            self._end_llm_request(self.embed_btn)
            self._display_result(self._tr("tab_llm", "title.embed_fail"),
                                 result.get("error", ""), is_error=True)
