"""
任务报告生成器插件 - 官方插件示例
提供任务统计报告生成和实时监控功能
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from core.plugin.plugin_interface import IPlugin
from .service import Service
from .ui.main_widget import MainWidget


class TaskReporterPlugin(IPlugin):
    """任务报告生成器插件"""

    @property
    def plugin_name(self) -> str:
        return "任务\n报告"

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
        return super().get_widget(parent, data_provider)

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
