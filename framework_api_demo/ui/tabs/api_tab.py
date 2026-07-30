# -*- coding: utf-8 -*-
"""跨插件 API 演示 Tab。

演示插件查询、API 查询、Function Tools 获取与跨插件方法调用。
槽函数仅取输入、调用 APIDemoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Callable

from PySide6.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, ListWidget, Message, TextArea

from .base_tab import BaseTab


class APITab(BaseTab):
    """跨插件 API 演示 Tab

    职责：构建 API 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, api_service, display_result: Callable, append_log: Callable):
        """初始化 API 演示 Tab

        参数:
            api_service: APIDemoService 实例（跨插件 API 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
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

    def _build_api_plugin_group(self) -> QGroupBox:
        group = QGroupBox("插件查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_all_plugins_btn = Button("获取所有插件", variant="primary")
        self.get_all_plugins_btn.clicked.connect(self._on_get_all_plugins)
        layout.addWidget(self.get_all_plugins_btn)

        self.plugins_list = ListWidget()
        self.plugins_list.setMaximumHeight(80)
        layout.addWidget(self.plugins_list)

        group.setLayout(layout)
        return group

    def _build_api_query_group(self) -> QGroupBox:
        group = QGroupBox("API 查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_all_apis_btn = Button("获取所有 API", variant="primary")
        self.get_all_apis_btn.clicked.connect(self._on_get_all_apis)
        layout.addWidget(self.get_all_apis_btn)

        self.apis_list = ListWidget()
        self.apis_list.setMaximumHeight(80)
        layout.addWidget(self.apis_list)

        group.setLayout(layout)
        return group

    def _build_api_function_group(self) -> QGroupBox:
        group = QGroupBox("Function Calling")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_function_tools_btn = Button("获取所有 Function Tools", variant="primary")
        self.get_function_tools_btn.clicked.connect(self._on_get_function_tools)
        layout.addWidget(self.get_function_tools_btn)

        self.function_tools_list = ListWidget()
        self.function_tools_list.setMaximumHeight(80)
        layout.addWidget(self.function_tools_list)

        group.setLayout(layout)
        return group

    def _build_api_call_group(self) -> QGroupBox:
        group = QGroupBox("跨插件调用")
        form = QFormLayout()
        form.setSpacing(6)

        self.call_plugin_input = LineEdit(placeholder="输入 plugin_id.method")
        form.addRow("调用:", self.call_plugin_input)

        self.call_method_btn = Button("调用插件方法", variant="primary")
        self.call_method_btn.clicked.connect(self._on_call_plugin_method)
        form.addRow("", self.call_method_btn)

        self.call_result_text = TextArea()
        self.call_result_text.setReadOnly(True)
        self.call_result_text.setMaximumHeight(60)
        form.addRow("结果:", self.call_result_text)

        group.setLayout(form)
        return group

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_get_all_plugins(self):
        result = self.api_service.get_all_plugins()
        self._log(f"获取插件: {result}")

        self.plugins_list.clear()
        if result.get("success"):
            lines = []
            for plugin in result.get("plugins", []):
                self.plugins_list.addItem(f"{plugin['name']} ({plugin['id']})")
                lines.append(f"• {plugin['name']} ({plugin['id']})")
            self._display_result("插件列表", "\n".join(lines))
        else:
            self._display_result("获取插件失败", result.get("error", ""), is_error=True)

    def _on_get_all_apis(self):
        result = self.api_service.get_all_apis()
        self._log(f"获取API: {result}")

        self.apis_list.clear()
        if result.get("success"):
            lines = []
            for pid, info in result.get("apis", {}).items():
                self.apis_list.addItem(f"{info['name']}: {', '.join(info['methods'])}")
                lines.append(f"• {info['name']}: {', '.join(info['methods'])}")
            self._display_result("API 列表", "\n".join(lines))
        else:
            self._display_result("获取 API 失败", result.get("error", ""), is_error=True)

    def _on_get_function_tools(self):
        result = self.api_service.get_all_function_tools()
        self._log(f"获取Function Tools: {result}")

        self.function_tools_list.clear()
        self._populate_function_tools_list(result.get("tools", []))
        self._show_function_tools_json(result.get("tools", []))

        if result.get("success"):
            lines = []
            for tool in result.get("tools", []):
                func = tool.get("function", {})
                name = func.get("name", "unknown")
                lines.append(f"• {name}")
            self._display_result("Function Tools", "\n".join(lines) if lines else "暂无工具")
        else:
            self._display_result("获取 Function Tools 失败", result.get("error", ""), is_error=True)

    def _populate_function_tools_list(self, tools: list):
        """填充 Function Tools 列表"""
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")[:50]
            self.function_tools_list.addItem(f"{name}: {desc}...")

    def _show_function_tools_json(self, tools: list):
        """显示 Function Tools JSON 信息"""
        raw_json = json.dumps(tools, indent=2, ensure_ascii=False)[:2000]
        Message.info(self._message_parent, raw_json)

    def _on_call_plugin_method(self):
        input_text = self.call_plugin_input.text()
        if not input_text or "." not in input_text:
            self._display_result("输入错误", "请输入格式: plugin_id.method", is_error=True)
            Message.warning(self._message_parent, "请输入格式: plugin_id.method")
            return

        parts = input_text.split(".", 1)
        plugin_id = parts[0]
        method_name = parts[1]

        result = self.api_service.call_plugin_method(plugin_id, method_name)
        self._log(f"调用结果: {result}")

        if result.get("success"):
            content = json.dumps(result.get("result"), indent=2, ensure_ascii=False)
            self._display_result("跨插件调用成功", content)
            self.call_result_text.setPlainText(content)
        else:
            self._display_result("跨插件调用失败", result.get("error", ""), is_error=True)
            self.call_result_text.setPlainText(f"错误: {result.get('error')}")
