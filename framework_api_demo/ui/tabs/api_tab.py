# -*- coding: utf-8 -*-
"""跨插件 API 演示 Tab。

演示插件查询、API 查询、Function Tools 获取与跨插件方法调用。
槽函数仅取输入、调用 APIDemoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

import json
from typing import Callable, Optional

from PySide6.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, ListWidget, Message, TextArea

from core.interfaces import ILocalizationFacade

from ..metrics import (
    CALL_RESULT_MAX_HEIGHT, FORM_SPACING, GROUP_SPACING, LIST_BOX_MAX_HEIGHT,
)
from .base_tab import BaseTab

# 结果面板展示 JSON 的缩进宽度
_JSON_INDENT = 2

# Function Tools 列表项描述的最大展示长度
_TOOL_DESC_DISPLAY_LEN = 50


class APITab(BaseTab):
    """跨插件 API 演示 Tab

    职责：构建 API 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, api_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化 API 演示 Tab

        参数:
            api_service: APIDemoService 实例（跨插件 API 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
        self.api_service = api_service

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 API Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_api_plugin_group())
        layout.addWidget(self._build_api_query_group())
        layout.addWidget(self._build_api_function_group())
        layout.addWidget(self._build_api_call_group())
        layout.addStretch()
        return scroll

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_api 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_api", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_api 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_api", key, slot, variant=variant)

    def _build_api_plugin_group(self) -> QGroupBox:
        group = self._make_group("group.plugins")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.get_all_plugins_btn = self._make_button(
            "btn.get_plugins", self._on_get_all_plugins, variant="primary")
        layout.addWidget(self.get_all_plugins_btn)
        self.plugins_list = ListWidget()
        self.plugins_list.setMaximumHeight(LIST_BOX_MAX_HEIGHT)
        layout.addWidget(self.plugins_list)
        group.setLayout(layout)
        return group

    def _build_api_query_group(self) -> QGroupBox:
        group = self._make_group("group.apis")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.get_all_apis_btn = self._make_button(
            "btn.get_apis", self._on_get_all_apis, variant="primary")
        layout.addWidget(self.get_all_apis_btn)
        self.apis_list = ListWidget()
        self.apis_list.setMaximumHeight(LIST_BOX_MAX_HEIGHT)
        layout.addWidget(self.apis_list)
        group.setLayout(layout)
        return group

    def _build_api_function_group(self) -> QGroupBox:
        group = self._make_group("group.functions")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.get_function_tools_btn = self._make_button(
            "btn.get_tools", self._on_get_function_tools, variant="primary")
        layout.addWidget(self.get_function_tools_btn)
        self.function_tools_list = ListWidget()
        self.function_tools_list.setMaximumHeight(LIST_BOX_MAX_HEIGHT)
        layout.addWidget(self.function_tools_list)
        group.setLayout(layout)
        return group

    def _build_api_call_group(self) -> QGroupBox:
        group = self._make_group("group.call")
        form = QFormLayout()
        form.setSpacing(FORM_SPACING)
        self.call_plugin_input = LineEdit(
            placeholder=self._tr("tab_api", "placeholder.call"))
        self._bind(self.call_plugin_input, "tab_api", "placeholder.call",
                   setter="setPlaceholderText")
        form.addRow(self._make_label("tab_api", "label.call"), self.call_plugin_input)
        self.call_method_btn = self._make_button(
            "btn.call", self._on_call_plugin_method, variant="primary")
        form.addRow("", self.call_method_btn)
        self.call_result_text = TextArea()
        self.call_result_text.setReadOnly(True)
        self.call_result_text.setMaximumHeight(CALL_RESULT_MAX_HEIGHT)
        form.addRow(self._make_label("common", "label.result"), self.call_result_text)
        group.setLayout(form)
        return group

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_get_all_plugins(self):
        result = self.api_service.get_all_plugins()
        self._log(self._tr("tab_api", "log.plugins", result=result))
        self.plugins_list.clear()
        if result.get("success"):
            lines = []
            for plugin in result.get("plugins", []):
                self.plugins_list.addItem(f"{plugin['name']} ({plugin['id']})")
                lines.append(f"• {plugin['name']} ({plugin['id']})")
            self._display_result(self._tr("tab_api", "title.plugins"), "\n".join(lines))
        else:
            self._display_result(self._tr("tab_api", "title.plugins_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_get_all_apis(self):
        result = self.api_service.get_all_apis()
        self._log(self._tr("tab_api", "log.apis", result=result))
        self.apis_list.clear()
        if result.get("success"):
            lines = []
            for pid, info in result.get("apis", {}).items():
                self.apis_list.addItem(f"{info['name']}: {', '.join(info['methods'])}")
                lines.append(f"• {info['name']}: {', '.join(info['methods'])}")
            self._display_result(self._tr("tab_api", "title.apis"), "\n".join(lines))
        else:
            self._display_result(self._tr("tab_api", "title.apis_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_get_function_tools(self):
        result = self.api_service.get_all_function_tools()
        self._log(self._tr("tab_api", "log.tools", result=result))
        self.function_tools_list.clear()
        self._populate_function_tools_list(result.get("tools", []))
        if result.get("success"):
            self._show_function_tools_json(result.get("tools", []))
            names = [f"• {tool.get('function', {}).get('name', 'unknown')}"
                     for tool in result.get("tools", [])]
            content = "\n".join(names) if names else self._tr("tab_api", "empty.tools")
            self._display_result(self._tr("tab_api", "title.tools"), content)
        else:
            self._display_result(self._tr("tab_api", "title.tools_fail"),
                                 result.get("error", ""), is_error=True)

    def _populate_function_tools_list(self, tools: list):
        """填充 Function Tools 列表"""
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")[:_TOOL_DESC_DISPLAY_LEN]
            self.function_tools_list.addItem(self._tr(
                "tab_api", "msg.tool_line", name=name, desc=desc))

    def _show_function_tools_json(self, tools: list):
        """把 Function Tools 原始 JSON 写入结果面板（替代原先截断 2000 字符的弹窗）"""
        raw_json = json.dumps(tools, indent=_JSON_INDENT, ensure_ascii=False)
        self._display_result(self._tr("tab_api", "title.tools_json"), raw_json)

    def _on_call_plugin_method(self):
        input_text = self.call_plugin_input.text()
        if not input_text or "." not in input_text:
            warning = self._tr("tab_api", "warn.format")
            self._display_result(self._tr("tab_api", "title.input_error"),
                                 warning, is_error=True)
            Message.warning(self._message_parent, warning)
            return
        plugin_id, method_name = input_text.split(".", 1)
        result = self.api_service.call_plugin_method(plugin_id, method_name)
        self._log(self._tr("tab_api", "log.call", result=result))
        self._show_call_result(result)

    def _show_call_result(self, result: dict):
        """展示跨插件调用结果（成功写结果区，失败写错误前缀）"""
        if result.get("success"):
            content = json.dumps(result.get("result"), indent=_JSON_INDENT,
                                 ensure_ascii=False)
            self._display_result(self._tr("tab_api", "title.call_ok"), content)
            self.call_result_text.setPlainText(content)
        else:
            error = result.get("error", "")
            self._display_result(self._tr("tab_api", "title.call_fail"),
                                 error, is_error=True)
            self.call_result_text.setPlainText(
                self._tr("common", "error.prefix", error=error))
