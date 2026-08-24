"""
Blueprint OpenCV 插件入口（胶水层）

基于 InstructionX_UIKit Blueprint 的 OpenCV 节点化图像处理蓝图编辑器。
本模块仅负责插件生命周期、节点类型注册、服务初始化与主控件创建；
全部 UI 构建与事件处理位于 ui/，业务逻辑位于 function/。
"""

import traceback
from typing import Callable, Optional

from PySide6.QtWidgets import QWidget

from core.data.data_provider import DataProvider, DataProviderError
from core.interfaces import ILocalizationFacade, PluginServices
from core.plugin.plugin_interface import IPlugin
from utils.logging_tools import LoggerManager

from .service import BlueprintOpenCVService
from .function import runtime_registry
from .ui.main_widget import MainWidget
from .ui.node_bootstrap import ensure_node_types_registered

# 日志模块标识
LOG_TAG = "BlueprintOpenCV"


class BlueprintOpenCVPlugin(IPlugin):
    """Blueprint OpenCV 插件（胶水层）：组装 service / function / ui 三层"""

    _logger = LoggerManager()

    def __init__(self, services: Optional[PluginServices] = None):
        super().__init__()
        # 框架加载时经构造函数注入 PluginServices（见 PluginManager._instantiate_plugin）
        self._injected_services = services
        self._service: Optional[BlueprintOpenCVService] = None
        self._main_widget: Optional[MainWidget] = None

    @property
    def plugin_name(self) -> str:
        return "Blueprint\nOpenCV"

    def on_plugin_loaded(self, plugin_id=None, **kwargs):
        """插件加载完成后：注册节点类型、注册数据命名空间、初始化服务（仅执行一次）"""
        self._register_node_types()
        data_provider = self._get_data_provider()
        self._register_with_provider(data_provider)
        self._service = BlueprintOpenCVService(
            plugin_id=self.plugin_id,
            data_provider=data_provider,
        )

    def on_plugin_unloaded(self):
        """插件卸载清理：停止管线、断开信号、释放共享运行实例与引用，逐项容错记日志"""
        self._safe_execute("停止管线", self._stop_pipeline)
        self._safe_execute("断开服务信号", self._disconnect_signals)
        self._safe_execute("清理共享运行实例", self._drop_runtime)
        self._main_widget = None
        self._service = None

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        """创建插件主控件（UI 构建由 ui.main_widget.MainWidget 完成）"""
        widget = MainWidget(
            self._require_service(),
            parent=parent,
            i18n=self._get_i18n(),
            plugin_id=self.plugin_id,
        )
        self._main_widget = widget
        return widget

    # ------------------------------------------------------------------
    #  初始化
    # ------------------------------------------------------------------

    def _register_node_types(self):
        """注册全部节点类型（ui.node_bootstrap 幂等 + 同名冲突纠正，热重载安全）"""
        try:
            ensure_node_types_registered(self._get_i18n())
        except Exception as e:
            self._logger.error(
                LOG_TAG, f"注册节点类型失败: {e}\n{traceback.format_exc()}",
            )

    def _register_with_provider(self, data_provider: DataProvider):
        """向 DataProvider 注册插件并设置活跃实例"""
        plugin_id = self.plugin_id
        try:
            data_provider.register_plugin(plugin_id, "BlueprintOpenCV")
        except DataProviderError as e:
            err = str(e)
            if "已存在" not in err and "exists" not in err.lower():
                self._logger.error(LOG_TAG, f"注册插件失败: {err}")
                return
        try:
            data_provider.set_active_instance(plugin_id)
        except DataProviderError as e:
            self._logger.error(LOG_TAG, f"设置活跃实例失败: {e}")

    def _require_service(self) -> BlueprintOpenCVService:
        """取服务实例；on_plugin_loaded 未执行时兜底创建（容错独立运行场景）"""
        if self._service is None:
            self._service = BlueprintOpenCVService(
                plugin_id=self.plugin_id,
                data_provider=self._get_data_provider(),
            )
        return self._service

    def _get_services(self) -> Optional[PluginServices]:
        """获取 PluginServices：优先构造注入，其次框架注入的 _services 实例属性"""
        if self._injected_services is not None:
            return self._injected_services
        return getattr(self, '_services', None)

    def _get_i18n(self) -> Optional[ILocalizationFacade]:
        """获取本插件的取词门面（services.localization，未注入时返回 None）"""
        services = self._get_services()
        if services is None:
            return None
        return getattr(services, 'localization', None)

    def _get_data_provider(self) -> DataProvider:
        """获取 DataProvider 实例（优先框架注入的；取不到回退单例保证容错）"""
        services = self._get_services()
        if services and getattr(services, 'data_provider', None):
            return services.data_provider
        return DataProvider()

    # ------------------------------------------------------------------
    #  卸载清理
    # ------------------------------------------------------------------

    def _stop_pipeline(self):
        """请求停止运行中的管线（服务未初始化时跳过）"""
        if self._service is not None:
            self._service.shutdown()

    def _drop_runtime(self):
        """释放本插件的共享运行实例（runtime_registry），热重载后可干净重建"""
        runtime_registry.drop_pipeline_runtime(self.plugin_id)

    def _disconnect_signals(self):
        """断开服务全部 Qt 信号连接（无连接时 disconnect 抛 TypeError，逐项容错）"""
        if self._service is None:
            return
        signals = (
            self._service.preview_ready,
            self._service.node_status_changed,
            self._service.run_finished,
        )
        for signal in signals:
            self._safe_execute("断开信号连接", signal.disconnect)

    def _safe_execute(self, action: str, func: Callable[[], None]) -> None:
        """执行单项清理动作，异常仅记日志不向外逃逸（卸载流程不中断）"""
        try:
            func()
        except Exception as e:
            self._logger.error(
                LOG_TAG, f"{action}失败: {e}\n{traceback.format_exc()}",
            )
