"""任务报告生成器插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
"""

from PySide6.QtWidgets import QWidget

from core.plugin.plugin_interface import IPlugin

from .service import Service
from .ui.main_widget import MainWidget


class TaskReporterPlugin(IPlugin):
    """任务报告生成器插件"""

    @property
    def plugin_name(self) -> str:
        return "任务\n报告"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        plugin_id = self.plugin_id if self.plugin_id else "task-reporter-default"
        service = Service(plugin_id)
        if data_provider:
            try:
                data_provider.register_plugin(plugin_id, "TaskReporter")
                data_provider.set_active_instance(plugin_id)
            except Exception:
                pass
        widget = MainWidget(service, parent)
        return widget
