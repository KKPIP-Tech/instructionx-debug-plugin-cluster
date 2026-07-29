"""
Framework API Demo 插件入口（胶水层）

展示 InstructionX 框架提供的所有核心 API 接口的使用方法。
本模块仅负责插件生命周期、服务初始化与主控件创建；
全部 UI 构建与事件处理位于 ui/main_widget.py。
"""

from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import QWidget

from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError
from utils.logging_tools import LoggerManager

from .function.services.core_service import (
    DataDemoService, TaskDemoService, LLMDemoService,
    APIDemoService, FrameworkInfoService
)
from .ui.main_widget import MainWidget


class SignalBridge(QObject):
    """Qt 信号桥接器，用于线程安全的 UI 更新"""
    log_message = Signal(str)


class FrameworkAPIDemoPlugin(IPlugin):
    """Framework API Demo 插件（胶水层）"""

    _logger = LoggerManager()

    def __init__(self):
        super().__init__()
        self._signal_bridge = SignalBridge()
        self._main_widget: Optional[MainWidget] = None

        # 服务实例（在 on_plugin_loaded 中初始化）
        self.data_service: Optional[DataDemoService] = None
        self.task_service: Optional[TaskDemoService] = None
        self.llm_service: Optional[LLMDemoService] = None
        self.api_service: Optional[APIDemoService] = None
        self.info_service: Optional[FrameworkInfoService] = None

    @property
    def plugin_name(self) -> str:
        return "Framework\nAPI Demo"

    def on_plugin_loaded(self, plugin_id=None, **kwargs):
        """插件加载完成后初始化服务和注册（仅执行一次）"""
        dp = self._get_data_provider()
        self._register_with_provider(dp)
        self._init_services(dp)
        self._signal_bridge.log_message.connect(self._on_log_message)

    def _get_data_provider(self) -> DataProvider:
        """获取 DataProvider 实例（优先使用框架注入的）"""
        services = getattr(self, '_services', None)
        if services and hasattr(services, 'data_provider'):
            return services.data_provider
        return DataProvider()

    def _register_with_provider(self, dp: DataProvider):
        """向 DataProvider 注册插件并设置活跃实例"""
        plugin_id = self.plugin_id
        try:
            dp.register_plugin(plugin_id, "FrameworkAPIDemo")
        except DataProviderError as e:
            err = str(e)
            if "已存在" not in err and "exists" not in err.lower():
                self._log(f"注册插件失败: {err}")
                return
        try:
            dp.set_active_instance(plugin_id)
        except DataProviderError as e:
            self._log(f"设置活跃实例失败: {e}")

    def _init_services(self, dp: DataProvider):
        """初始化所有演示服务"""
        pid = self.plugin_id
        self.data_service = DataDemoService(pid, dp)
        self.task_service = TaskDemoService(pid, dp)
        self.llm_service = LLMDemoService(pid, dp)
        self.api_service = APIDemoService(pid, dp)
        self.info_service = FrameworkInfoService(pid, dp)

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        """创建插件主控件（UI 构建由 MainWidget 完成）"""
        widget = MainWidget(
            data_service=self.data_service,
            task_service=self.task_service,
            llm_service=self.llm_service,
            api_service=self.api_service,
            info_service=self.info_service,
            parent=parent,
        )
        self._main_widget = widget
        widget.append_log("Framework API Demo 插件已加载")
        widget.append_log(f"插件 ID: {self.plugin_id}")
        return widget

    def _log(self, message: str):
        """插件加载早期日志：经信号桥转发给主控件（控件未创建时丢弃）"""
        self._signal_bridge.log_message.emit(message)

    @Slot(str)
    def _on_log_message(self, message: str):
        """将信号桥日志转发给主控件日志面板（控件未创建时忽略）"""
        if self._main_widget is not None:
            self._main_widget.append_log(message)
