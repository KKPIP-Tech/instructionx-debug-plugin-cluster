# -*- coding: utf-8 -*-
"""任务管理器插件入口（胶水层）。

实例化 TaskService 与 MainWidget 并组装到宿主控件；
样式由 InstructionX_UIKit 全局主题提供，插件不再加载本地 QSS。
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError

from .function.services.core_service import TaskService
from .ui.main_widget import MainWidget


class TaskManagerPlugin(IPlugin):
    """任务管理器插件"""

    @property
    def plugin_name(self) -> str:
        return "任务\n管理器"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        """创建插件主控件：注册数据命名空间并组装 UI。"""
        dp = DataProvider()

        actual_plugin_id = self.plugin_id
        if actual_plugin_id is None:
            actual_plugin_id = "task-manager-default"
            self._plugin_id = actual_plugin_id

        try:
            dp.register_plugin(actual_plugin_id, "TaskManager")
            dp.set_active_instance(actual_plugin_id)
        except DataProviderError:
            pass

        if data_provider:
            try:
                data_provider.register_plugin(actual_plugin_id, "TaskManager")
                data_provider.set_active_instance(actual_plugin_id)
            except DataProviderError:
                pass

        service = TaskService(actual_plugin_id)

        widget = QWidget(parent)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_widget = MainWidget(service, parent=widget)
        main_layout.addWidget(main_widget)

        return widget
