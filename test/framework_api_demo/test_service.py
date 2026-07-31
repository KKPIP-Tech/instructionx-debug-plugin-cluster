# -*- coding: utf-8 -*-
"""service.py 的 FrameworkApiDemoService 测试（service_api 三方法）。

覆盖：
- demo_data_operation：read/write/list 全操作、缺 key 与未知 operation 的错误路径；
- demo_task_operation：create（sync/未知类型）、query、cancel（缺 task_id /
  不存在 task_id）、未知 operation；
- get_framework_info：框架信息结构；
- 构造参数兜底：plugin_id 缺省时回退 DEFAULT_PLUGIN_ID。

数据操作经注入的隔离 DataProvider 落盘到 tmp_path；
任务操作使用 BackgroundTaskManager 单例但仅以隔离 plugin_id 创建，
fixture 负责清理。
"""

from core.version import get_instructionx_version_string

from plugin.framework_api_demo.service import (
    DEFAULT_PLUGIN_ID,
    FrameworkApiDemoService,
)


class TestConstructorFallback:
    """构造参数兜底行为"""

    def test_default_plugin_id_when_omitted(self):
        """未注入 plugin_id 时应回退到 DEFAULT_PLUGIN_ID"""
        service = FrameworkApiDemoService()
        assert service._plugin_id == DEFAULT_PLUGIN_ID

    def test_explicit_plugin_id(self, plugin_id, registered_provider):
        """显式注入的 plugin_id 应被保留"""
        service = FrameworkApiDemoService(
            plugin_id=plugin_id, data_provider=registered_provider,
        )
        assert service._plugin_id == plugin_id


class TestDemoDataOperation:
    """demo_data_operation 的 read/write/list 与错误路径"""

    def test_write_then_read_roundtrip(self, api_service_instance):
        """write 写入后 read 应读回相同值"""
        write_result = api_service_instance.demo_data_operation(
            "write", key="greeting", value="hello",
        )
        assert write_result["success"] is True

        read_result = api_service_instance.demo_data_operation(
            "read", key="greeting",
        )
        assert read_result["success"] is True
        assert read_result["value"] == "hello"

    def test_read_missing_key_returns_default_none(self, api_service_instance):
        """read 未写入过的键应成功且返回默认 None"""
        result = api_service_instance.demo_data_operation("read", key="not-exist")
        assert result["success"] is True
        assert result["value"] is None

    def test_list_returns_private_and_public(self, api_service_instance):
        """list 应返回包含 private/public 两个字典的结果，公共区含已写入键"""
        api_service_instance.demo_data_operation("write", key="k1", value=123)
        result = api_service_instance.demo_data_operation("list")
        assert result["success"] is True
        assert isinstance(result["private"], dict)
        assert isinstance(result["public"], dict)
        assert result["public"]["k1"] == 123

    def test_read_without_key_returns_error(self, api_service_instance):
        """read 缺 key 应返回参数错误而非抛异常"""
        result = api_service_instance.demo_data_operation("read")
        assert result["success"] is False
        assert "key" in result["error"]

    def test_write_without_key_returns_error(self, api_service_instance):
        """write 缺 key 应返回参数错误"""
        result = api_service_instance.demo_data_operation("write", value="v")
        assert result["success"] is False
        assert "key" in result["error"]

    def test_unknown_operation_returns_error(self, api_service_instance):
        """未知 operation 应返回错误并列出支持的操作"""
        result = api_service_instance.demo_data_operation("delete", key="k")
        assert result["success"] is False
        assert "未知操作类型" in result["error"]
        assert "read" in result["error"]


class TestDemoTaskOperation:
    """demo_task_operation 的 create/query/cancel 与错误路径"""

    def test_create_sync_task_success(self, api_service_instance):
        """create + sync 应成功并返回 task_id"""
        result = api_service_instance.demo_task_operation("create", task_type="sync")
        assert result["success"] is True
        assert result["task_id"]

    def test_create_unknown_task_type_returns_error(self, api_service_instance):
        """create 使用未知 task_type 应返回错误且不创建任务"""
        result = api_service_instance.demo_task_operation(
            "create", task_type="not-a-type",
        )
        assert result["success"] is False
        assert "未知操作类型" in result["error"]

    def test_query_returns_three_task_lists(self, api_service_instance):
        """query 应返回普通/定时/长期三类任务列表"""
        result = api_service_instance.demo_task_operation("query")
        assert result["success"] is True
        assert isinstance(result["tasks"], list)
        assert isinstance(result["scheduled_tasks"], list)
        assert isinstance(result["long_running_tasks"], list)

    def test_query_includes_created_task(self, api_service_instance):
        """create 后 query 的普通任务列表应包含新任务 id"""
        created = api_service_instance.demo_task_operation("create", task_type="sync")
        result = api_service_instance.demo_task_operation("query")
        task_ids = {t["task_id"] for t in result["tasks"]}
        assert created["task_id"] in task_ids

    def test_cancel_without_task_id_returns_error(self, api_service_instance):
        """cancel 缺 task_id 应返回参数错误"""
        result = api_service_instance.demo_task_operation("cancel")
        assert result["success"] is False
        assert "task_id" in result["error"]

    def test_cancel_nonexistent_task_returns_error(self, api_service_instance):
        """cancel 不存在的 task_id 应返回「不在运行列表中」错误"""
        result = api_service_instance.demo_task_operation(
            "cancel", task_id="pytest-nonexistent-task",
        )
        assert result["success"] is False
        assert "不在运行列表中" in result["error"]

    def test_unknown_operation_returns_error(self, api_service_instance):
        """未知 operation 应返回错误并列出支持的操作"""
        result = api_service_instance.demo_task_operation("restart")
        assert result["success"] is False
        assert "未知操作类型" in result["error"]
        assert "create" in result["error"]


class TestGetFrameworkInfo:
    """get_framework_info 结构校验"""

    def test_framework_info_structure(self, api_service_instance):
        """应返回框架名、当前版本字符串与核心 API 清单"""
        info = api_service_instance.get_framework_info()
        assert info["framework"] == "InstructionX"
        assert info["version"] == get_instructionx_version_string()
        assert isinstance(info["apis"], list)
        assert "DataProvider" in info["apis"]
        assert "BackgroundTaskManager" in info["apis"]
