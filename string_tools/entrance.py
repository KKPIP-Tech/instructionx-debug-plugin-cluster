"""
字符串工具插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
"""

from PySide6.QtWidgets import QWidget
from core.plugin.plugin_interface import IPlugin
from .service import Service
from .ui.main_widget import MainWidget


class StringToolsPlugin(IPlugin):
    """字符串工具插件"""

    @property
    def plugin_name(self) -> str:
        return "字符串工具"

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
        return super().get_widget(parent, data_provider)

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        service = Service(self.plugin_id)
        widget = MainWidget(service, parent)
        return widget

    def on_plugin_loaded(self):
        """插件加载完成回调"""
        pass
