"""
Framework API Demo 跨插件 API 演示服务

演示 PluginManager 接口（插件查询、API 查询、跨插件调用）。
"""

from typing import Any, Dict

from core.plugin.manager import PluginManager

from .base import Service


class APIDemoService(Service):
    """演示 PluginManager API 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        self.plugin_manager = PluginManager()

    def get_all_plugins(self) -> Dict[str, Any]:
        """演示获取所有插件"""
        try:
            plugins = self.plugin_manager.get_all_plugins()
            return {
                "success": True,
                "count": len(plugins),
                "plugins": [{"name": p.plugin_name, "id": p.plugin_id} for p in plugins],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_plugin_by_id(self, plugin_id: str = None) -> Dict[str, Any]:
        """演示通过 ID 获取插件"""
        try:
            if not plugin_id:
                plugins = self.plugin_manager.get_all_plugins()
                if plugins:
                    plugin_id = plugins[0].plugin_id
            plugin = self.plugin_manager.get_plugin_by_id(plugin_id)
            if plugin:
                return {
                    "success": True,
                    "plugin": {"name": plugin.plugin_name, "id": plugin.plugin_id},
                }
            return {"success": False, "error": "插件不存在"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_apis(self) -> Dict[str, Any]:
        """演示获取所有注册的 API"""
        try:
            apis = self.plugin_manager.get_all_apis()
            return {
                "success": True,
                "count": len(apis),
                "apis": {
                    pid: {
                        "name": info["plugin_name"],
                        "methods": list(info.get("methods", [])),
                    }
                    for pid, info in apis.items()
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_function_tools(self) -> Dict[str, Any]:
        """演示获取所有 Function Tools（MCP/OpenAI 格式）"""
        try:
            tools = self.plugin_manager.get_all_function_tools()
            return {"success": True, "count": len(tools), "tools": tools}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_api_description(self, plugin_id: str = None, method_name: str = None) -> Dict[str, Any]:
        """演示获取 API 描述"""
        try:
            if not plugin_id:
                apis = self.plugin_manager.get_all_apis()
                if apis:
                    plugin_id = list(apis.keys())[0]
            desc = self.plugin_manager.get_api_description(plugin_id, method_name)
            return {"success": True, "description": desc}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def call_plugin_method(self, plugin_id: str = None, method_name: str = None, **kwargs) -> Dict[str, Any]:
        """演示跨插件调用方法"""
        try:
            if not plugin_id or not method_name:
                return {"success": False, "error": "需要指定 plugin_id 和 method_name"}
            result = self.plugin_manager.call_plugin_method(
                caller_id=self.plugin_id,
                plugin_id=plugin_id,
                method_name=method_name,
                **kwargs,
            )
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}
