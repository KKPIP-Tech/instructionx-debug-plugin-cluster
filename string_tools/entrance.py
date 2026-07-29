"""
字符串工具插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
UIKit 主题切换对组件自动生效，无需主题缓存覆写。
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

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        service = Service(self.plugin_id)
        widget = MainWidget(service, parent)
        return widget

    def on_plugin_loaded(self):
        """插件加载完成回调"""
        pass
