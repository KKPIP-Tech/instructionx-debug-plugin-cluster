"""
文本格式化插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class TextFormattingPluginInfo(IPluginInfo):
    """文本格式化插件元数据"""

    @property
    def version(self) -> PluginVersion:
        return PluginVersion.from_string("release.1.0.0")

    @property
    def developer(self) -> str:
        return "KKPIP-Tech"

    @property
    def developer_email(self) -> str:
        return "support@example.com"

    @property
    def developer_website(self) -> str:
        return "https://github.com/KKPIP-Tech/InstructionX"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return "文本格式化插件提供常用的文本处理工具，包括文本大小写转换（大写、小写）和批量文本处理。适用于数据处理、内容编辑等场景。"

    @property
    def service_api(self) -> Dict[str, Any]:
        def api(name, params, returns):
            return {"description": name, "parameters": params, "returns": returns}
        text_param = {"text": {"type": "str", "description": "输入文本", "required": True}}
        return {
            "to_uppercase": api("将文本转换为大写", text_param, {"type": "str", "description": "大写后的文本"}),
            "to_lowercase": api("将文本转换为小写", text_param, {"type": "str", "description": "小写后的文本"})
        }

    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_ArrowForward")

    @property
    def skill_description(self) -> str:
        return "提供文本格式化工具"

    @property
    def tags(self) -> Optional[list[str]]:
        return ["text", "formatting", "utility"]

    @property
    def dependencies(self) -> Dict[str, str]:
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "text-formatting"