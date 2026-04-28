"""
图片压缩插件 — 胶水层

实例化 Service 和 MainWidget，连接两者。
"""

from PySide6.QtWidgets import QWidget

from core.plugin.plugin_interface import IPlugin
from .function.services.core_service import CoreService as Service
from .ui.main_widget import MainWidget


class ImageCompressorPlugin(IPlugin):
    """图片压缩插件"""

    @property
    def plugin_name(self) -> str:
        return "图片压缩"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        service = Service(self.plugin_id)
        widget = MainWidget(service, parent)
        return widget
