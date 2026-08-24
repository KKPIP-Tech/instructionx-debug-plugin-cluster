"""
Blueprint OpenCV 服务接口层

本模块的 BlueprintOpenCVService 是 information.py 中 service_api 声明的
实际实现实体：PluginManager 自动注册机制按「类名以 Service 结尾」规则
从本模块挑选该类，实例化后把九个 service_api 方法（run_pipeline /
stop_pipeline / save_graph / load_graph / list_graphs / delete_graph /
rename_graph / list_node_types / get_last_result_info）注册为跨插件 API
并同步为 MCP 工具。

本类为 QObject 门面：PipelineController 与当前图快照由 function 层
runtime_registry 按 plugin_id 提供的共享 PipelineRuntime 承载——框架
自动注册跨插件 API 时会自行实例化第二个本类对象，共享运行实例保证
UI / 跨插件 / MCP 路径操作同一份运行态（见 runtime_registry 模块
docstring）。本类定义的 Qt 信号用于工作线程 → UI 线程的结果封送
（emit 由 Qt 自动排队到接收方所在线程，本类不创建任何 QPixmap）。
执行引擎、节点目录、图像编解码等业务细节全部委托 function/ 层，
本模块不出现 cv2 / numpy。
"""

import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, Signal

from core.data.data_provider import DataProvider, DataProviderError
from core.task.background_task import BackgroundTaskManager
from utils.logging_tools import LoggerManager

# 经包模块间接引用 function 层：本模块命名空间中只保留 BlueprintOpenCVService
# 一个类，确保 PluginManager 按「类名以 Service 结尾」规则挑选时命中本类
from .function import executor as executor_module
from .function import graph_migration, node_catalog
from .function import runtime_registry
from .function.constants import NodeExecutionError

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

#: 图名非法字符（Windows 文件名禁用字符，SPEC-graph-list §1.4）
INVALID_NAME_CHARS = '<>:"/\\|?*'

# 预置示例图资产路径（相对插件目录，见 SPEC §8 assets.preset_graph）
PRESET_GRAPH_RELATIVE_PATH = "assets/preset_graph.json"

#: 插件根目录（预置图内相对路径的解析基准）
_PLUGIN_ROOT = Path(__file__).resolve().parent
#: 节点属性中的文件路径参数键（预置图相对路径解析对象）
_FILE_PATH_PROPERTY = "file_path"

# 管线执行后台任务名（register_async_task 的 name 参数）
RUN_TASK_NAME = "blueprint_opencv.run_pipeline"


class BlueprintOpenCVService(QObject):
    """service_api 声明的实体实现：Blueprint OpenCV 插件的统一服务门面

    构造函数前四个参数全部可选，兼容 PluginManager 的递减注入
    （(plugin_id, data_provider, llm_service, task_manager) 逐级裁减）。
    llm_service 仅为兼容注入签名而接收；task_manager 用于把管线执行
    提交到框架线程池（缺省回退 BackgroundTaskManager 单例）。

    运行态（PipelineController + 图快照）取自 runtime_registry 按
    plugin_id 共享的 PipelineRuntime，因此 UI 实例与框架自动注册实例
    操作同一份图与运行状态，跨实例并发提交由控制器的运行状态机拦截。

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
        self._task_manager = task_manager
        # 共享运行实例（按 plugin_id 进程内唯一）：框架自动注册跨插件 API
        # 时自行实例化的第二个本类对象解析到同一 runtime，避免 MCP
        # run_pipeline 跑空图、save_graph 以空图覆盖用户存档
        self._runtime = runtime_registry.get_pipeline_runtime(self._plugin_id)

    # ------------------------------------------------------------------
    #  跨插件 API 实体方法（与 information.py 的 service_api 声明一致）
    # ------------------------------------------------------------------

    def run_pipeline(self) -> Dict[str, Any]:
        """运行当前图管线（异步，提交 BackgroundTaskManager 工作线程执行）

        运行前校验（无 start / exec 链成环 / 节点数超限）同步完成，失败
        立即返回中文错误；校验通过后 cv2 处理在工作线程执行，结果经 Qt
        信号封送回 UI（SPEC §1.3 / §7）。
        """
        try:
            started = self._runtime.controller.submit_run(
                self._build_callbacks(), self._submit_background)
        except NodeExecutionError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            self._log_error("提交管线后台任务", e)
            return {"success": False, "error": f"提交后台任务失败: {e}"}
        if not started:
            return {"success": False,
                    "error": "已有运行中的管线，请先停止或等待完成"}
        return {"success": True, "data": {"started": True}}

    def _submit_background(self, work: Callable[[], None]) -> None:
        """把管线执行提交到框架线程池（SPEC §1.3，service 层注入调度）。

        注意：BackgroundTaskManager.register_sync_task 是在调用方线程
        内联执行的（见 core/task/background_task.py），只有
        register_async_task 才真正进入框架线程池，故此处用后者；
        结果封送不依赖任务 callback，由本类 Qt 信号完成。
        """
        task_manager = self._task_manager or BackgroundTaskManager()
        task_id = task_manager.register_async_task(
            self._plugin_id, RUN_TASK_NAME, work)
        if task_id is None:
            raise RuntimeError("后台任务管理器已关闭，无法提交管线执行")

    def stop_pipeline(self) -> Dict[str, Any]:
        """请求停止当前运行（协作式，当前节点完成后中断）"""
        self._runtime.controller.request_stop()
        return {"success": True, "data": {"stopping": True}}

    def save_graph(self, name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
        """将当前图快照序列化并经 DataProvider 持久化到插件私有资产区"""
        graph_name = name or DEFAULT_GRAPH_NAME
        snapshot = self._runtime.current_graph
        try:
            self._ensure_storage_dir()
            content = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
            self._data_provider.save_asset(
                self._plugin_id, self._asset_filename(graph_name), content,
            )
        except (DataProviderError, OSError, TypeError, ValueError) as e:
            self._log_error("保存图", e)
            return {"success": False, "error": f"保存图失败: {e}"}
        return {"success": True, "data": {
            "name": graph_name, "node_count": self._node_count(snapshot),
        }}

    def _ensure_storage_dir(self) -> None:
        """确保图存档子目录存在（save_asset 只建插件根目录，不建嵌套子目录）。"""
        self._storage_dir().mkdir(parents=True, exist_ok=True)

    def _storage_dir(self) -> Path:
        """图存档目录路径（插件资产区 graphs/ 子目录，SPEC-graph-list §3.1）。"""
        return (Path(self._data_provider.assets_dir)
                / self._plugin_id / GRAPH_STORAGE_NAMESPACE)

    def list_graphs(self) -> Dict[str, Any]:
        """枚举全部已保存图存档（名称 + 节点数 + 大小 + 修改时间）

        目录不存在（尚未保存过）返回空列表；单个存档损坏仅使其
        node_count 为 None，不拖垮整体枚举。
        """
        try:
            storage_dir = self._storage_dir()
            if not storage_dir.is_dir():
                return {"success": True, "data": {"graphs": []}}
            graphs = [self._graph_file_meta(p) for p in sorted(
                storage_dir.glob(f"*{GRAPH_FILE_SUFFIX}"))]
        except OSError as e:
            self._log_error("列出图存档", e)
            return {"success": False, "error": f"列出图存档失败: {e}"}
        return {"success": True, "data": {"graphs": graphs}}

    def delete_graph(self, name: str) -> Dict[str, Any]:
        """删除指定图存档；名非法 / 存档不存在返回中文错误"""
        error = self._validate_graph_name(name)
        if error:
            return {"success": False, "error": error}
        path = self._storage_dir() / f"{name}{GRAPH_FILE_SUFFIX}"
        try:
            path.unlink()
        except FileNotFoundError:
            return {"success": False, "error": f"存档不存在: {name}"}
        except OSError as e:
            self._log_error("删除图存档", e)
            return {"success": False, "error": f"删除图存档失败: {e}"}
        return {"success": True, "data": {"name": name}}

    def rename_graph(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """重命名图存档；名非法 / 旧档不存在 / 新名冲突返回中文错误"""
        for candidate in (old_name, new_name):
            error = self._validate_graph_name(candidate)
            if error:
                return {"success": False, "error": error}
        old_path = self._storage_dir() / f"{old_name}{GRAPH_FILE_SUFFIX}"
        new_path = self._storage_dir() / f"{new_name}{GRAPH_FILE_SUFFIX}"
        if not old_path.is_file():
            return {"success": False, "error": f"存档不存在: {old_name}"}
        if new_path.exists():
            return {"success": False, "error": f"已存在同名存档: {new_name}"}
        try:
            old_path.rename(new_path)
        except OSError as e:
            self._log_error("重命名图存档", e)
            return {"success": False, "error": f"重命名图存档失败: {e}"}
        return {"success": True,
                "data": {"old_name": old_name, "new_name": new_name}}

    def load_graph(self, name: str = DEFAULT_GRAPH_NAME) -> Dict[str, Any]:
        """从 DataProvider 恢复指定图；不存在/损坏时回退预置示例图

        加载结果写入图快照并经 PipelineController 同步；UI 随后读取
        current_graph 并 canvas.from_dict 恢复画布。

        读出存档后先执行引脚迁移（幂等）：污染期保存的旧存档引脚在此
        被纠正为标准定义，保证 UI 恢复的画布与运行路径都拿到干净图；
        controller 的 update_graph 入口会再迁移一次，幂等无改动。
        """
        graph_name = name or DEFAULT_GRAPH_NAME
        graph_dict = self._read_saved_graph(graph_name)
        fallback = graph_dict is None
        if fallback:
            graph_dict = self._read_preset_graph()
        graph_dict, _migrated = graph_migration.migrate_graph_dict(
            graph_dict, node_catalog.defs_by_type())
        self.update_graph(graph_dict)
        return {"success": True, "data": {"name": graph_name, "fallback": fallback}}

    def list_node_types(self) -> Dict[str, Any]:
        """列出全部已注册节点类型（剔除不可序列化的 op 可调用对象）"""
        nodes = [self._node_definition_to_dict(d) for d in node_catalog.NODE_DEFINITIONS]
        return {"success": True, "data": {"nodes": nodes}}

    def get_last_result_info(self) -> Dict[str, Any]:
        """最近一次运行的汇总信息与 preview 结果元数据（不含图像本体）"""
        info = dict(self._runtime.controller.last_result_info or {})
        return {"success": True, "data": info}

    # ------------------------------------------------------------------
    #  供 UI 层调用的内部方法（不在 service_api 声明内，不注册跨插件 API）
    # ------------------------------------------------------------------

    def update_graph(self, graph_dict: Dict[str, Any]) -> None:
        """同步最新图快照：UI 在图变更（含 load_graph 恢复）后调用

        Args:
            graph_dict: canvas.to_dict 格式的图序列化字典
        """
        self._runtime.update_graph(graph_dict)

    @property
    def current_graph(self) -> Dict[str, Any]:
        """当前图快照（load_graph 后由 UI 读取并 canvas.from_dict 恢复画布）"""
        return self._runtime.current_graph

    def shutdown(self) -> None:
        """卸载清理：请求停止运行中的管线（信号断开由 entrance 逐项容错处理）"""
        self._runtime.controller.request_stop()

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
        """读取 DataProvider 存档图；不存在返回 None，损坏记 WARNING 并返回 None

        先校验图名合法性（拒绝路径穿越字符，替代原 get_asset_path 的
        读侧消毒），再 is_file 预检：存档不存在属正常路径（首次启动 /
        未保存过），静默回退预置图不记 WARNING，避免日志噪音。
        """
        if self._validate_graph_name(name) is not None:
            return None  # 非法图名按不存在处理（不读盘）
        path = self._storage_dir() / f"{name}{GRAPH_FILE_SUFFIX}"
        if not path.is_file():
            return None  # 存档不存在：正常回退路径，不记日志
        try:
            with open(path, "rb") as f:
                return json.loads(f.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.warning(LOG_TAG, f"读取图存档失败（回退示例图）: {name}: {e}")
            return None

    def _read_preset_graph(self) -> Dict[str, Any]:
        """读取插件资产中的预置示例图；缺失/损坏时记日志并回退空图

        预置图中的 file_path 属性以相对插件目录路径存放（资产可移植，
        不绑定开发机绝对路径），读出后统一解析为绝对路径。
        """
        preset_path = _PLUGIN_ROOT / PRESET_GRAPH_RELATIVE_PATH
        try:
            with open(preset_path, "rb") as f:
                graph_dict = json.loads(f.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.warning(LOG_TAG, f"预置示例图不可用（回退空图）: {e}")
            return dict(runtime_registry.EMPTY_GRAPH)
        return self._resolve_preset_paths(graph_dict)

    @staticmethod
    def _resolve_preset_paths(graph_dict: Dict[str, Any]) -> Dict[str, Any]:
        """把预置图中相对插件目录的 file_path 属性解析为绝对路径（就地修改）。"""
        nodes = graph_dict.get("graph", graph_dict).get("nodes", [])
        for node in nodes:
            props = node.get("properties", {})
            path = str(props.get(_FILE_PATH_PROPERTY, "") or "")
            if path and not Path(path).is_absolute():
                props[_FILE_PATH_PROPERTY] = str(_PLUGIN_ROOT / path)
        return graph_dict

    @staticmethod
    def _asset_filename(name: str) -> str:
        """组装图存档文件名（命名空间子目录 + 图名 + 扩展名）"""
        return f"{GRAPH_STORAGE_NAMESPACE}/{name}{GRAPH_FILE_SUFFIX}"

    def _graph_file_meta(self, path: Path) -> Dict[str, Any]:
        """单个存档文件的元信息（SPEC-graph-list §1.3；节点数读取失败为 None）。"""
        stat = path.stat()
        modified = datetime.fromtimestamp(stat.st_mtime)
        return {
            "name": path.stem,
            "node_count": self._read_graph_node_count(path),
            "size_bytes": stat.st_size,
            "modified_at": modified.isoformat(sep=" ", timespec="seconds"),
        }

    def _read_graph_node_count(self, path: Path) -> Optional[int]:
        """读取存档文件的节点数；损坏 / 不可读时记 WARNING 并返回 None。"""
        try:
            with open(path, "rb") as f:
                return self._node_count(json.loads(f.read().decode("utf-8")))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
            self._logger.warning(LOG_TAG, f"读取存档节点数失败: {path.name}: {e}")
            return None

    @staticmethod
    def _validate_graph_name(name: str) -> Optional[str]:
        """校验图名合法性（SPEC §1.4）；合法返回 None，否则返回中文错误原因。"""
        if not name or not name.strip():
            return "图名不能为空"
        if any(char in name for char in INVALID_NAME_CHARS):
            return f"图名含非法字符（{INVALID_NAME_CHARS}）"
        return None

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
