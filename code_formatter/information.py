"""
代码格式化插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class CodeFormatterPluginInfo(IPluginInfo):
    """代码格式化插件元数据"""

    @property
    def version(self) -> PluginVersion:
        return PluginVersion.from_string("release.1.1.0")

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
        return "代码格式化插件提供 JSON/XML 格式化、注释移除、代码压缩等常用工具，适用于代码审查、数据清理等场景。"

    @property
    def service_api(self) -> Dict[str, Any]:
        return {
            "format_json": self._m("格式化JSON字符串", {"json_str": {"type": "str", "description": "JSON字符串", "required": True}}),
            "format_xml": self._m("格式化XML字符串", {"xml_str": {"type": "str", "description": "XML字符串", "required": True}}),
            "remove_comments": self._m("移除代码注释", {"code": {"type": "str", "description": "代码字符串", "required": True}, "language": {"type": "str", "description": "编程语言（python, javascript）", "required": True}}),
            "compress_code": self._m("压缩代码（移除空白字符）", {"code": {"type": "str", "description": "代码字符串", "required": True}})
        }

    def _m(self, desc: str, params: Dict = None) -> Dict:
        return {"description": desc, "parameters": params or {}, "returns": {"type": "str", "description": "处理结果"}}

    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_ArrowDown")

    @property
    def skill_description(self) -> str:
        return "提供代码格式化工具"

    @property
    def tags(self) -> Optional[list[str]]:
        return ["code", "formatting", "utility"]

    @property
    def dependencies(self) -> Dict[str, str]:
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符，用于代码层面的插件识别"""
        return "code-formatter"