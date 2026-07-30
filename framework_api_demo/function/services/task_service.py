"""
Framework API Demo 任务演示服务

演示 BackgroundTaskManager 接口（同步/异步/定时/长期任务、取消、查询、清理）。
任务回调均在工作线程执行，UI 通知经注入的 event_notifier 上抛，
由 UI 层自行封送到 UI 线程。
"""

import threading
import time
from typing import Any, Callable, Dict, Optional

from utils.logging_tools import get_name

from .base import Service, _load_config

# 长期任务演示：每次循环休眠秒数（每秒计数 +1）
LONG_TASK_TICK_SECONDS = 1


class TaskDemoService(Service):
    """演示 BackgroundTaskManager 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        config = _load_config()
        demo_cfg = config.get("demo", {})
        self.sync_seconds = demo_cfg.get("sync_task_seconds", 1)
        self.async_seconds = demo_cfg.get("async_task_seconds", 2)
        self._event_notifier: Optional[Callable[[str], None]] = None

    def set_event_notifier(self, notifier: Optional[Callable[[str], None]]) -> None:
        """注入任务事件的 UI 通知回调（callable(str)，由 UI 负责线程封送）"""
        self._event_notifier = notifier

    def _notify_event(self, message: str) -> None:
        """上抛任务事件：有 notifier 时通知 UI，否则仅记日志"""
        if self._event_notifier is not None:
            self._event_notifier(message)
        else:
            self.logger.info(get_name(), f"任务事件（无 UI 通知器）: {message}")

    def _make_completion_callback(self, task_name: str) -> Callable:
        """构造任务完成回调（工作线程执行）：经 notifier 上抛 + 记日志，异常不外抛"""

        def on_completed(task_id: str, status, result, error) -> None:
            try:
                message = f"任务回调: {task_name} [{status}] 结果={result} 错误={error}"
                self._notify_event(message)
                self.logger.info(get_name(), f"任务完成回调 {task_name}({task_id}): {message}")
            except Exception as e:
                self.logger.error(get_name(), f"任务完成回调处理失败 {task_name}: {e}")

        return on_completed

    def create_sync_task(self, name: str = "sync_task") -> Dict[str, Any]:
        """演示创建同步任务（带完成回调）"""
        def sync_func(seconds: int):
            time.sleep(seconds)
            return f"同步任务完成，耗时 {seconds} 秒"

        try:
            task_id = self.tm.register_sync_task(
                plugin_id=self.plugin_id, name=name,
                func=sync_func, args=(self.sync_seconds,),
                callback=self._make_completion_callback(name),
            )
            return {"success": True, "task_id": task_id, "message": "同步任务已创建并执行"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_async_task(self, name: str = "async_task") -> Dict[str, Any]:
        """演示创建异步任务（带完成回调）"""
        def async_func(seconds: int):
            time.sleep(seconds)
            return f"异步任务完成，耗时 {seconds} 秒"

        try:
            task_id = self.tm.register_async_task(
                plugin_id=self.plugin_id, name=name,
                func=async_func, args=(self.async_seconds,),
                callback=self._make_completion_callback(name),
            )
            if task_id is None:
                return {"success": False, "error": "任务管理器已关闭，无法创建任务"}
            return {"success": True, "task_id": task_id, "message": "异步任务已创建"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_scheduled_task(self, name: str = "scheduled_task", interval: int = 60) -> Dict[str, Any]:
        """演示创建定时任务（带完成回调）"""
        def scheduled_func():
            return "定时任务执行"

        try:
            task_id = self.tm.register_scheduled_task(
                plugin_id=self.plugin_id, name=name,
                func=scheduled_func, interval=interval,
                callback=self._make_completion_callback(name),
            )
            if task_id is None:
                return {"success": False, "error": "任务管理器已关闭，无法创建任务"}
            return {"success": True, "task_id": task_id, "message": f"定时任务已创建，间隔 {interval} 秒"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  长期任务
    # ------------------------------------------------------------------

    def create_long_running_task(self, name: str = "long_task") -> Dict[str, Any]:
        """演示创建长期任务

        func 为循环计数（每秒 +1）。框架不向 func 注入停止信号：
        stop_long_running_task 只会调用 stop_callback 并尝试 future.cancel()
        （对已运行任务无效），因此 func 通过闭包共享的 stop_event 自行感知
        停止信号并优雅退出，stop_callback 负责置位该事件。
        """
        stop_event = threading.Event()
        task_holder: Dict[str, str] = {}

        def long_func() -> str:
            counter = 0
            while not stop_event.is_set():
                time.sleep(LONG_TASK_TICK_SECONDS)
                counter += 1
                self._report_long_status(task_holder, f"已运行 {counter} 秒")
            return f"长期任务优雅停止，共计数 {counter}"

        try:
            task_id = self.tm.register_long_running_task(
                plugin_id=self.plugin_id, name=name,
                func=long_func,
                callback=self._make_completion_callback(name),
                stop_callback=lambda: self._on_long_task_stop(name, stop_event),
                status_callback=lambda tid, status: self._on_long_task_status(name, tid, status),
                auto_restart=False,
            )
            if task_id is None:
                return {"success": False, "error": "任务管理器已关闭，无法创建任务"}
            task_holder["task_id"] = task_id
            return {"success": True, "task_id": task_id, "message": "长期任务已创建（每秒计数 +1）"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _report_long_status(self, task_holder: Dict[str, str], status: str) -> None:
        """向框架上报长期任务状态（触发 status_callback）；task_id 未就绪时跳过"""
        task_id = task_holder.get("task_id")
        if not task_id:
            return
        try:
            self.tm.update_long_running_task_status(task_id, status)
        except Exception as e:
            self.logger.warning(get_name(), f"更新长期任务状态失败 {task_id}: {e}")

    def _on_long_task_stop(self, name: str, stop_event: threading.Event) -> None:
        """长期任务停止回调：置位停止事件使 func 循环退出，并上抛通知"""
        try:
            stop_event.set()
            self._notify_event(f"长期任务收到停止信号: {name}")
            self.logger.info(get_name(), f"长期任务停止回调: {name}")
        except Exception as e:
            self.logger.error(get_name(), f"长期任务停止回调处理失败 {name}: {e}")

    def _on_long_task_status(self, name: str, task_id: str, status: str) -> None:
        """长期任务状态回调（工作线程）：经 notifier 上抛 + 记日志，异常不外抛"""
        try:
            self._notify_event(f"长期任务状态: {name} -> {status}")
            self.logger.info(get_name(), f"长期任务状态回调 {name}({task_id}): {status}")
        except Exception as e:
            self.logger.error(get_name(), f"长期任务状态回调处理失败 {name}: {e}")

    def stop_long_task(self, task_id: str) -> Dict[str, Any]:
        """演示停止长期任务（触发 stop_callback，func 经 stop_event 优雅退出）"""
        try:
            stopped = self.tm.stop_long_running_task(task_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if stopped:
            return {"success": True, "message": f"长期任务 {task_id} 已停止"}
        return {"success": False, "error": f"长期任务 {task_id} 不存在或未在运行"}

    # ------------------------------------------------------------------
    #  任务取消 / 状态查询
    # ------------------------------------------------------------------

    def cancel_task_demo(self, task_id: str) -> Dict[str, Any]:
        """演示取消任务（对已在执行的任务仅标记 CANCELLED，不中断执行）"""
        try:
            cancelled = self.tm.cancel_task(task_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if cancelled:
            return {"success": True, "message": f"任务 {task_id} 已标记取消"}
        return {"success": False, "error": f"任务 {task_id} 不在运行列表中"}

    def get_task_status_demo(self, task_id: str) -> Dict[str, Any]:
        """演示查询任务状态与详情"""
        try:
            status = self.tm.get_task_status(task_id)
            task = self.tm.get_task(task_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if task is None:
            return {"success": False, "error": f"任务 {task_id} 不存在"}
        return {
            "success": True,
            "task_id": task_id,
            "name": task.name,
            "status": status.value if status is not None else "未知",
            "result": str(task.result),
            "error": str(task.error),
        }

    # ------------------------------------------------------------------
    #  定时任务控制
    # ------------------------------------------------------------------

    def set_scheduled_enabled(self, task_id: str, enabled: bool) -> Dict[str, Any]:
        """演示启用/禁用定时任务"""
        action = "启用" if enabled else "禁用"
        try:
            if enabled:
                done = self.tm.enable_scheduled_task(task_id)
            else:
                done = self.tm.disable_scheduled_task(task_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if done:
            return {"success": True, "message": f"定时任务 {task_id} 已{action}"}
        return {"success": False, "error": f"定时任务 {task_id} 不存在"}

    def unregister_scheduled(self, task_id: str) -> Dict[str, Any]:
        """演示注销定时任务（从运行列表与持久化存储中移除）"""
        try:
            done = self.tm.unregister_scheduled_task(task_id)
        except Exception as e:
            return {"success": False, "error": str(e)}
        if done:
            return {"success": True, "message": f"定时任务 {task_id} 已注销"}
        return {"success": False, "error": f"定时任务 {task_id} 不在运行列表中"}

    # ------------------------------------------------------------------
    #  查询与清理
    # ------------------------------------------------------------------

    def query_tasks(self) -> Dict[str, Any]:
        """演示查询任务（普通任务 + 定时任务 + 长期任务）"""
        try:
            all_tasks = self.tm.get_tasks_by_plugin(self.plugin_id)
            scheduled_tasks = self.tm.get_scheduled_tasks(self.plugin_id)
            long_tasks = self.tm.get_long_running_tasks(self.plugin_id)
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
                "long_running_tasks": [
                    {"task_id": t.task_id, "name": t.name, "status": t.current_status}
                    for t in long_tasks
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
        """卸载清理：停止全部长期任务并注销全部定时任务（异常仅记日志）"""
        self._stop_all_long_tasks()
        self._unregister_all_scheduled()

    def _stop_all_long_tasks(self) -> None:
        """停止本插件全部长期任务，逐项容错"""
        try:
            long_tasks = self.tm.get_long_running_tasks(self.plugin_id)
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：查询长期任务失败: {e}")
            return
        for task in long_tasks:
            self._stop_one_long_task(task.task_id)

    def _stop_one_long_task(self, task_id: str) -> None:
        """停止单个长期任务，失败仅记日志"""
        try:
            self.tm.stop_long_running_task(task_id)
            self.logger.info(get_name(), f"卸载清理：已停止长期任务 {task_id}")
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：停止长期任务 {task_id} 失败: {e}")

    def _unregister_all_scheduled(self) -> None:
        """注销本插件全部定时任务，逐项容错"""
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
