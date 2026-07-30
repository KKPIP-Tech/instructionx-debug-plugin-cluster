# -*- coding: utf-8 -*-
"""框架信息演示 Tab。

演示框架信息获取、框架 utils 工具（日志级别、线程封送、字体与资源）
以及 UIKit 主题跟随，并展示可用接口文档文本。
槽函数仅调用 FrameworkInfoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Any, Callable, Dict

from PySide6.QtWidgets import QGroupBox, QLabel, QVBoxLayout, QScrollArea

from InstructionX_UIKit import ThemeManager
from InstructionX_UIKit.components import Button, TextArea

from .base_tab import BaseTab

# 主题状态标签的文案前缀
_THEME_LABEL_PREFIX = "当前主题: "


class InfoTab(BaseTab):
    """框架信息演示 Tab

    职责：构建信息演示页的控件布局（含框架信息、utils 工具演示、
    主题跟随演示与可用接口文档）并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, info_service, display_result: Callable, append_log: Callable):
        """初始化信息演示 Tab

        参数:
            info_service: FrameworkInfoService 实例（框架信息演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
        self.info_service = info_service

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 Info Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_info_group())
        layout.addWidget(self._build_log_group())
        layout.addWidget(self._build_thread_group())
        layout.addWidget(self._build_asset_group())
        layout.addWidget(self._build_theme_group())
        layout.addWidget(self._build_info_doc_group())
        layout.addStretch()
        return scroll

    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("框架信息")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_info_btn = Button("获取框架信息", variant="primary")
        self.get_info_btn.clicked.connect(self._on_get_framework_info)
        layout.addWidget(self.get_info_btn)

        self.info_text = TextArea()
        self.info_text.setReadOnly(True)
        layout.addWidget(self.info_text)

        group.setLayout(layout)
        return group

    def _build_log_group(self) -> QGroupBox:
        """构建「日志级别」分组：写入 LoggerManager 五级日志"""
        group = QGroupBox("日志级别（LoggerManager）")
        layout = QVBoxLayout()
        self.log_levels_btn = Button("写入五级日志", variant="primary")
        self.log_levels_btn.clicked.connect(self._on_write_log_levels)
        layout.addWidget(self.log_levels_btn)
        group.setLayout(layout)
        return group

    def _build_thread_group(self) -> QGroupBox:
        """构建「线程工具」分组：演示 is_ui_thread 与 run_in_ui_thread(_sync)"""
        group = QGroupBox("线程工具（thread_utils）")
        layout = QVBoxLayout()
        self.thread_utils_btn = Button("演示线程封送", variant="primary")
        self.thread_utils_btn.clicked.connect(self._on_demo_thread_utils)
        layout.addWidget(self.thread_utils_btn)
        group.setLayout(layout)
        return group

    def _build_asset_group(self) -> QGroupBox:
        """构建「字体与资源」分组：FontMap 字体查询与图片转 Base64"""
        group = QGroupBox("字体与资源（FontMap / image_utils）")
        layout = QVBoxLayout()
        self.font_map_btn = Button("列出字体", variant="primary")
        self.font_map_btn.clicked.connect(self._on_demo_font_map)
        layout.addWidget(self.font_map_btn)
        self.image_base64_btn = Button("图片转 Base64", variant="primary")
        self.image_base64_btn.clicked.connect(self._on_demo_image_base64)
        layout.addWidget(self.image_base64_btn)
        group.setLayout(layout)
        return group

    def _build_theme_group(self) -> QGroupBox:
        """构建「主题跟随」分组：监听 ThemeManager.theme_changed

        UIKit 组件本身随全局 QSS 自动跟随主题，无需监听信号；
        只有插件自建样式（自定义 QSS/绘制）才需要监听 theme_changed 做适配。
        """
        group = QGroupBox("主题跟随（ThemeManager.theme_changed）")
        layout = QVBoxLayout()
        theme_manager = ThemeManager.instance()
        self.theme_status_label = QLabel(f"{_THEME_LABEL_PREFIX}{theme_manager.mode}")
        layout.addWidget(self.theme_status_label)
        theme_manager.theme_changed.connect(self._on_theme_changed)
        group.setLayout(layout)
        return group

    def _build_info_doc_group(self) -> QGroupBox:
        doc_text = TextArea()
        doc_text.setReadOnly(True)
        doc_text.setPlainText(self._get_api_doc_text())

        group = QGroupBox("可用接口文档")
        layout = QVBoxLayout()
        layout.addWidget(doc_text)
        group.setLayout(layout)
        return group

    def _get_api_doc_text(self) -> str:
        """获取 API 文档文本"""
        return """Framework API Demo 演示以下接口:

1. DataProvider
   - register_plugin() / unregister_plugin()
   - get_plugin_data() / set_plugin_data() / get_all_plugin_data()
   - subscribe() / publish() / unsubscribe()（发布订阅）
   - save_asset() / load_asset()
   - get_active_instance()

2. BackgroundTaskManager
   - register_sync_task() / register_async_task()
   - register_scheduled_task()（含启用/禁用/注销）
   - register_long_running_task() / stop_long_running_task()
   - cancel_task() / get_task_status()
   - get_tasks_by_plugin() / clear_completed_tasks()

3. ILLMService（llm_facade）
   - list_providers() / get_models() / validate_provider()
   - chat() / stream_chat() / embed()
   - 会话: create_conversation() / send_message() / stream_send_message()
     / get_conversation() / list_conversations() / delete_conversation()
   - 工具调用: get_shared_tool_registry()（register/unregister/list_tools）
     / chat_with_tools()；入口 IPlugin.llm_tools 钩子
   - 多模态: generate_image() / text_to_speech()
   - get_usage_stats()

4. PluginManager
   - get_all_plugins() / get_plugin_by_id()
   - get_all_apis() / call_plugin_method()
   - get_all_function_tools() (Function Calling)
   - get_api_description()

5. MCPManager / MCPClientManager
   - start_server() / stop_server() / is_server_running() / get_server_url()
   - service_api 自动桥接工具（{plugin_id}__{method} 净化名）
   - connect() / disconnect() / list_connected_servers() / list_tools()

6. LoggerManager
   - debug() / info() / warning() / error() / critical()

7. utils 工具与主题
   - is_ui_thread() / run_in_ui_thread() / run_in_ui_thread_sync()
   - FontMap.get() / FontMap.all_fonts()
   - load_image_as_base64()
   - ThemeManager.theme_changed 主题跟随
"""

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_get_framework_info(self):
        result = self.info_service.get_framework_info()
        self._log(f"框架信息: {result}")
        if result:
            content = json.dumps(result, indent=2, ensure_ascii=False)
            self._display_result("框架信息", content)
            self.info_text.setPlainText(content)
        else:
            self._display_result("获取框架信息失败", "无返回数据", is_error=True)

    def _on_write_log_levels(self):
        """写入五级日志并展示结果"""
        result = self.info_service.demo_log_levels()
        self._show_service_result("日志级别演示", result)

    def _on_demo_thread_utils(self):
        """演示线程封送：is_ui_thread 对照经服务任务回传"""
        result = self.info_service.demo_thread_utils()
        self._show_service_result("线程工具演示", result)

    def _on_demo_font_map(self):
        """列出 FontMap 可用字体"""
        result = self.info_service.demo_font_map()
        self._show_service_result("字体查询演示", result)

    def _on_demo_image_base64(self):
        """演示图片转 Base64"""
        result = self.info_service.demo_load_image_base64()
        self._show_service_result("图片转 Base64 演示", result)

    def _on_theme_changed(self, mode: str):
        """主题切换回调：更新状态标签并记录日志（UIKit 组件本身自动跟随主题）"""
        self.theme_status_label.setText(f"{_THEME_LABEL_PREFIX}{mode}")
        self._log(f"主题已切换: {mode}")

    def _show_service_result(self, title: str, result: Dict[str, Any]):
        """统一展示服务返回结果（含失败分支）"""
        self._log(f"{title}: {result}")
        content = json.dumps(result, indent=2, ensure_ascii=False)
        self._display_result(title, content, is_error=not result.get("success", False))
