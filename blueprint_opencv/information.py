"""
Blueprint OpenCV 插件元数据

基于 InstructionX_UIKit Blueprint 的 OpenCV 节点化图像处理蓝图编辑器。
service_api 声明的九个方法由 service.py 的 BlueprintOpenCVService 实现，
框架自动注册为跨插件 API 并同步为 MCP 工具。
"""

from typing import Any, Dict, Optional

from core.interfaces import IPluginInfo
from core.plugin.plugin_icon import PluginIcon
from core.plugin.plugin_version import PluginVersion

# 插件 Python 依赖（与 IXPlugin.json 的 dependencies 保持一致）
PLUGIN_DEPENDENCIES = {
    "opencv-python": ">=4.8.0",
    "numpy": ">=1.24.0",
}

# 插件详细描述（独立常量，保持 description 属性体简洁）
_PLUGIN_DESCRIPTION = """
Blueprint OpenCV 是一个基于 InstructionX_UIKit Blueprint 组件的
OpenCV 节点化图像处理蓝图编辑器，同时作为 Blueprint 用法的官方样板插件。

主要能力：
- 20 个内置节点：输入（加载图片/生成噪声/纯色）、基础（灰度/反色/缩放/
  翻转/旋转）、滤波（高斯/中值/双边）、阈值与边缘（固定/自适应/Canny）、
  形态学、调整（亮度对比度/锐化/HSV）、输出（预览/保存图片）
- exec/data 双链语义：exec 链决定执行顺序，image 链决定数据流向，
  上游未求值时按需递归求值并按节点缓存
- 参数编辑走右侧属性面板：按节点 param_schema 动态重建表单，
  修改即时写回 node.properties 并随图序列化
- 工作线程执行：cv2 处理经 BackgroundTaskManager 提交线程池，
  结果（PNG 字节 + 元数据）经 Qt 信号跨线程排队封送回 UI
- 图持久化：canvas.to_dict 序列化后经 DataProvider 保存/恢复，
  支持多命名存档（另存为/加载/重命名/删除），损坏存档自动回退预置示例图
- service_api 九方法供跨插件 / MCP 调用（运行、停止、保存、加载、
  存档枚举/重命名/删除、列出节点类型、查询最近运行结果）
"""

# save_graph / load_graph 共用的图名参数声明（service_api 契约）
_GRAPH_NAME_PARAM = {
    "name": {
        "type": "str",
        "description": "图名（存档 key，缺省 default）",
        "required": False,
    },
}


class BlueprintOpenCVPluginInfo(IPluginInfo):
    """Blueprint OpenCV 插件元数据"""

    @property
    def version(self) -> PluginVersion:
        """插件版本"""
        return PluginVersion.from_string("release.1.0.2")

    @property
    def developer(self) -> str:
        """开发者名称"""
        return "InstructionX"

    @property
    def developer_email(self) -> str:
        """开发者邮箱"""
        return "support@instructionx.dev"

    @property
    def developer_website(self) -> str:
        """开发者网站"""
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        """是否免费"""
        return True

    @property
    def description(self) -> str:
        """插件详细描述"""
        return _PLUGIN_DESCRIPTION

    @property
    def service_api(self) -> Dict[str, Any]:
        """Service API 定义（九个方法，与 service.py 实现逐一一致）"""
        return {
            **self._api_run_methods(),
            **self._api_graph_methods(),
            **self._api_info_methods(),
        }

    def _api_run_methods(self) -> Dict[str, Any]:
        """运行控制类 service_api 声明（run_pipeline / stop_pipeline）。"""
        return {
            "run_pipeline": self._api(
                "运行当前图管线（异步，工作线程执行）",
                {},
                {"type": "dict", "description": '{"success": bool, "data": {"started": bool}}，失败时含 "error"（中文原因）'},
            ),
            "stop_pipeline": self._api(
                "请求停止当前运行（协作式，当前节点完成后中断）",
                {},
                {"type": "dict", "description": '{"success": bool, "data": {"stopping": bool}}'},
            ),
        }

    def _api_graph_methods(self) -> Dict[str, Any]:
        """图持久化类 service_api 声明（save/load/list/delete/rename_graph）。"""
        return {
            "save_graph": self._api(
                "将当前图序列化并经 DataProvider 持久化",
                dict(_GRAPH_NAME_PARAM),
                {"type": "dict", "description": '{"success": bool, "data": {"name": str, "node_count": int}}'},
            ),
            "load_graph": self._api(
                "从 DataProvider 恢复指定图到画布；不存在/损坏时回退示例图",
                dict(_GRAPH_NAME_PARAM),
                {"type": "dict", "description": '{"success": bool, "data": {"name": str, "fallback": bool}}'},
            ),
            **self._api_graph_manage_methods(),
        }

    def _api_graph_manage_methods(self) -> Dict[str, Any]:
        """存档管理类 service_api 声明（list/delete/rename_graph，SPEC-graph-list §3.5）。"""
        return {
            "list_graphs": self._api(
                "枚举全部已保存图存档（名称/节点数/大小/修改时间）",
                {},
                {"type": "dict", "description": '{"success": bool, "data": {"graphs": [{"name", "node_count", "size_bytes", "modified_at"}, ...]}}'},
            ),
            "delete_graph": self._api(
                "删除指定图存档；存档不存在返回中文错误",
                {"name": {"type": "str", "description": "图名（存档 key）", "required": True}},
                {"type": "dict", "description": '{"success": bool, "data": {"name": str}}，失败时含 "error"（中文原因）'},
            ),
            "rename_graph": self._api(
                "重命名图存档；重名冲突/存档不存在返回中文错误",
                {
                    "old_name": {"type": "str", "description": "原图名", "required": True},
                    "new_name": {"type": "str", "description": "新图名", "required": True},
                },
                {"type": "dict", "description": '{"success": bool, "data": {"old_name": str, "new_name": str}}，失败时含 "error"（中文原因）'},
            ),
        }

    def _api_info_methods(self) -> Dict[str, Any]:
        """查询类 service_api 声明（list_node_types / get_last_result_info）。"""
        return {
            "list_node_types": self._api(
                "列出全部已注册节点类型（Blueprint 样板/动态表单场景使用）",
                {},
                {"type": "dict", "description": '{"success": bool, "data": {"nodes": [{"type_name", "title", "category", "inputs", "outputs", "param_schema", "description"}, ...]}}'},
            ),
            "get_last_result_info": self._api(
                "最近一次运行的汇总信息与 preview 结果元数据（不含图像本体）",
                {},
                {"type": "dict", "description": '{"success": bool, "data": {"status": str, "total_ms": float, "node_count": int, "errors": list, "preview": dict | null}}'},
            ),
        }

    def _api(self, desc: str, params: Dict, returns: Dict) -> Dict:
        """组装单个 service_api 方法描述"""
        return {"description": desc, "parameters": params, "returns": returns}

    @property
    def skill_icon(self) -> PluginIcon:
        """插件图标配置"""
        return PluginIcon.builtin("SP_FileDialogContentsView")

    @property
    def skill_description(self) -> str:
        """插件简短描述"""
        return "OpenCV 节点化图像处理蓝图编辑器"

    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["blueprint", "opencv", "image", "node-editor", "demo"]

    @property
    def dependencies(self) -> Dict[str, str]:
        """依赖项"""
        return PLUGIN_DEPENDENCIES

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "blueprint-opencv"
