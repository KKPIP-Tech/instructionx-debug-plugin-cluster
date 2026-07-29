"""
API 调用演示插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class ApiDemoPluginInfo(IPluginInfo):
    """API 调用演示插件元数据"""

    @property
    def version(self) -> PluginVersion:
        """插件版本"""
        return PluginVersion.from_string("release.1.1.0")

    @property
    def developer(self) -> str:
        """开发者名称"""
        return "KKPIP-Tech"

    @property
    def developer_email(self) -> str:
        """开发者邮箱"""
        return "support@example.com"

    @property
    def developer_website(self) -> str:
        """开发者网站"""
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        """是否免费"""
        return True

    @property
    def description(self) -> str:
        """插件详细描述"""
        return (
            "API 调用演示插件展示如何使用 PluginManager 的 API 调用功能。"
            "演示内容包括：如何通过 PluginManager 调用其他插件的方法、"
            "如何获取插件 ID、如何查询可用的 API 方法、如何处理 API 调用错误、"
            "如何获取 Function Tools 定义。"
        )

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "api-demo"

    @property
    def service_api(self) -> Dict[str, Any]:
        """Service API 定义"""
        return {
            "get_target_plugin_id": self._api("通过插件类型 ID 获取插件实例 ID",
                {"type_id": {"type": "str", "description": "插件类型标识符", "required": True}},
                {"type": "str", "description": "插件实例 ID，未找到返回 None"}),
            "get_plugin_api": self._api("获取指定插件的 API 信息",
                {"plugin_id": {"type": "str", "description": "插件实例 ID", "required": True}},
                {"type": "dict", "description": "插件 API 信息字典"}),
            "call_plugin_method": self._api("调用其他插件的方法",
                {"target_plugin_id": {"type": "str"}, "method_name": {"type": "str"}, "text": {"type": "str"}},
                {"type": "any"}),
            "get_all_apis": self._api("获取所有已注册的 API", {}, {"type": "dict"}),
            "get_all_function_tools": self._api("获取所有 Function Tools", {}, {"type": "list"})
        }

    def _api(self, desc: str, params: Dict, returns: Dict) -> Dict:
        return {"description": desc, "parameters": params, "returns": returns}

    @property
    def skill_icon(self) -> PluginIcon:
        """插件图标配置"""
        return PluginIcon.builtin("SP_MessageBoxQuestion")

    @property
    def skill_description(self) -> str:
        """插件简短描述"""
        return "演示插件间 API 调用"

    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["demo", "api", "tutorial", "example"]

    @property
    def dependencies(self) -> Dict[str, str]:
        """依赖项（格式: {插件类型ID: 版本约束}）"""
        return {}
