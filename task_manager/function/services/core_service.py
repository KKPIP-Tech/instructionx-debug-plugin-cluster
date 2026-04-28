"""
Task Manager Service - Business Logic Layer
All actual business logic resides here.
"""

import csv
import json
from datetime import datetime
from io import StringIO
from typing import Dict, List, Any, Optional

from core.data.data_provider import DataProvider, DataNamespace


class TaskService:
    """任务管理服务 - 业务逻辑层"""

    _TASK_KEY = "tasks"
    _STATISTICS_KEY = "statistics"
    _EVENT_KEY = "last_event"
    _STATUSES = ["pending", "in_progress", "completed", "cancelled"]
    _PRIORITIES = ["low", "normal", "high"]

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._data_provider = DataProvider()

    def add_task(self, title: str, description: str = "", priority: str = "normal") -> Dict[str, Any]:
        """添加新任务"""
        task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": priority,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        tasks = self._load_tasks()
        tasks.append(task)
        self._save_tasks(tasks)
        self._update_statistics()
        self._publish_event({
            "type": "task_added",
            "task_id": task_id,
            "timestamp": datetime.now().isoformat(),
        })
        return task

    def update_task_status(self, task_id: str, status: str) -> bool:
        """更新任务状态"""
        if status not in self._STATUSES:
            return False
        tasks = self._load_tasks()
        for task in tasks:
            if task["id"] == task_id:
                old_status = task["status"]
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat()
                self._save_tasks(tasks)
                self._update_statistics()
                self._publish_event({
                    "type": "status_changed",
                    "task_id": task_id,
                    "old_status": old_status,
                    "new_status": status,
                    "timestamp": datetime.now().isoformat(),
                })
                return True
        return False

    def get_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取任务列表，可按状态筛选"""
        tasks = self._load_tasks()
        if status and status in self._STATUSES:
            return [t for t in tasks if t["status"] == status]
        return tasks

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        tasks = self._load_tasks()
        original_count = len(tasks)
        tasks = [t for t in tasks if t["id"] != task_id]
        if len(tasks) < original_count:
            self._save_tasks(tasks)
            self._update_statistics()
            self._publish_event({
                "type": "task_deleted",
                "task_id": task_id,
                "timestamp": datetime.now().isoformat(),
            })
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        return self._data_provider.get_plugin_data(
            self.plugin_id,
            self._STATISTICS_KEY,
            DataNamespace.PUBLIC,
            {"total": 0, "pending": 0, "in_progress": 0, "completed": 0, "cancelled": 0},
        )

    def export_tasks(self, format: str = "json") -> str:
        """导出任务数据"""
        tasks = self.get_tasks()
        stats = self.get_statistics()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if format == "json":
            content = json.dumps(
                {"exported_at": datetime.now().isoformat(), "statistics": stats, "tasks": tasks},
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")
            filename = f"tasks_export_{timestamp}.json"
        elif format == "csv":
            output = StringIO()
            writer = csv.DictWriter(
                output, fieldnames=["id", "title", "description", "priority", "status", "created_at"]
            )
            writer.writeheader()
            writer.writerows(tasks)
            content = output.getvalue().encode("utf-8")
            filename = f"tasks_export_{timestamp}.csv"
        else:
            raise ValueError(f"不支持的导出格式: {format}")
        return self.save_task_attachment("export", filename, content)

    def save_task_attachment(self, task_id: str, filename: str, content: bytes) -> str:
        """保存任务附件"""
        attachment_filename = f"{task_id}_{filename}"
        return self._data_provider.save_asset(self.plugin_id, attachment_filename, content)

    def _load_tasks(self) -> List[Dict]:
        """加载任务列表"""
        return self._data_provider.get_plugin_data(
            self.plugin_id, self._TASK_KEY, DataNamespace.PRIVATE, []
        )

    def _save_tasks(self, tasks: List[Dict]):
        """保存任务列表"""
        self._data_provider.set_plugin_data(
            self.plugin_id, self._TASK_KEY, tasks, DataNamespace.PRIVATE
        )

    def _update_statistics(self):
        """更新任务统计信息并发布"""
        tasks = self._load_tasks()
        stats = {
            "total": len(tasks),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "cancelled": 0,
        }
        for task in tasks:
            status = task["status"]
            if status in stats:
                stats[status] += 1
        self._data_provider.publish(
            self.plugin_id, self._STATISTICS_KEY, stats, DataNamespace.PUBLIC
        )

    def _publish_event(self, event: Dict):
        """发布事件"""
        self._data_provider.publish(
            self.plugin_id, self._EVENT_KEY, event, DataNamespace.PUBLIC
        )
