"""
单位转换插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
"""

from PySide6.QtWidgets import QWidget

from core.plugin.plugin_interface import IPlugin
from .service import UnitConverterService as Service
from .ui.main_widget import MainWidget


class UnitConverterPlugin(IPlugin):
    """单位转换插件"""

    @property
    def plugin_name(self) -> str:
        return "单位转换"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        service = Service(self.plugin_id)
        widget = MainWidget(service, parent)
        return widget
