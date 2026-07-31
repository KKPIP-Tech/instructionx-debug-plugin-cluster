"""
Blueprint OpenCV 服务接口层

本模块的 BlueprintOpenCVService 是 information.py 中 service_api 声明的
实际实现实体：PluginManager 自动注册机制按「类名以 Service 结尾」规则
从本模块挑选该类，实例化后把六个 service_api 方法（run_pipeline /
stop_pipeline / save_graph / load_graph / list_node_types /
get_last_result_info）注册为跨插件 API 并同步为 MCP 工具。

本类为 QObject 门面：持有 PipelineController 与当前图快照，定义 Qt 信号
用于工作线程 → UI 线程的结果封送（emit 由 Qt 自动排队到接收方所在线程，
本类不创建任何 QPixmap）。执行引擎、节点目录、图像编解码等业务细节全部
委托 function/ 层，本模块不出现 cv2 / numpy。
"""

import json
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Signal

from core.data.data_provider import DataProvider, DataProviderError
from utils.logging_tools import LoggerManager

# 经包模块间接引用 function 层：本模块命名空间中只保留 BlueprintOpenCVService
# 一个类，确保 PluginManager 按「类名以 Service 结尾」规则挑选时命中本类
from .function import executor as executor_module
from .function import node_catalog, pipeline_controller

# 日志模块标识
LOG_TAG = "BlueprintOpenCV"

# 未注入 plugin_id 时的兜底标识（独立运行/冒烟测试场景）
DEFAULT_PLUGIN_ID = "blueprint-opencv"

# DataProvider 图存档文件名约定（取值与 config/default.json 的 graph.*
# 配置一致：default_name / storage_namespace；配置加载由 ui 层负责，
# service 层以此命名常量作为缺省值，保证跨插件调用路径不依赖配置文件）
DEFAULT_GRAPH_NAME = "default"
GRAPH_STORAGE_NAMESPACE = "graphs"
GRAPH_FILE_SUFFIX = ".json"

# DataProvider.save_asset 返回的资源相对路径前缀（见 data_provider.py 实现）
ASSET_PATH_PREFIX = "assets/plugins"

# 预置示例图资产路径（相对插件目录，见 SPEC §8 assets.preset_graph）
PRESET_GRAPH_RELATIVE_PATH = "assets/preset_graph.json"

# 空图结构（与 BlueprintCanvas.to_dict 格式一致；预置示例图缺失时的最终回退）
EMPTY_GRAPH: Dict[str, Any] = {
    "graph": {"nodes": [], "edges": []},
    "view": {"zoom": 1.0, "offset": [0.0, 0.0]},
}


class BlueprintOpenCVService(QObject):
    """service_api 声明的实体实现：Blueprint OpenCV 插件的统一服务门面

    构造函数前四个参数全部可选，兼容 PluginManager 的递减注入
    （(plugin_id, data_provider, llm_service, task_manager) 逐级裁减）。
    llm_service / task_manager 仅为兼容注入签名而接收——管线执行由
    PipelineController 内部经 BackgroundTaskManager 提交工作线程。

    线程模型：run_pipeline / stop_pipeline 可被任意线程（UI / MCP）调用；
    执行回调在工作线程触发，此处直接 emit Qt 信号，由 Qt 自动排队到
    接收方（UI 控件）所在线程执行槽函数。
    """

    # ---- 信号（非 service_api，供 UI/内部订阅，跨线程自动排队）----
    preview_ready = Signal(bytes, dict)                  # preview 结果 PNG 字节 + info
    node_status_changed = Signal(str, str, float, str)   # node_id, status, elapsed_ms, message
    run_finished = Signal(dict)                          # 运行汇总 summary

    _logger = LoggerManager()

    def __init__(
        self,
        plugin_id: Optional[str] = None,
        data_provider: Optional[DataProvider] = None,
        llm_service: Any = None,
        task_manager: Any = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._plugin_id = plugin_id or DEFAULT_PLUGIN_ID
        self._data_provider = data_provider or DataProvider()
        self._controller = pipeline_controller.PipelineController()
        # 当前图快照（canvas.to_dict 格式）：UI 经 update_graph 同步，
        # 保存/运行以此为数据源
        self._graph_snapshot: Dict[str, Any] = dict(EMPTY_GRAPH)

    # ------------------------------------------------------------------
    #  跨插件 API 实体方法（与 information.py 的 service_api 声明一致）
    # ------------------------------------------------------------------

    def run_pipeline(self) -> Dict[str, Any]:
        """运行当前图管线（异步，工作线程执行）

        Returns:
            {"success": True, "data": {"started": True}}；
            校验失败（无 start 节点 / exec 链成环 / 已在运行）时
            {"success": False, "error": 中文原因}
        """
        started = self._controller.start_run(self._build_callbacks())
        if not started:
            return {"success": False, "error": (
                "无法启动运行：请确认图中存在 start 节点、exec 链无环、"
                "节点数未超上限且当前无运行中的管线"
            )}
        return {"success": True, "data": {"started": True}}

    def stop_pipeline(self) -> Dict[str, Any]:
        """请求停止当前运行（协作式，当前节点完成后中断）"""
        self._controller.request_stop()
        return {"success": True, "data": {"stopping": True}}

    def save_graph(self, name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
        """将当前图快照序列化并经 DataProvider 持久化到插件私有资产区"""
        graph_name = name or DEFAULT_GRAPH_NAME
        try:
            content = json.dumps(self._graph_snapshot, ensure_ascii=False).encode("utf-8")
            self._data_provider.save_asset(
                self._plugin_id, self._asset_filename(graph_name), content,
            )
        except (DataProviderError, OSError, TypeError, ValueError) as e:
            self._log_error("保存图", e)
            return {"success": False, "error": f"保存图失败: {e}"}
        return {"success": True, "data": {
            "name": graph_name, "node_count": self._node_count(self._graph_snapshot),
        }}

    def load_graph(self, name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
        """从 DataProvider 恢复指定图；不存在/损坏时回退预置示例图

        加载结果写入图快照并经 PipelineController 同步；UI 随后读取
        current_graph 并 canvas.from_dict 恢复画布。
        """
        graph_name = name or DEFAULT_GRAPH_NAME
        graph_dict = self._read_saved_graph(graph_name)
        fallback = graph_dict is None
        if fallback:
            graph_dict = self._read_preset_graph()
        self.update_graph(graph_dict)
        return {"success": True, "data": {"name": graph_name, "fallback": fallback}}

    def list_node_types(self) -> Dict[str, Any]:
        """列出全部已注册节点类型（剔除不可序列化的 op 可调用对象）"""
        nodes = [self._node_definition_to_dict(d) for d in node_catalog.NODE_DEFINITIONS]
        return {"success": True, "data": {"nodes": nodes}}

    def get_last_result_info(self) -> Dict[str, Any]:
        """最近一次运行的汇总信息与 preview 结果元数据（不含图像本体）"""
        info = dict(self._controller.last_result_info or {})
        return {"success": True, "data": info}

    # ------------------------------------------------------------------
    #  供 UI 层调用的内部方法（不在 service_api 声明内，不注册跨插件 API）
    # ------------------------------------------------------------------

    def update_graph(self, graph_dict: Dict[str, Any]) -> None:
        """同步最新图快照：UI 在图变更（含 load_graph 恢复）后调用

        Args:
            graph_dict: canvas.to_dict 格式的图序列化字典
        """
        self._graph_snapshot = graph_dict
        self._controller.update_graph(graph_dict)

    @property
    def current_graph(self) -> Dict[str, Any]:
        """当前图快照（load_graph 后由 UI 读取并 canvas.from_dict 恢复画布）"""
        return self._graph_snapshot

    def shutdown(self) -> None:
        """卸载清理：请求停止运行中的管线（信号断开由 entrance 逐项容错处理）"""
        self._controller.request_stop()

    # ------------------------------------------------------------------
    #  执行回调：工作线程触发，直接 emit Qt 信号自动排队封送
    # ------------------------------------------------------------------

    def _build_callbacks(self) -> "executor_module.ExecutorCallbacks":
        """构造执行回调集合，将引擎回调桥接到本类的 Qt 信号"""
        return executor_module.ExecutorCallbacks(
            on_node_status=self._on_node_status,
            on_preview=self._on_preview,
            on_run_finished=self._on_run_finished,
        )

    def _on_node_status(self, node_id: str, status: str, elapsed_ms: float, message: str) -> None:
        """节点状态回调（工作线程）：原样上抛信号"""
        self.node_status_changed.emit(node_id, status, elapsed_ms, message)

    def _on_preview(self, node_id: str, png_bytes: bytes, info: Dict[str, Any]) -> None:
        """preview 节点结果回调（工作线程）：PNG 字节 + info 上抛信号"""
        self.preview_ready.emit(png_bytes, info)

    def _on_run_finished(self, summary: Dict[str, Any]) -> None:
        """运行结束回调（工作线程）：汇总 summary 上抛信号"""
        self.run_finished.emit(summary)

    # ------------------------------------------------------------------
    #  图存档读写（DataProvider 资产区 + 预置示例图回退）
    # ------------------------------------------------------------------

    def _read_saved_graph(self, name: str) -> Optional[Dict[str, Any]]:
        """读取 DataProvider 存档图；不存在或损坏时记 WARNING 日志并返回 None"""
        relative = f"{ASSET_PATH_PREFIX}/{self._plugin_id}/{self._asset_filename(name)}"
        try:
            path = self._data_provider.get_asset_path(relative)
            with open(path, "rb") as f:
                return json.loads(f.read().decode("utf-8"))
        except (DataProviderError, OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.warning(LOG_TAG, f"读取图存档失败（回退示例图）: {name}: {e}")
            return None

    def _read_preset_graph(self) -> Dict[str, Any]:
        """读取插件资产中的预置示例图；缺失/损坏时记日志并回退空图"""
        preset_path = Path(__file__).parent / PRESET_GRAPH_RELATIVE_PATH
        try:
            with open(preset_path, "rb") as f:
                return json.loads(f.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.warning(LOG_TAG, f"预置示例图不可用（回退空图）: {e}")
            return dict(EMPTY_GRAPH)

    @staticmethod
    def _asset_filename(name: str) -> str:
        """组装图存档文件名（命名空间子目录 + 图名 + 扩展名）"""
        return f"{GRAPH_STORAGE_NAMESPACE}/{name}{GRAPH_FILE_SUFFIX}"

    @staticmethod
    def _node_count(graph_dict: Dict[str, Any]) -> int:
        """统计图内节点数（兼容 canvas.to_dict 的 {"graph": ...} 外层包装）"""
        graph_payload = graph_dict.get("graph", graph_dict)
        return len(graph_payload.get("nodes", []))

    @staticmethod
    def _node_definition_to_dict(definition: Any) -> Dict[str, Any]:
        """把 NodeDefinition 转为可 JSON 序列化字典（剔除 op 可调用对象）"""
        return {
            "type_name": definition.type_name,
            "title": definition.title,
            "category": definition.category,
            "inputs": definition.inputs,
            "outputs": definition.outputs,
            "param_schema": definition.param_schema,
            "description": definition.description,
        }

    def _log_error(self, operation: str, error: Exception) -> None:
        """统一记录操作失败日志（含堆栈，LoggerManager 不支持 exc_info）"""
        self._logger.error(
            LOG_TAG, f"{operation}失败: {error}\n{traceback.format_exc()}",
        )


__all__ = ["BlueprintOpenCVService"]
