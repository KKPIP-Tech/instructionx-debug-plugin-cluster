"""UI Demo Plugin"""

from core.plugin.plugin_interface import IPlugin
from .service import Service
from .ui.main_widget import MainWidget


class UiDemoPlugin(IPlugin):
    """UI Control Demo Plugin"""

    def __init__(self):
        super().__init__()

    @property
    def plugin_name(self) -> str:
        return "UI\nDemo"

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
        return super().get_widget(parent, data_provider)

    def _create_widget(self, parent=None, data_provider=None) -> MainWidget:
        """Create plugin widget"""
        service = Service()
        widget = MainWidget(parent=parent, service=service, plugin=self)
        return widget
