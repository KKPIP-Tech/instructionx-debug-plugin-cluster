"""
Local Server 插件信息

定义插件元数据、API 接口、技能图标等信息。
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class LocalServerPluginInfo(IPluginInfo):
    """本地HTTP服务器插件信息"""

    @property
    def version(self) -> PluginVersion:
        """插件版本"""
        return PluginVersion.from_string("release.1.0.0")

    @property
    def developer(self) -> str:
        """开发者名称"""
        return "InstructionX Team"

    @property
    def developer_email(self) -> str:
        return "support@instructionx.com"

    @property
    def developer_website(self) -> str:
        return "https://instructionx.com"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "提供本地HTTP服务器功能，可用于测试Webhook、API等场景"

    @property
    def service_api(self) -> Dict[str, Any]:
        """插件API定义"""
        def api(name, params, returns):
            return {"description": name, "parameters": params, "returns": returns}
        return {
            "get_status": api("获取服务器状态", {}, {"type": "dict", "description": "包含 is_running, request_count, task_id"}),
            "get_default_port": api("获取默认端口", {}, {"type": "int"}),
            "get_port_range": api("获取端口范围", {}, {"type": "tuple", "description": "(最小端口, 最大端口)"}),
            "increment_request_count": api("增加请求计数", {}, {"type": "None"}),
            "set_running": api("设置服务器运行状态", {"is_running": {"type": "bool", "required": True}, "task_id": {"type": "str", "required": False}}, {"type": "None"}),
            "save_data": api("保存数据到 DataProvider", {"key": {"type": "str", "required": True}, "value": {"type": "any", "required": True}}, {"type": "None"}),
            "load_data": api("从 DataProvider 加载数据", {"key": {"type": "str", "required": True}, "default": {"type": "any", "required": False}}, {"type": "any", "description": "存储的值或默认值"})
        }

    @property
    def skill_icon(self) -> PluginIcon:
        """技能按钮图标"""
        return PluginIcon.builtin("SP_ComputerIcon")

    @property
    def skill_description(self) -> str:
        """技能简短描述"""
        return "本地HTTP服务器"

    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["开发工具", "服务器", "HTTP"]

    @property
    def dependencies(self) -> Dict[str, str]:
        """插件依赖"""
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "local-server"
