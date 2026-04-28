"""
后台任务演示器插件信息
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class BackgroundTaskDemoInfo(IPluginInfo):
    """后台任务演示器插件元数据"""

    @property
    def version(self) -> PluginVersion:
        return PluginVersion.from_string("release.1.0.0")

    @property
    def developer(self) -> str:
        return "InstructionX Team"

    @property
    def developer_email(self) -> str:
        return "support@instructionx.com"

    @property
    def developer_website(self) -> str:
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "演示 BackgroundTask 后台任务模块的所有功能，包括同步任务、异步任务、定时任务和任务状态管理"

    @property
    def service_api(self) -> Dict[str, Any]:
        """定义插件提供的 API"""
        def api(desc: str, params: Dict, returns: Dict) -> Dict:
            return {"description": desc, "parameters": params, "returns": returns}
        return {
            "get_all_tasks": api("获取所有后台任务", {}, {"type": "list", "description": "任务列表"}),
            "get_tasks_by_plugin": api("按插件 UUID 获取任务", {"plugin_id": {"type": "str", "description": "插件 UUID", "required": True}}, {"type": "list", "description": "任务列表"}),
            "get_scheduled_tasks": api("获取定时任务列表", {"plugin_id": {"type": "str", "description": "插件 UUID", "required": False}}, {"type": "list", "description": "定时任务列表"}),
            "get_task_status": api("获取任务状态", {"task_id": {"type": "str", "description": "任务 ID", "required": True}}, {"type": "str", "description": "状态值"}),
            "register_sync_task": api("注册同步任务", {"plugin_id": {"type": "str", "required": True}, "name": {"type": "str", "required": True}, "func": {"type": "callable", "required": True}, "callback": {"type": "callable", "required": False}, "args": {"type": "tuple", "required": False}, "kwargs": {"type": "dict", "required": False}}, {"type": "str", "description": "任务 ID"}),
            "register_async_task": api("注册异步任务", {"plugin_id": {"type": "str", "required": True}, "name": {"type": "str", "required": True}, "func": {"type": "callable", "required": True}, "callback": {"type": "callable", "required": False}, "args": {"type": "tuple", "required": False}, "kwargs": {"type": "dict", "required": False}}, {"type": "str", "description": "任务 ID"}),
            "register_scheduled_task": api("注册定时任务", {"plugin_id": {"type": "str", "required": True}, "name": {"type": "str", "required": True}, "func": {"type": "callable", "required": True}, "interval": {"type": "int", "required": True}, "callback": {"type": "callable", "required": False}, "args": {"type": "tuple", "required": False}, "kwargs": {"type": "dict", "required": False}}, {"type": "str", "description": "任务 ID"}),
            "register_scheduled_task_factory": api("注册定时任务工厂", {"plugin_id": {"type": "str", "required": True}, "func": {"type": "callable", "required": True}, "callback": {"type": "callable", "required": False}}, {"type": "null"}),
            "restore_scheduled_tasks": api("恢复定时任务", {"plugin_id": {"type": "str", "required": True}}, {"type": "int", "description": "恢复数量"}),
            "cancel_task": api("取消任务", {"task_id": {"type": "str", "required": True}}, {"type": "bool"}),
            "clear_completed_tasks": api("清理已完成任务", {"plugin_id": {"type": "str", "required": False}}, {"type": "int", "description": "清理数量"}),
            "enable_scheduled_task": api("启用定时任务", {"task_id": {"type": "str", "required": True}}, {"type": "bool"}),
            "disable_scheduled_task": api("禁用定时任务", {"task_id": {"type": "str", "required": True}}, {"type": "bool"})
        }

    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_MediaPause")

    @property
    def skill_description(self) -> str:
        return "后台任务演示"

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "background-task-demo"

    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["demo", "background-task", "task-manager", "demonstration"]

    @property
    def dependencies(self) -> Dict[str, str]:
        return {}
