"""
API Demo 核心业务逻辑

封装 PluginManager 调用，提供对其他插件 API 的发现和调用能力。
"""

from core.plugin.manager import PluginManager


class CoreService:
    """API Demo 核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._plugin_manager = PluginManager()

    def get_target_plugin_id(self, type_id: str) -> str | None:
        """通过类型 ID 获取插件实例 ID"""
        return self._plugin_manager.get_plugin_id_by_type_id(type_id)

    def get_plugin_api(self, plugin_id: str) -> dict | None:
        """获取指定插件的 API 信息"""
        return self._plugin_manager.get_plugin_api(plugin_id)

    def call_plugin_method(self, target_plugin_id: str, method_name: str, text: str):
        """调用其他插件的方法"""
        return self._plugin_manager.call_plugin_method(
            caller_id=self.plugin_id,
            plugin_id=target_plugin_id,
            method_name=method_name,
            text=text
        )

    def get_all_apis(self) -> dict:
        """获取所有已注册的 API"""
        return self._plugin_manager.get_all_apis()

    def get_all_function_tools(self) -> list:
        """获取所有 Function Tools"""
        return self._plugin_manager.get_all_function_tools()
