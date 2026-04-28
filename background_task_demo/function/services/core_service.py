"""Background Task Demo Core Service"""

from typing import Dict, List, Any, Optional, Callable

from core.task.background_task import BackgroundTaskManager


class CoreService:
    """后台任务演示核心服务

    承载所有后台任务管理的实际业务逻辑。
    """

    def __init__(self):
        self._task_manager = BackgroundTaskManager()

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有后台任务"""
        tasks = self._task_manager.get_all_tasks()
        return [task.to_dict() for task in tasks]

    def get_tasks_by_plugin(self, plugin_id: str) -> List[Dict[str, Any]]:
        """按插件 UUID 获取任务"""
        tasks = self._task_manager.get_tasks_by_plugin(plugin_id)
        return [task.to_dict() for task in tasks]

    def get_scheduled_tasks(self, plugin_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取定时任务"""
        tasks = self._task_manager.get_scheduled_tasks(plugin_id)
        return [task.to_dict() for task in tasks]

    def get_task_status(self, task_id: str) -> Optional[str]:
        """获取任务状态"""
        status = self._task_manager.get_task_status(task_id)
        return status.value if status else None

    def register_sync_task(
        self,
        plugin_id: str,
        name: str,
        func: Callable,
        callback: Optional[Callable] = None,
        args: tuple = (),
        kwargs: dict = None
    ) -> str:
        """注册同步任务"""
        if kwargs is None:
            kwargs = {}
        return self._task_manager.register_sync_task(
            plugin_id=plugin_id,
            name=name,
            func=func,
            callback=callback,
            args=args,
            kwargs=kwargs
        )

    def register_async_task(
        self,
        plugin_id: str,
        name: str,
        func: Callable,
        callback: Optional[Callable] = None,
        args: tuple = (),
        kwargs: dict = None
    ) -> str:
        """注册异步任务"""
        if kwargs is None:
            kwargs = {}
        return self._task_manager.register_async_task(
            plugin_id=plugin_id,
            name=name,
            func=func,
            callback=callback,
            args=args,
            kwargs=kwargs
        )

    def register_scheduled_task(
        self,
        plugin_id: str,
        name: str,
        func: Callable,
        interval: int,
        callback: Optional[Callable] = None,
        args: tuple = (),
        kwargs: dict = None
    ) -> str:
        """注册定时任务"""
        return self._task_manager.register_scheduled_task(
            plugin_id=plugin_id,
            name=name,
            func=func,
            interval=interval,
            callback=callback,
            args=args,
            kwargs=kwargs or {}
        )

    def register_scheduled_task_factory(
        self,
        plugin_id: str,
        func: Callable,
        callback: Optional[Callable] = None
    ) -> None:
        """注册定时任务工厂"""
        self._task_manager.register_scheduled_task_factory(
            plugin_id=plugin_id,
            func=func,
            callback=callback
        )

    def restore_scheduled_tasks(self, plugin_id: str) -> int:
        """恢复定时任务"""
        return self._task_manager.restore_scheduled_tasks(plugin_id)

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self._task_manager.cancel_task(task_id)

    def clear_completed_tasks(self, plugin_id: Optional[str] = None) -> int:
        """清理已完成的任务"""
        return self._task_manager.clear_completed_tasks(plugin_id)

    def enable_scheduled_task(self, task_id: str) -> bool:
        """启用定时任务"""
        return self._task_manager.enable_scheduled_task(task_id)

    def disable_scheduled_task(self, task_id: str) -> bool:
        """禁用定时任务"""
        return self._task_manager.disable_scheduled_task(task_id)
