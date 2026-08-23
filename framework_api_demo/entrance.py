"""
Framework API Demo 插件入口（胶水层）

展示 InstructionX 框架提供的所有核心 API 接口的使用方法。
本模块仅负责插件生命周期、服务初始化与主控件创建；
全部 UI 构建与事件处理位于 ui/main_widget.py。
"""

import traceback
from typing import Any, Dict, List, Optional

from PySide6.QtWidgets import QWidget

from core.interfaces import PluginServices
from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError
from utils.logging_tools import LoggerManager
from utils.thread_utils import run_in_ui_thread

from .function.services import (
    DataDemoService, TaskDemoService, LLMDemoService,
    APIDemoService, FrameworkInfoService, MCPDemoService
)
from .function.tools import DEMO_TOOL_DEFINITIONS
from .ui.main_widget import MainWidget


class FrameworkAPIDemoPlugin(IPlugin):
    """Framework API Demo 插件（胶水层）"""

    _logger = LoggerManager()

    def __init__(self, services: Optional[PluginServices] = None):
        super().__init__()
        # 框架加载时经构造函数注入 PluginServices（见 PluginManager._instantiate_plugin）
        self._injected_services = services
        self._main_widget: Optional[MainWidget] = None

        # 服务实例（在 on_plugin_loaded 中初始化）
        self.data_service: Optional[DataDemoService] = None
        self.task_service: Optional[TaskDemoService] = None
        self.llm_service: Optional[LLMDemoService] = None
        self.api_service: Optional[APIDemoService] = None
        self.info_service: Optional[FrameworkInfoService] = None
        self.mcp_service: Optional[MCPDemoService] = None

    @property
    def plugin_name(self) -> str:
        return "Framework\nAPI Demo"

    @property
    def llm_tools(self) -> List[Dict[str, Any]]:
        """演示 IPlugin.llm_tools 钩子：声明本插件暴露给 LLM 的工具

        框架消费方式说明（以 core/ 实际代码为准）：框架核心当前仅在
        IPlugin 接口中定义该属性契约（OpenAI function calling 格式的
        字典列表），尚未在 PluginManager 等处自动收集消费——插件需
        自行把工具注册进共享 ToolRegistry（见 llm_service.register_demo_tools）
        才能让 LLM 实际调用；该属性是声明式清单，与 information.py 的
        service_api 自动注册跨插件 API 是两条独立通道。
        """
        return DEMO_TOOL_DEFINITIONS

    def on_plugin_loaded(self, plugin_id=None, **kwargs):
        """插件加载完成后初始化服务和注册（仅执行一次）"""
        dp = self._get_data_provider()
        self._register_with_provider(dp)
        self._init_services(dp)

    def on_plugin_unloaded(self):
        """插件卸载清理：逐个服务 cleanup，异常不向外逃逸"""
        for service in self._iter_cleanup_services():
            self._safe_cleanup_service(service)

    def _get_services(self) -> Optional[PluginServices]:
        """获取 PluginServices：优先构造注入，其次框架注入的 _services 实例属性"""
        if self._injected_services is not None:
            return self._injected_services
        return getattr(self, '_services', None)

    def _get_data_provider(self) -> DataProvider:
        """获取 DataProvider 实例（优先使用框架注入的；取不到回退单例保证容错）"""
        services = self._get_services()
        if services and getattr(services, 'data_provider', None):
            return services.data_provider
        # 回退单例：兼容框架未注入 services 的旧加载路径
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
        """初始化所有演示服务（统一传入 PluginServices 与 DataProvider）"""
        pid = self.plugin_id
        services = self._get_services()
        self.data_service = DataDemoService(pid, services=services, data_provider=dp)
        self.task_service = TaskDemoService(pid, services=services, data_provider=dp)
        self.llm_service = LLMDemoService(pid, services=services, data_provider=dp)
        self.api_service = APIDemoService(pid, services=services, data_provider=dp)
        self.info_service = FrameworkInfoService(pid, services=services, data_provider=dp)
        self.mcp_service = MCPDemoService(pid, services=services, data_provider=dp)

    def _iter_cleanup_services(self):
        """返回需要执行卸载清理的服务实例（跳过未初始化的）"""
        return [
            s for s in (self.data_service, self.task_service, self.llm_service)
            if s is not None
        ]

    def _safe_cleanup_service(self, service) -> None:
        """调用单个服务的 cleanup，异常仅记日志不抛出（LoggerManager 不支持 exc_info）"""
        try:
            service.cleanup()
        except Exception as e:
            self._logger.error(
                "FrameworkAPIDemo",
                f"服务卸载清理失败: {e}\n{traceback.format_exc()}"
            )

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        """创建插件主控件（UI 构建由 MainWidget 完成；注入取词门面与插件 UUID）"""
        services = self._get_services()
        i18n = services.localization if services is not None else None
        widget = MainWidget(
            data_service=self.data_service,
            task_service=self.task_service,
            llm_service=self.llm_service,
            api_service=self.api_service,
            info_service=self.info_service,
            mcp_service=self.mcp_service,
            parent=parent,
            i18n=i18n,
            plugin_id=self.plugin_id,
        )
        self._main_widget = widget
        widget.append_log(widget.tr_text("main", "log.loaded"))
        widget.append_log(widget.tr_text("main", "log.plugin_id", id=self.plugin_id))
        return widget

    def _log(self, message: str):
        """插件加载早期日志：经 run_in_ui_thread 封送到 UI 线程转发给主控件

        替代原 SignalBridge：run_in_ui_thread 在 UI 线程直接执行、
        其他线程经队列投递到 UI 事件循环，语义与自建信号桥等价。
        """
        run_in_ui_thread(self._deliver_log, message)

    def _deliver_log(self, message: str):
        """将日志转发给主控件日志面板（控件未创建时忽略）"""
        if self._main_widget is not None:
            self._main_widget.append_log(message)
