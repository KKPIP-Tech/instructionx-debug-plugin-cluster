"""
Framework API Demo MCP 演示服务

演示 PluginServices 注入的 mcp_manager / mcp_client 接口：
内置 MCP Server 生命周期与状态、service_api 自动桥接工具清单、
远程 MCP Server 连接/断开/工具列表（MCPClientManager 同步契约）。

mcp_manager / mcp_client 为 Optional 注入（框架未启用 MCP 时为 None），
所有公开方法先判空，未注入时返回统一错误字典。
"""

from typing import Any, Callable, Dict, List, Optional

from core.mcp.config import MCPRemoteServerConfig
from core.plugin.manager import PluginManager
from core.plugin.tool_name import sanitize_tool_name
from utils.logging_tools import get_name

from .base import Service, _load_config

# MCP 服务未注入时的统一错误信息
MCP_UNAVAILABLE_ERROR = "MCP 服务未注入（框架未启用 MCP）"

# 演示启动内置 Server 固定使用 streamable-http：
# stdio 传输的 run_stdio() 会阻塞调用线程直到 Server 退出
# （见 core/mcp/server.py MCPHostServer.run_stdio），
# 而 run_http() 在后台线程起 uvicorn、快速返回，适合 UI 触发的演示。
DEMO_SERVER_TRANSPORT = "streamable-http"


class MCPDemoService(Service):
    """演示 MCPManager / MCPClientManager 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        # mcp_manager / mcp_client 均为 Optional 注入，框架未启用 MCP 时为 None
        self.mcp_manager = getattr(services, "mcp_manager", None) if services else None
        self.mcp_client = getattr(services, "mcp_client", None) if services else None
        self.plugin_manager = PluginManager()
        mcp_cfg = _load_config().get("mcp", {})
        self.remote_demo_config: Dict[str, Any] = mcp_cfg.get("remote_demo", {})

    # ------------------------------------------------------------------
    #  公共辅助
    # ------------------------------------------------------------------

    def _unavailable(self) -> Dict[str, Any]:
        """MCP 服务未注入时的统一错误返回（门面缺失时回退模块级中文常量）"""
        return {"success": False, "error": self._tr(
            "svc_mcp", "err.unavailable", default=MCP_UNAVAILABLE_ERROR)}

    def get_remote_demo_config(self) -> Dict[str, Any]:
        """返回远程演示服务器的示例配置（config/default.json 的 mcp.remote_demo 段）"""
        return dict(self.remote_demo_config)

    def _make_mcp_callback(self, operation: str) -> Callable:
        """构造后台 MCP 操作的完成回调（工作线程执行）：经 notifier 上抛 + 记日志"""

        def on_completed(task_id: str, status, result, error) -> None:
            try:
                message = self._tr(
                    "svc_mcp", "msg.callback",
                    default="MCP {operation}: [{status}] 结果={result} 错误={error}",
                    operation=operation, status=status, result=result, error=error)
                self._notify_event(message)
                self.logger.info(get_name(), f"MCP 后台操作回调 {operation}({task_id}): {message}")
            except Exception as e:
                self.logger.error(get_name(), f"MCP 回调处理失败 {operation}: {e}")

        return on_completed

    # ------------------------------------------------------------------
    #  内置 MCP Server
    # ------------------------------------------------------------------

    def get_server_status(self) -> Dict[str, Any]:
        """返回内置 MCP Server 的运行状态、地址与配置摘要"""
        if self.mcp_manager is None:
            return self._unavailable()
        try:
            cfg = self.mcp_manager.get_server_config()
            return {
                "success": True,
                "running": self.mcp_manager.is_server_running(),
                "url": self.mcp_manager.get_server_url(),
                "config": {
                    "host": cfg.host, "port": cfg.port,
                    "transport": cfg.transport, "enabled": cfg.enabled,
                    "auth_enabled": cfg.auth_token is not None,
                },
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_mcp_server(self) -> Dict[str, Any]:
        """启动内置 MCP Server（固定 streamable-http，避免 stdio 阻塞 UI 线程）"""
        if self.mcp_manager is None:
            return self._unavailable()
        try:
            self.mcp_manager.start_server(transport=DEMO_SERVER_TRANSPORT)
            running = self.mcp_manager.is_server_running()
            if running:
                return {"success": True, "url": self.mcp_manager.get_server_url()}
            return {"success": False, "error": self._tr(
                "svc_mcp", "err.server_not_running",
                default="Server 未进入运行状态（可能在配置中被禁用）")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stop_mcp_server(self) -> Dict[str, Any]:
        """停止内置 MCP Server"""
        if self.mcp_manager is None:
            return self._unavailable()
        try:
            self.mcp_manager.stop_server()
            return {"success": True, "running": self.mcp_manager.is_server_running()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  service_api 自动桥接工具
    # ------------------------------------------------------------------

    def list_bridged_tools(self) -> Dict[str, Any]:
        """列出本插件 service_api 自动桥接为 MCP 工具的工具名清单

        桥接机制（core/mcp/bridge.py MCPBridge）：插件在 information.py 声明
        service_api 后，PluginManager 自动注册跨插件 API 并同步到 MCP Server，
        工具名为 sanitize_tool_name(f"{plugin_id}__{method_name}")
        （非法字符替换为 '_'，截断到 64 字符，见 core/plugin/tool_name.py）。
        """
        try:
            apis = self.plugin_manager.get_all_apis()
            info = apis.get(self.plugin_id)
            if info is None:
                return {"success": False, "error": self._tr(
                    "svc_mcp", "err.not_bridged",
                    default="本插件 API 尚未注册到 PluginManager")}
            methods: List[str] = list(info.get("methods", []))
            tools = [sanitize_tool_name(f"{self.plugin_id}__{m}") for m in methods]
            return {"success": True, "count": len(tools), "tools": tools}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  远程 MCP Server（MCPClientManager 同步契约）
    # ------------------------------------------------------------------

    def connect_remote_demo(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """演示连接远程 MCP Server（后台任务执行，避免阻塞 UI 线程）

        mcp_client.connect 为同步方法，内部经事件循环等待连接完成，
        失败时最长阻塞至超时（默认 60 秒），故经 register_async_task
        提交到任务线程池执行，结果经事件通知器上抛 UI。

        参数:
            config: 符合 MCPRemoteServerConfig 字段的 dict
                    （server_id/name 必填，stdio 填 command/args，http 填 url）
        """
        if self.mcp_client is None:
            return self._unavailable()
        try:
            remote_cfg = MCPRemoteServerConfig.from_dict(config)
        except (KeyError, TypeError) as e:
            return self._connect_config_error(e)
        op = self._tr("svc_mcp", "op.connect", default="连接远程 Server")
        return self._submit_mcp_task(op, self._do_connect, remote_cfg)

    def _connect_config_error(self, error: Exception) -> Dict[str, Any]:
        """远程配置格式错误的统一返回"""
        return {"success": False, "error": self._tr(
            "svc_mcp", "err.config_format",
            default="配置格式错误（需含 server_id/name）: {error}", error=error)}

    def _do_connect(self, remote_cfg: MCPRemoteServerConfig) -> str:
        """后台线程执行：同步连接远程 Server 并返回摘要（异常抛给任务系统）"""
        server_id = self.mcp_client.connect(remote_cfg)
        tools = self.mcp_client.list_tools(server_id)
        return self._tr("svc_mcp", "msg.connected",
                        default="已连接 {id}，注册工具 {count} 个",
                        id=server_id, count=len(tools))

    def disconnect_remote_demo(self, server_id: str) -> Dict[str, Any]:
        """演示断开远程 MCP Server（后台任务执行，理由同 connect）"""
        if self.mcp_client is None:
            return self._unavailable()
        if not server_id:
            return {"success": False, "error": self._tr(
                "svc_mcp", "err.server_id_required", default="需要指定 server_id")}
        return self._submit_mcp_task(
            self._tr("svc_mcp", "op.disconnect", default="断开远程 Server"),
            self._do_disconnect, server_id
        )

    def _do_disconnect(self, server_id: str) -> str:
        """后台线程执行：同步断开远程 Server"""
        self.mcp_client.disconnect(server_id)
        return self._tr("svc_mcp", "msg.disconnected",
                        default="已断开 {id}", id=server_id)

    def _submit_mcp_task(self, operation: str, func: Callable, arg: Any) -> Dict[str, Any]:
        """把阻塞型 MCP 操作提交为异步后台任务（线程池执行，避免阻塞 UI 线程）"""
        try:
            task_id = self.tm.register_async_task(
                plugin_id=self.plugin_id, name=f"mcp_{operation}",
                func=func, args=(arg,),
                callback=self._make_mcp_callback(operation),
            )
            if task_id is None:
                return {"success": False, "error": self._tr(
                    "svc_mcp", "err.manager_closed",
                    default="任务管理器已关闭，无法发起后台任务")}
            return {"success": True, "task_id": task_id,
                    "message": self._tr(
                        "svc_mcp", "msg.submitted",
                        default="{operation}已提交后台执行，结果见执行日志",
                        operation=operation)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_remote_servers(self) -> Dict[str, Any]:
        """列出当前已连接的远程 MCP Server（同步方法，快速返回）"""
        if self.mcp_client is None:
            return self._unavailable()
        try:
            servers = self.mcp_client.list_connected_servers()
            return {"success": True, "count": len(servers), "servers": servers}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_remote_tools_demo(self, server_id: str) -> Dict[str, Any]:
        """列出指定远程 Server 的工具（净化后的命名空间名 mcp__{server_id}__{tool}）"""
        if self.mcp_client is None:
            return self._unavailable()
        if not server_id:
            return {"success": False, "error": self._tr(
                "svc_mcp", "err.server_id_required", default="需要指定 server_id")}
        try:
            tools = self.mcp_client.list_tools(server_id)
            return {"success": True, "count": len(tools), "tools": tools}
        except Exception as e:
            return {"success": False, "error": str(e)}
