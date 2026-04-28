"""
local_server 插件服务层（接口层）

仅对外暴露 API，不含任何业务逻辑。
所有业务逻辑委托给 function/services/ 目录下的模块。
"""

from core.data.data_provider import DataProvider, DataProviderError, DataNamespace
from .function.services.core_service import HttpService


class Service:
    """本地 HTTP 服务器服务（接口层）"""

    def __init__(self, plugin_id: str = None, data_provider=None):
        self.plugin_id = plugin_id
        self.data_provider = data_provider or DataProvider()
        self._http_service = HttpService()
        self._server_task_id = self.load_data("server_task_id")
        self._request_count = self.load_data("request_count", 0)
        self._is_running = self.load_data("is_running", False)

    def get_status(self) -> dict:
        return {
            "is_running": self._is_running,
            "request_count": self._request_count,
            "task_id": self._server_task_id
        }

    def increment_request_count(self):
        self._request_count += 1
        if not self.plugin_id:
            return
        self.data_provider.set_plugin_data(
            self.plugin_id,
            "request_count",
            self._request_count,
            DataNamespace.PRIVATE
        )

    def set_running(self, is_running: bool, task_id: str = None):
        self._is_running = is_running
        self._server_task_id = task_id
        if not self.plugin_id:
            return
        self.data_provider.set_plugin_data(
            self.plugin_id,
            "is_running",
            is_running,
            DataNamespace.PRIVATE
        )

    def save_data(self, key: str, value):
        self.data_provider.set_plugin_data(
            self.plugin_id,
            key,
            value,
            DataNamespace.PRIVATE
        )

    def load_data(self, key: str, default=None):
        try:
            return self.data_provider.get_plugin_data(
                self.plugin_id,
                key,
                DataNamespace.PRIVATE,
                default
            )
        except DataProviderError:
            return default

    def get_default_port(self) -> int:
        return self._http_service.get_default_port()

    def get_port_range(self) -> tuple:
        return self._http_service.get_port_range()

    def start_http_server(self, port: int, request_callback):
        self._http_service.start_server(port, request_callback)

    def stop_http_server(self):
        self._http_service.stop_server()

    def is_http_running(self) -> bool:
        return self._http_service.is_running()
