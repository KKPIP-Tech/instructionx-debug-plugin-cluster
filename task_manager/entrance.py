"""
Task Manager Plugin - Plugin Entry Point
"""

from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError
from utils.style_qss.registry import QssRegistry
from .function.services.core_service import TaskService
from .ui.main_widget import MainWidget


class TaskManagerPlugin(IPlugin):
    """任务管理器插件"""

    @property
    def plugin_name(self) -> str:
        return "任务\n管理器"

    def _load_plugin_style(self, widget: QWidget):
        """加载插件目录下的 style/*.qss，支持 {variable} 变量替换"""
        style_dir = Path(__file__).parent / "style"
        if not style_dir.exists():
            return

        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))

        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            widget.setStyleSheet(self._qss_content)
            widget.destroyed.connect(lambda qss=self._qss_content: widget.setStyleSheet(""))

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
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
        self._load_plugin_style(widget)

        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_widget = MainWidget(service, parent=widget)
        main_layout.addWidget(main_widget)

        return widget
