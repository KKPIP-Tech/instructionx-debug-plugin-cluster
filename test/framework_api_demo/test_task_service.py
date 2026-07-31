# -*- coding: utf-8 -*-
"""TaskDemoService 任务演示服务测试（查询类方法为主）。

覆盖 function/services/task_service.py 中可在测试进程安全执行的方法：
- get_interval_config：配置读取（config/default.json 的 task 段）；
- query_tasks / clear_completed：空插件 id 下的查询与清理；
- get_task_status_demo / cancel_task_demo / set_scheduled_enabled /
  unregister_scheduled / stop_long_task：不存在任务 id 的错误路径；
- create_sync_task / create_scheduled_task 的正常路径及其后续的
  状态查询、启停、注销（fixture 负责清理残留任务）。

任务创建走 BackgroundTaskManager 单例，但仅使用隔离 plugin_id，
不在测试中长期驻留任何任务。
"""


class TestIntervalConfig:
    """定时任务间隔配置"""

    def test_interval_config_matches_default_json(self, task_service):
        """应返回 config/default.json 声明的 minimum/maximum/default"""
        config = task_service.get_interval_config()
        assert config == {"minimum": 5, "maximum": 3600, "default": 60}


class TestQueryAndClear:
    """查询与清理（隔离 plugin_id 下应为空集）"""

    def test_query_tasks_empty_for_fresh_plugin(self, task_service):
        """未创建任务时三类列表均应为空"""
        result = task_service.query_tasks()
        assert result["success"] is True
        assert result["tasks"] == []
        assert result["scheduled_tasks"] == []
        assert result["long_running_tasks"] == []

    def test_clear_completed_returns_zero(self, task_service):
        """无已完成任务时清理计数应为 0"""
        result = task_service.clear_completed()
        assert result["success"] is True
        assert "0" in result["message"]


class TestNonexistentTaskErrors:
    """对不存在任务 id 的操作应返回 success=False 而非抛异常"""

    def test_get_status_nonexistent(self, task_service):
        """查询不存在任务的状态应返回「不存在」错误"""
        result = task_service.get_task_status_demo("pytest-no-such-task")
        assert result["success"] is False
        assert "不存在" in result["error"]

    def test_cancel_nonexistent(self, task_service):
        """取消不存在任务应返回「不在运行列表中」错误"""
        result = task_service.cancel_task_demo("pytest-no-such-task")
        assert result["success"] is False
        assert "不在运行列表中" in result["error"]

    def test_set_scheduled_enabled_nonexistent(self, task_service):
        """启用/禁用不存在的定时任务应返回「不存在」错误"""
        for enabled in (True, False):
            result = task_service.set_scheduled_enabled(
                "pytest-no-such-task", enabled,
            )
            assert result["success"] is False
            assert "不存在" in result["error"]

    def test_unregister_scheduled_nonexistent(self, task_service):
        """注销不存在的定时任务应返回「不在运行列表中」错误"""
        result = task_service.unregister_scheduled("pytest-no-such-task")
        assert result["success"] is False
        assert "不在运行列表中" in result["error"]

    def test_stop_long_task_nonexistent(self, task_service):
        """停止不存在的长期任务应返回「不存在或未在运行」错误"""
        result = task_service.stop_long_task("pytest-no-such-task")
        assert result["success"] is False
        assert "不存在" in result["error"]


class TestSyncTaskLifecycle:
    """同步任务的创建与状态查询"""

    def test_create_sync_task_success(self, task_service):
        """创建同步任务应成功并返回 task_id"""
        result = task_service.create_sync_task()
        assert result["success"] is True
        assert result["task_id"]

    def test_created_task_appears_in_query(self, task_service):
        """创建的任务应出现在 query_tasks 的普通任务列表中"""
        created = task_service.create_sync_task()
        result = task_service.query_tasks()
        matches = [t for t in result["tasks"] if t["task_id"] == created["task_id"]]
        assert len(matches) == 1
        assert matches[0]["name"] == "sync_task"
        assert matches[0]["status"]

    def test_get_status_of_created_task(self, task_service):
        """查询已创建任务应返回成功与任务名/状态字段"""
        created = task_service.create_sync_task()
        result = task_service.get_task_status_demo(created["task_id"])
        assert result["success"] is True
        assert result["task_id"] == created["task_id"]
        assert result["name"] == "sync_task"
        assert result["status"]


class TestScheduledTaskLifecycle:
    """定时任务的创建、启停与注销"""

    def test_create_scheduled_task_success(self, task_service):
        """创建定时任务应成功并带间隔说明"""
        result = task_service.create_scheduled_task(interval=60)
        assert result["success"] is True
        assert result["task_id"]
        assert "60" in result["message"]

    def test_scheduled_task_appears_in_query(self, task_service):
        """创建的定时任务应出现在 query_tasks 的定时任务列表中"""
        created = task_service.create_scheduled_task(interval=60)
        result = task_service.query_tasks()
        matches = [
            t for t in result["scheduled_tasks"]
            if t["task_id"] == created["task_id"]
        ]
        assert len(matches) == 1
        assert matches[0]["interval"] == 60
        assert matches[0]["enabled"] is True

    def test_disable_then_enable(self, task_service):
        """禁用后启用定时任务均应成功"""
        created = task_service.create_scheduled_task(interval=60)
        task_id = created["task_id"]
        assert task_service.set_scheduled_enabled(task_id, False)["success"] is True
        assert task_service.set_scheduled_enabled(task_id, True)["success"] is True

    def test_unregister_scheduled(self, task_service):
        """注销定时任务后 query 列表中应不再出现"""
        created = task_service.create_scheduled_task(interval=60)
        task_id = created["task_id"]
        assert task_service.unregister_scheduled(task_id)["success"] is True
        result = task_service.query_tasks()
        remaining = {t["task_id"] for t in result["scheduled_tasks"]}
        assert task_id not in remaining
