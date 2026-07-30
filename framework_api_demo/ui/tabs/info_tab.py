# -*- coding: utf-8 -*-
"""框架信息演示 Tab。

演示框架信息获取，并展示可用接口文档文本。
槽函数仅调用 FrameworkInfoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Callable

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, TextArea

from .base_tab import BaseTab


class InfoTab(BaseTab):
    """框架信息演示 Tab

    职责：构建信息演示页的控件布局（含可用接口文档）并处理其事件，
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
   - get_plugin_data() / set_plugin_data()
   - save_asset() / load_asset()

2. BackgroundTaskManager
   - register_sync_task() / register_async_task()
   - register_scheduled_task()
   - get_tasks_by_plugin() / clear_completed_tasks()

3. LLMProvider
   - get_all_providers() / get_cached_models()
   - chat() / stream_chat()
   - embed()

4. PluginManager
   - get_all_plugins() / get_plugin_by_id()
   - get_all_apis() / call_plugin_method()
   - get_all_function_tools() (Function Calling)
   - get_api_description()

5. LoggerManager
   - debug() / info() / warning() / error() / critical()
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
