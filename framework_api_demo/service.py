"""
Framework API Demo 服务接口层

本模块的 FrameworkApiDemoService 是 information.py 中 service_api 声明的
实际实现实体：PluginManager 自动注册机制按「类名以 Service 结尾」规则
从本模块挑选该类，实例化后把 service_api 声明的三个方法
（demo_data_operation / demo_task_operation / get_framework_info）
注册为跨插件 API 并同步为 MCP 工具。

类本身只做参数校验与分发，实际业务逻辑委托给 function.services 包中
对应的演示服务（惰性创建并缓存）。
"""

from typing import Any, Dict, Optional

from core.data.data_provider import DataProvider

# 经包模块间接引用委托服务类：本模块命名空间中只保留 FrameworkApiDemoService
# 一个类，确保 PluginManager 按「类名以 Service 结尾」规则挑选时命中本类
from .function import services as demo_services

# 未注入 plugin_id 时的兜底标识（独立运行/冒烟测试场景）
DEFAULT_PLUGIN_ID = "framework-api-demo"

# demo_data_operation 支持的操作类型
DATA_OP_READ = "read"
DATA_OP_WRITE = "write"
DATA_OP_LIST = "list"

# demo_task_operation 支持的操作类型与任务类型
TASK_OP_CREATE = "create"
TASK_OP_QUERY = "query"
TASK_OP_CANCEL = "cancel"
TASK_TYPE_SYNC = "sync"
TASK_TYPE_ASYNC = "async"
TASK_TYPE_SCHEDULED = "scheduled"


class FrameworkApiDemoService:
    """service_api 声明的实体实现：三个演示方法的统一入口

    构造函数四个参数全部可选，兼容 PluginManager 的递减注入
    （(plugin_id, data_provider, llm_service, task_manager) 逐级裁减）。
    内部委托服务按需惰性创建；框架注入的 data_provider 优先使用，
    缺失时由委托服务基类回退 DataProvider() 单例。llm_service 与
    task_manager 仅为兼容注入签名而接收——框架实际注入的就是对应单例，
    委托服务经基类解析到的为同一实例，故无需显式透传。
    """

    def __init__(
        self,
        plugin_id: Optional[str] = None,
        data_provider: Optional[DataProvider] = None,
        llm_service: Any = None,
        task_manager: Any = None,
    ):
        self._plugin_id = plugin_id or DEFAULT_PLUGIN_ID
        self._data_provider = data_provider
        self._data_service: Optional['demo_services.DataDemoService'] = None
        self._task_service: Optional['demo_services.TaskDemoService'] = None
        self._info_service: Optional['demo_services.FrameworkInfoService'] = None

    # ------------------------------------------------------------------
    #  跨插件 API 实体方法（与 information.py 的 service_api 声明一致）
    # ------------------------------------------------------------------

    def demo_data_operation(
        self,
        operation: str,
        key: Optional[str] = None,
        value: Any = None,
    ) -> Dict[str, Any]:
        """演示 DataProvider 数据操作（read/write/list，作用于公共命名空间）"""
        service = self._get_data_service()
        if operation == DATA_OP_READ:
            return self._require_key(operation, key) or service.read_public_data(key)
        if operation == DATA_OP_WRITE:
            return self._require_key(operation, key) or service.write_public_data(key, value)
        if operation == DATA_OP_LIST:
            return service.get_all_data()
        return self._unknown_operation(operation, [DATA_OP_READ, DATA_OP_WRITE, DATA_OP_LIST])

    def demo_task_operation(
        self,
        operation: str,
        task_type: str = TASK_TYPE_SYNC,
        task_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """演示任务操作（create/query/cancel）"""
        service = self._get_task_service()
        if operation == TASK_OP_CREATE:
            return self._dispatch_task_create(service, task_type)
        if operation == TASK_OP_QUERY:
            return service.query_tasks()
        if operation == TASK_OP_CANCEL:
            return self._dispatch_task_cancel(service, task_id)
        return self._unknown_operation(operation, [TASK_OP_CREATE, TASK_OP_QUERY, TASK_OP_CANCEL])

    def get_framework_info(self) -> Dict[str, Any]:
        """获取框架信息（版本与可用 API 清单）"""
        return self._get_info_service().get_framework_info()

    # ------------------------------------------------------------------
    #  内部分发与参数校验
    # ------------------------------------------------------------------

    def _dispatch_task_create(self, service: 'demo_services.TaskDemoService', task_type: str) -> Dict[str, Any]:
        """按任务类型分发创建请求"""
        if task_type == TASK_TYPE_SYNC:
            return service.create_sync_task()
        if task_type == TASK_TYPE_ASYNC:
            return service.create_async_task()
        if task_type == TASK_TYPE_SCHEDULED:
            return service.create_scheduled_task()
        return self._unknown_operation(task_type, [TASK_TYPE_SYNC, TASK_TYPE_ASYNC, TASK_TYPE_SCHEDULED])

    @staticmethod
    def _dispatch_task_cancel(service: 'demo_services.TaskDemoService', task_id: Optional[str]) -> Dict[str, Any]:
        """分发取消请求：cancel 必须提供 task_id，缺失时返回参数不足错误"""
        if not task_id:
            return {"success": False, "error": "cancel 操作需要提供 task_id 参数"}
        return service.cancel_task_demo(task_id)

    @staticmethod
    def _require_key(operation: str, key: Optional[str]) -> Optional[Dict[str, Any]]:
        """校验 read/write 操作的 key 参数，缺失时返回错误字典，否则返回 None"""
        if not key:
            return {"success": False, "error": f"{operation} 操作需要提供 key 参数"}
        return None

    @staticmethod
    def _unknown_operation(operation: str, supported: list) -> Dict[str, Any]:
        """构造未知操作类型的错误返回"""
        return {
            "success": False,
            "error": f"未知操作类型: {operation}（支持: {'/'.join(supported)}）",
        }

    # ------------------------------------------------------------------
    #  委托服务惰性创建（属性缓存）
    # ------------------------------------------------------------------

    def _get_data_service(self) -> 'demo_services.DataDemoService':
        """惰性创建 DataDemoService（注入的 data_provider 优先，缺失由基类回退单例）"""
        if self._data_service is None:
            self._data_service = demo_services.DataDemoService(
                self._plugin_id, data_provider=self._data_provider,
            )
        return self._data_service

    def _get_task_service(self) -> 'demo_services.TaskDemoService':
        """惰性创建 TaskDemoService（注入的 data_provider 优先，缺失由基类回退单例）"""
        if self._task_service is None:
            self._task_service = demo_services.TaskDemoService(
                self._plugin_id, data_provider=self._data_provider,
            )
        return self._task_service

    def _get_info_service(self) -> 'demo_services.FrameworkInfoService':
        """惰性创建 FrameworkInfoService"""
        if self._info_service is None:
            self._info_service = demo_services.FrameworkInfoService(
                self._plugin_id, data_provider=self._data_provider,
            )
        return self._info_service


__all__ = ["FrameworkApiDemoService"]
