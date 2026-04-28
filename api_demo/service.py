"""
API Demo 插件服务层

作为接口层，仅封装 function 子模块的方法，不包含任何业务逻辑和 UI 操作。
"""

from .function.services.core_service import CoreService as _Impl


class Service:
    """API Demo 服务类（接口层）"""

    def __init__(self, plugin_id: str):
        self._impl = _Impl(plugin_id)

    def get_target_plugin_id(self, type_id: str):
        return self._impl.get_target_plugin_id(type_id)

    def get_plugin_api(self, plugin_id: str):
        return self._impl.get_plugin_api(plugin_id)

    def call_plugin_method(self, target_plugin_id: str, method_name: str, text: str):
        return self._impl.call_plugin_method(target_plugin_id, method_name, text)

    def get_all_apis(self):
        return self._impl.get_all_apis()

    def get_all_function_tools(self):
        return self._impl.get_all_function_tools()
