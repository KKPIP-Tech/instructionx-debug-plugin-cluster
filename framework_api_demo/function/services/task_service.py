"""
Framework API Demo 任务演示服务

演示 BackgroundTaskManager 接口（同步/异步/定时任务、查询、清理）。
"""

import time
from typing import Any, Dict

from utils.logging_tools import get_name

from .base import Service, _load_config


class TaskDemoService(Service):
    """演示 BackgroundTaskManager 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        config = _load_config()
        demo_cfg = config.get("demo", {})
        self.sync_seconds = demo_cfg.get("sync_task_seconds", 1)
        self.async_seconds = demo_cfg.get("async_task_seconds", 2)

    def create_sync_task(self, name: str = "sync_task") -> Dict[str, Any]:
        """演示创建同步任务"""
        def sync_func(seconds: int):
            time.sleep(seconds)
            return f"同步任务完成，耗时 {seconds} 秒"

        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=name,
                func=sync_func, args=(self.sync_seconds,),
            )
            return {"success": True, "task_id": task_id, "message": "同步任务已创建并执行"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_async_task(self, name: str = "async_task") -> Dict[str, Any]:
        """演示创建异步任务"""
        def async_func(seconds: int):
            time.sleep(seconds)
            return f"异步任务完成，耗时 {seconds} 秒"

        try:
            task_id = self.tm.register_async_task(
                plugin_id=self.plugin_id, name=name,
                func=async_func, args=(self.async_seconds,),
            )
            return {"success": True, "task_id": task_id, "message": "异步任务已创建"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_scheduled_task(self, name: str = "scheduled_task", interval: int = 60) -> Dict[str, Any]:
        """演示创建定时任务"""
        def scheduled_func():
            return "定时任务执行"

        try:
            task_id = self.tm.register_scheduled_task(
                plugin_id=self.plugin_id, name=name,
                func=scheduled_func, interval=interval,
            )
            return {"success": True, "task_id": task_id, "message": f"定时任务已创建，间隔 {interval} 秒"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def query_tasks(self) -> Dict[str, Any]:
        """演示查询任务"""
        try:
            all_tasks = self.tm.get_tasks_by_plugin(self.plugin_id)
            scheduled_tasks = self.tm.get_scheduled_tasks(self.plugin_id)
            return {
                "success": True,
                "tasks": [
                    {"task_id": t.task_id, "name": t.name, "status": t.status.value}
                    for t in all_tasks
                ],
                "scheduled_tasks": [
                    {"task_id": t.task_id, "name": t.name, "interval": t.interval, "enabled": t.enabled}
                    for t in scheduled_tasks
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def clear_completed(self) -> Dict[str, Any]:
        """演示清理已完成任务"""
        try:
            count = self.tm.clear_completed_tasks(self.plugin_id)
            return {"success": True, "message": f"已清理 {count} 个任务"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup(self) -> None:
        """卸载清理：注销本插件全部定时任务（异常仅记日志，不向外抛出）"""
        try:
            scheduled_tasks = self.tm.get_scheduled_tasks(self.plugin_id)
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：查询定时任务失败: {e}")
            return
        for task in scheduled_tasks:
            self._unregister_one(task.task_id)

    def _unregister_one(self, task_id: str) -> None:
        """注销单个定时任务，失败仅记日志"""
        try:
            self.tm.unregister_scheduled_task(task_id)
            self.logger.info(get_name(), f"卸载清理：已注销定时任务 {task_id}")
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：注销定时任务 {task_id} 失败: {e}")
