"""
Framework API Demo 服务基类

统一持有 PluginServices 注入容器并解析框架服务依赖：
优先使用框架注入的 services（PluginServices），
缺失时回退对应框架单例（保证旧调用方式与独立测试场景可用）。
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core.interfaces import PluginServices
from core.data.data_provider import DataProvider
from core.task import BackgroundTaskManager
from core.llm.plugin_service import get_llm_plugin_service
from utils.logging_tools import LoggerManager, get_name


def _load_config() -> Dict[str, Any]:
    """从 config/default.json 加载配置"""
    config_path = Path(__file__).parent.parent.parent / "config" / "default.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


class Service:
    """服务基类：统一解析框架服务依赖（PluginServices 优先，单例兜底）"""

    def __init__(
        self,
        plugin_id: str,
        services: Optional[PluginServices] = None,
        data_provider: Optional[DataProvider] = None,
    ):
        self.plugin_id = plugin_id
        self.services = services
        self.dp = self._resolve_data_provider(services, data_provider)
        self.tm = self._resolve_task_manager(services)
        self.llm = self._resolve_llm_facade(services)
        self.logger = self._resolve_logger(services)
        # 多语言取词门面（ILocalizationFacade）：框架加载路径始终经
        # PluginServices.localization 注入；service.py 委托链等无注入路径为 None
        self._i18n = services.localization if services is not None else None
        # 事件通知回调（callable(str)）：工作线程回调产生的事件经它上抛，
        # 由 UI 层注入并自行负责线程封送（run_in_ui_thread）
        self._event_notifier: Optional[Callable[[str], None]] = None

    def set_event_notifier(self, notifier: Optional[Callable[[str], None]]) -> None:
        """注入事件的 UI 通知回调（callable(str)，由 UI 负责线程封送）"""
        self._event_notifier = notifier

    def _tr(self, group: str, key: str, /, default: str = "", **params) -> str:
        """取插件文案；门面未注入时回退中文默认文案

        服务层经跨插件 API / MCP 工具被外部调用时不保证有门面注入
        （如 service.py 委托链），回退 default 保持行为与改造前一致，
        避免调用方看到裸键名。

        参数:
            group: 语言文件分组名
            key: 分组内点分键名
            default: 门面缺失时的中文回退文案（可含与 params 对应的占位符）
            params: 命名占位符参数（对应模板中的 {name}）
        """
        if self._i18n is not None:
            return self._i18n.tr(group, key, **params)
        if default:
            return default.format(**params)
        return key

    def _notify_event(self, message: str) -> None:
        """上抛事件：有 notifier 时通知 UI，否则仅记日志"""
        if self._event_notifier is not None:
            self._event_notifier(message)
        else:
            self.logger.info(get_name(), f"服务事件（无 UI 通知器）: {message}")

    @staticmethod
    def _resolve_data_provider(
        services: Optional[PluginServices],
        data_provider: Optional[DataProvider],
    ) -> DataProvider:
        """解析 DataProvider：注入优先；缺失时回退单例（兼容旧构造与独立测试）"""
        if services is not None and services.data_provider is not None:
            return services.data_provider
        if data_provider is not None:
            return data_provider
        return DataProvider()

    @staticmethod
    def _resolve_task_manager(services: Optional[PluginServices]) -> BackgroundTaskManager:
        """解析 BackgroundTaskManager：注入优先，缺失时回退单例"""
        if services is not None and services.task_manager is not None:
            return services.task_manager
        return BackgroundTaskManager()

    @staticmethod
    def _resolve_llm_facade(services: Optional[PluginServices]):
        """解析 llm_facade：注入优先，缺失时回退 LLMPluginService 单例"""
        if services is not None and services.llm_facade is not None:
            return services.llm_facade
        return get_llm_plugin_service()

    @staticmethod
    def _resolve_logger(services: Optional[PluginServices]) -> LoggerManager:
        """解析 Logger：注入优先，缺失时回退 LoggerManager 单例"""
        if services is not None and services.logger is not None:
            return services.logger
        return LoggerManager()
