# -*- coding: utf-8 -*-
"""MCP 演示 Tab。

演示内置 MCP Server 生命周期与状态、service_api 自动桥接工具清单、
远程 MCP Server 连接/断开/工具列表（mcp_client 同步契约）。
连接/断开为阻塞操作，由服务层放入后台任务执行，
结果经事件通知器 + run_in_ui_thread 上抛 UI。
槽函数仅取输入、调用 MCPDemoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

import json
from typing import Any, Callable, Dict, Optional

from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, ListWidget, Message, TextArea

from core.interfaces import ILocalizationFacade
from utils.thread_utils import run_in_ui_thread

from ..metrics import (
    BRIDGE_NOTE_MAX_HEIGHT, GROUP_SPACING, MCP_LIST_MAX_HEIGHT,
    REMOTE_CONFIG_MAX_HEIGHT, SERVER_STATUS_MAX_HEIGHT,
)
from .base_tab import BaseTab

# 结果面板展示 JSON 的缩进宽度
JSON_DISPLAY_INDENT = 2


class MCPTab(BaseTab):
    """MCP 演示 Tab

    职责：构建 MCP 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, mcp_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化 MCP 演示 Tab

        参数:
            mcp_service: MCPDemoService 实例（MCP 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
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

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_mcp 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_mcp", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_mcp 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_mcp", key, slot, variant=variant)

    def _build_server_group(self) -> QGroupBox:
        """内置 MCP Server 分组：状态展示 + 启动/停止/刷新"""
        group = self._make_group("group.server")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.server_status_text = TextArea()
        self.server_status_text.setReadOnly(True)
        self.server_status_text.setMaximumHeight(SERVER_STATUS_MAX_HEIGHT)
        layout.addWidget(self.server_status_text)
        for row in self._build_server_button_rows():
            layout.addLayout(row)
        group.setLayout(layout)
        return group

    def _build_server_button_rows(self) -> list:
        """构建 Server 控制按钮行（拆为两行，适配收窄后的面板宽度）"""
        control_row = QHBoxLayout()
        self.start_server_btn = self._make_button(
            "btn.start", self._on_start_server, variant="primary")
        control_row.addWidget(self.start_server_btn)
        self.stop_server_btn = self._make_button("btn.stop", self._on_stop_server)
        control_row.addWidget(self.stop_server_btn)
        refresh_row = QHBoxLayout()
        self.refresh_status_btn = self._make_button("btn.refresh", self._on_refresh_status)
        refresh_row.addWidget(self.refresh_status_btn)
        refresh_row.addStretch()
        return [control_row, refresh_row]

    def _build_bridge_group(self) -> QGroupBox:
        """桥接工具分组：说明文案 + 本插件自动桥接的 MCP 工具清单"""
        group = self._make_group("group.bridge")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.bridge_note_text = TextArea()
        self.bridge_note_text.setReadOnly(True)
        self.bridge_note_text.setMaximumHeight(BRIDGE_NOTE_MAX_HEIGHT)
        self.bridge_note_text.setPlainText(self._tr("tab_mcp", "note.bridge"))
        layout.addWidget(self.bridge_note_text)
        self.list_bridge_btn = self._make_button(
            "btn.list_bridge", self._on_list_bridged_tools, variant="primary")
        layout.addWidget(self.list_bridge_btn)
        self.bridge_tools_list = ListWidget()
        self.bridge_tools_list.setMaximumHeight(MCP_LIST_MAX_HEIGHT)
        layout.addWidget(self.bridge_tools_list)
        group.setLayout(layout)
        return group

    def _build_remote_group(self) -> QGroupBox:
        """远程 MCP Server 分组：可编辑配置 + 连接/断开/刷新/查看工具"""
        group = self._make_group("group.remote")
        layout = QVBoxLayout()
        layout.setSpacing(GROUP_SPACING)
        self.remote_config_text = TextArea()
        self.remote_config_text.setMaximumHeight(REMOTE_CONFIG_MAX_HEIGHT)
        sample = self.mcp_service.get_remote_demo_config()
        self.remote_config_text.setPlainText(
            json.dumps(sample, indent=JSON_DISPLAY_INDENT, ensure_ascii=False)
        )
        layout.addWidget(self.remote_config_text)
        for row in self._build_remote_button_rows():
            layout.addLayout(row)
        self.remote_list = ListWidget()
        self.remote_list.setMaximumHeight(MCP_LIST_MAX_HEIGHT)
        layout.addWidget(self.remote_list)
        group.setLayout(layout)
        return group

    def _build_remote_button_rows(self) -> list:
        """构建远程操作按钮行（连接/断开 与 刷新列表/查看工具 各一行，适配窄面板）"""
        conn_row = QHBoxLayout()
        self.connect_btn = self._make_button(
            "btn.connect", self._on_connect_remote, variant="primary")
        conn_row.addWidget(self.connect_btn)
        self.disconnect_btn = self._make_button("btn.disconnect", self._on_disconnect_remote)
        conn_row.addWidget(self.disconnect_btn)
        view_row = QHBoxLayout()
        self.list_servers_btn = self._make_button("btn.refresh_list",
                                                  self._on_list_remote_servers)
        view_row.addWidget(self.list_servers_btn)
        self.list_tools_btn = self._make_button("btn.list_tools",
                                                self._on_list_remote_tools)
        view_row.addWidget(self.list_tools_btn)
        return [conn_row, view_row]

    def retranslate(self) -> None:
        """语言切换后重设静态文案，并按当前语言重取桥接说明文本"""
        super().retranslate()
        self.bridge_note_text.setPlainText(self._tr("tab_mcp", "note.bridge"))

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
            Message.warning(self._message_parent,
                            self._tr("tab_mcp", "warn.json", error=e))
            return None

    def _show_list_result(self, title_key: str, fail_key: str, result: Dict[str, Any],
                          items_key: str, empty_key: Optional[str] = None):
        """统一展示列表型结果（桥接工具/远程 Server/远程工具）：成功按行列出

        参数:
            empty_key: 列表为空时的回退文案键（tab_mcp 分组）；None 表示无回退
        """
        if result.get("success"):
            items = result.get(items_key, [])
            content = "\n".join(items)
            if not content and empty_key is not None:
                content = self._tr("tab_mcp", empty_key)
            self._display_result(self._tr("tab_mcp", title_key), content)
        else:
            self._display_result(self._tr("tab_mcp", fail_key),
                                 result.get("error", ""), is_error=True)

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_refresh_status(self):
        result = self.mcp_service.get_server_status()
        self._show_result(self._tr("tab_mcp", "title.server_status"), result)
        if result.get("success"):
            self.server_status_text.setPlainText(
                json.dumps(result, indent=JSON_DISPLAY_INDENT, ensure_ascii=False)
            )

    def _on_start_server(self):
        title = self._tr("tab_mcp", "title.start_server")
        self._show_result(title, self.mcp_service.start_mcp_server())

    def _on_stop_server(self):
        title = self._tr("tab_mcp", "title.stop_server")
        self._show_result(title, self.mcp_service.stop_mcp_server())

    def _on_list_bridged_tools(self):
        result = self.mcp_service.list_bridged_tools()
        self._log(self._tr("tab_mcp", "log.bridged", result=result))
        self.bridge_tools_list.clear()
        if result.get("success"):
            for tool_name in result.get("tools", []):
                self.bridge_tools_list.addItem(tool_name)
        self._show_list_result("title.bridged", "title.bridged_fail", result, "tools")

    def _on_connect_remote(self):
        config = self._read_remote_config()
        if config is not None:
            self._show_result(self._tr("tab_mcp", "title.connect"),
                              self.mcp_service.connect_remote_demo(config))

    def _on_disconnect_remote(self):
        config = self._read_remote_config()
        if config is not None:
            server_id = str(config.get("server_id", ""))
            self._show_result(self._tr("tab_mcp", "title.disconnect"),
                              self.mcp_service.disconnect_remote_demo(server_id))

    def _on_list_remote_servers(self):
        result = self.mcp_service.list_remote_servers()
        self._log(self._tr("tab_mcp", "log.servers", result=result))
        self.remote_list.clear()
        if result.get("success"):
            for server_id in result.get("servers", []):
                self.remote_list.addItem(server_id)
        self._show_list_result("title.servers", "title.servers_fail", result,
                               "servers", "empty.servers")

    def _on_list_remote_tools(self):
        config = self._read_remote_config()
        if config is None:
            return
        server_id = str(config.get("server_id", ""))
        result = self.mcp_service.list_remote_tools_demo(server_id)
        self._log(self._tr("tab_mcp", "log.tools", result=result))
        self.remote_list.clear()
        if result.get("success"):
            for tool_name in result.get("tools", []):
                self.remote_list.addItem(tool_name)
        self._show_list_result("title.tools", "title.tools_fail", result,
                               "tools", "empty.tools")
