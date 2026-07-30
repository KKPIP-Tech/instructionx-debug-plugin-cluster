# -*- coding: utf-8 -*-
"""MCP 演示 Tab。

演示内置 MCP Server 生命周期与状态、service_api 自动桥接工具清单、
远程 MCP Server 连接/断开/工具列表（mcp_client 同步契约）。
连接/断开为阻塞操作，由服务层放入后台任务执行，
结果经事件通知器 + run_in_ui_thread 上抛 UI。
槽函数仅取输入、调用 MCPDemoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Any, Callable, Dict

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, ListWidget, Message, TextArea

from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab

# 结果面板展示 JSON 的缩进宽度
JSON_DISPLAY_INDENT = 2


class MCPTab(BaseTab):
    """MCP 演示 Tab

    职责：构建 MCP 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, mcp_service, display_result: Callable, append_log: Callable):
        """初始化 MCP 演示 Tab

        参数:
            mcp_service: MCPDemoService 实例（MCP 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
        self.mcp_service = mcp_service
        # 连接/断开在后台线程完成，经 run_in_ui_thread 封送到 UI 线程写日志
        self.mcp_service.set_event_notifier(self._on_mcp_event_notify)

    def _on_mcp_event_notify(self, message: str):
        """MCP 后台操作事件通知（工作线程）：封送到 UI 线程追加日志"""
        run_in_ui_thread(self._append_log, message)

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 MCP Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_server_group())
        layout.addWidget(self._build_bridge_group())
        layout.addWidget(self._build_remote_group())
        layout.addStretch()
        return scroll

    def _build_server_group(self) -> QGroupBox:
        """内置 MCP Server 分组：状态展示 + 启动/停止/刷新"""
        group = QGroupBox("内置 MCP Server")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.server_status_text = TextArea()
        self.server_status_text.setReadOnly(True)
        self.server_status_text.setMaximumHeight(90)
        layout.addWidget(self.server_status_text)

        btn_row = QHBoxLayout()
        self.start_server_btn = Button("启动 Server", variant="primary")
        self.start_server_btn.clicked.connect(self._on_start_server)
        btn_row.addWidget(self.start_server_btn)
        self.stop_server_btn = Button("停止 Server")
        self.stop_server_btn.clicked.connect(self._on_stop_server)
        btn_row.addWidget(self.stop_server_btn)
        self.refresh_status_btn = Button("刷新状态")
        self.refresh_status_btn.clicked.connect(self._on_refresh_status)
        btn_row.addWidget(self.refresh_status_btn)
        layout.addLayout(btn_row)

        group.setLayout(layout)
        return group

    def _build_bridge_group(self) -> QGroupBox:
        """桥接工具分组：说明文案 + 本插件自动桥接的 MCP 工具清单"""
        group = QGroupBox("桥接工具（service_api 自动注册）")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.bridge_note_text = TextArea()
        self.bridge_note_text.setReadOnly(True)
        self.bridge_note_text.setMaximumHeight(70)
        self.bridge_note_text.setPlainText(
            "插件在 information.py 声明 service_api 并提供 service.py 后，"
            "框架自动注册跨插件 API，并由 MCPBridge 同步为 MCP Server 工具；"
            "工具名为 {plugin_id}__{method} 净化形式，外部 MCP Client 可直接调用。"
        )
        layout.addWidget(self.bridge_note_text)

        self.list_bridge_btn = Button("列出本插件桥接工具", variant="primary")
        self.list_bridge_btn.clicked.connect(self._on_list_bridged_tools)
        layout.addWidget(self.list_bridge_btn)

        self.bridge_tools_list = ListWidget()
        self.bridge_tools_list.setMaximumHeight(90)
        layout.addWidget(self.bridge_tools_list)

        group.setLayout(layout)
        return group

    def _build_remote_group(self) -> QGroupBox:
        """远程 MCP Server 分组：可编辑配置 + 连接/断开/刷新/查看工具"""
        group = QGroupBox("远程 MCP Server")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.remote_config_text = TextArea()
        self.remote_config_text.setMaximumHeight(130)
        sample = self.mcp_service.get_remote_demo_config()
        self.remote_config_text.setPlainText(
            json.dumps(sample, indent=JSON_DISPLAY_INDENT, ensure_ascii=False)
        )
        layout.addWidget(self.remote_config_text)

        btn_row = QHBoxLayout()
        self.connect_btn = Button("连接", variant="primary")
        self.connect_btn.clicked.connect(self._on_connect_remote)
        btn_row.addWidget(self.connect_btn)
        self.disconnect_btn = Button("断开")
        self.disconnect_btn.clicked.connect(self._on_disconnect_remote)
        btn_row.addWidget(self.disconnect_btn)
        self.list_servers_btn = Button("刷新列表")
        self.list_servers_btn.clicked.connect(self._on_list_remote_servers)
        btn_row.addWidget(self.list_servers_btn)
        self.list_tools_btn = Button("查看工具")
        self.list_tools_btn.clicked.connect(self._on_list_remote_tools)
        btn_row.addWidget(self.list_tools_btn)
        layout.addLayout(btn_row)

        self.remote_list = ListWidget()
        self.remote_list.setMaximumHeight(90)
        layout.addWidget(self.remote_list)

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    #  公共辅助
    # ------------------------------------------------------------------

    def _show_result(self, title: str, result: Dict[str, Any]):
        """统一展示服务返回：成功显示 JSON，失败显示错误并记日志"""
        self._log(f"{title}: {result}")
        if result.get("success"):
            content = json.dumps(result, indent=JSON_DISPLAY_INDENT, ensure_ascii=False)
            self._display_result(title, content)
        else:
            self._display_result(title, result.get("error", ""), is_error=True)

    def _read_remote_config(self) -> Dict[str, Any] | None:
        """读取并解析远程配置输入框的 JSON；解析失败弹窗提示并返回 None"""
        try:
            return json.loads(self.remote_config_text.toPlainText())
        except json.JSONDecodeError as e:
            Message.warning(self._message_parent, f"配置 JSON 解析失败: {e}")
            return None

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_refresh_status(self):
        result = self.mcp_service.get_server_status()
        self._show_result("MCP Server 状态", result)
        if result.get("success"):
            self.server_status_text.setPlainText(
                json.dumps(result, indent=JSON_DISPLAY_INDENT, ensure_ascii=False)
            )

    def _on_start_server(self):
        self._show_result("启动 MCP Server", self.mcp_service.start_mcp_server())

    def _on_stop_server(self):
        self._show_result("停止 MCP Server", self.mcp_service.stop_mcp_server())

    def _on_list_bridged_tools(self):
        result = self.mcp_service.list_bridged_tools()
        self._log(f"桥接工具: {result}")
        self.bridge_tools_list.clear()
        if result.get("success"):
            for tool_name in result.get("tools", []):
                self.bridge_tools_list.addItem(tool_name)
            self._display_result("桥接工具", "\n".join(result.get("tools", [])))
        else:
            self._display_result("获取桥接工具失败", result.get("error", ""), is_error=True)

    def _on_connect_remote(self):
        config = self._read_remote_config()
        if config is not None:
            self._show_result("连接远程 Server", self.mcp_service.connect_remote_demo(config))

    def _on_disconnect_remote(self):
        config = self._read_remote_config()
        if config is not None:
            server_id = str(config.get("server_id", ""))
            self._show_result("断开远程 Server", self.mcp_service.disconnect_remote_demo(server_id))

    def _on_list_remote_servers(self):
        result = self.mcp_service.list_remote_servers()
        self._log(f"远程 Server 列表: {result}")
        self.remote_list.clear()
        if result.get("success"):
            for server_id in result.get("servers", []):
                self.remote_list.addItem(server_id)
            self._display_result("远程 Server 列表", "\n".join(result.get("servers", [])) or "暂无连接")
        else:
            self._display_result("获取远程 Server 失败", result.get("error", ""), is_error=True)

    def _on_list_remote_tools(self):
        config = self._read_remote_config()
        if config is None:
            return
        server_id = str(config.get("server_id", ""))
        result = self.mcp_service.list_remote_tools_demo(server_id)
        self._log(f"远程工具: {result}")
        self.remote_list.clear()
        if result.get("success"):
            for tool_name in result.get("tools", []):
                self.remote_list.addItem(tool_name)
            self._display_result("远程工具", "\n".join(result.get("tools", [])) or "该 Server 暂无工具")
        else:
            self._display_result("获取远程工具失败", result.get("error", ""), is_error=True)
