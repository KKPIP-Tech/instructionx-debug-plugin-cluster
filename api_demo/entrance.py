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

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
        return super().get_widget(parent, data_provider)

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
