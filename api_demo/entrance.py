"""
API Demo 插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
"""

from PySide6.QtWidgets import QWidget

from core.plugin.plugin_interface import IPlugin
from .service import Service
from .ui.main_widget import MainWidget


class ApiDemoPlugin(IPlugin):
    """API 调用演示插件"""

    def __init__(self, services=None):
        super().__init__()
        self._services = services

    @property
    def plugin_name(self) -> str:
        return "API 调用\n演示"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        plugin_id = self.plugin_id or "api-demo-default"
        data_provider = data_provider or (self._services.data_provider if self._services else None)
        if data_provider:
            try:
                data_provider.register_plugin(plugin_id, "ApiDemo")
                data_provider.set_active_instance(plugin_id)
            except Exception:
                pass
        service = Service(plugin_id)
        widget = MainWidget(service, parent)
        return widget
