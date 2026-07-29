# -*- coding: utf-8 -*-
"""LLM Chat 插件入口 — 胶水层。

仅负责创建 Service 与 MainWidget 并完成接线；
UI 在 ui/，业务逻辑在 function/，本文件不含任何界面构建代码。
"""

from PySide6.QtWidgets import QWidget

from core.data.data_provider import DataProvider, DataProviderError
from core.plugin.plugin_interface import IPlugin
from utils.logging_tools import LoggerManager, get_name

from .service import Service
from .ui.main_widget import MainWidget

# 未经框架加载（独立实例化、无注入 plugin_id）时的回退标识
_FALLBACK_PLUGIN_ID = "llm-chat-default"
# DataProvider 注册用的插件类型名
_PLUGIN_TYPE_NAME = "LLMChat"


class LLMChatPlugin(IPlugin):
    """LLM Chat 插件（胶水层：Service + MainWidget 的创建与接线）"""

    _logger = LoggerManager()

    @property
    def plugin_name(self) -> str:
        return "LLM\nChat"

    def on_plugin_loaded(self):
        self._logger.info(get_name(), f"插件已加载: {self.plugin_name}")

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        """创建插件主控件：注册数据命名空间后装配 Service 与 MainWidget"""
        plugin_id = self.plugin_id or _FALLBACK_PLUGIN_ID
        dp = DataProvider()
        self._register_data_namespace(dp, plugin_id)
        if data_provider:
            self._register_data_namespace(data_provider, plugin_id)

        self.service = Service(plugin_id, dp)
        self.widget = MainWidget(self.service, parent)
        return self.widget

    def _register_data_namespace(self, dp, plugin_id: str):
        """注册插件数据命名空间（已注册时 DataProviderError 属正常，忽略）"""
        try:
            dp.register_plugin(plugin_id, _PLUGIN_TYPE_NAME)
            dp.set_active_instance(plugin_id)
        except DataProviderError:
            pass
