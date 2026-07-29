"""
字符串工具插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional

class StringToolsPluginInfo(IPluginInfo):
    """字符串工具插件元数据"""
    
    @property
    def version(self) -> PluginVersion:
        """插件版本"""
        return PluginVersion.from_string("release.1.1.0")
    
    @property
    def developer(self) -> str:
        """开发者名称"""
        return "KKPIP-Tech"
    
    @property
    def developer_email(self) -> str:
        """开发者邮箱"""
        return "support@example.com"
    
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
        return """
        字符串工具插件提供丰富的文本处理功能，包括：
        - 文本大小写转换（大写、小写）
        - 文本反转
        - 单词首字母大写
        - 单词统计
        - 字符统计
        - 移除空白字符
        
        该插件提供了多个 API 方法，可以被其他插件调用，
        用于处理各种字符串操作。
        
        示例使用场景：
        - 文本格式化工具
        - 数据清洗
        - 内容编辑
        - 自动化文本处理
        """
    
    @property
    def service_api(self) -> Dict[str, Any]:
        """Service API 定义"""
        text_param = {"text": {"type": "str", "description": "输入文本", "required": True}}
        ret_str = {"type": "str", "description": "处理结果"}
        ret_int = {"type": "int", "description": "统计结果"}
        return {
            "to_uppercase": self._api("将文本转换为大写", text_param, ret_str),
            "to_lowercase": self._api("将文本转换为小写", text_param, ret_str),
            "reverse_text": self._api("反转文本", text_param, ret_str),
            "capitalize_words": self._api("将每个单词的首字母大写", text_param, ret_str),
            "count_words": self._api("统计单词数量", text_param, ret_int),
            "count_chars": self._api("统计字符数量", {"text": {"type": "str", "description": "输入文本", "required": True}, "include_spaces": {"type": "bool", "description": "是否包含空格", "required": False, "default": True}}, ret_int),
            "remove_whitespace": self._api("移除所有空白字符", text_param, ret_str)
        }

    def _api(self, desc: str, params: Dict, returns: Dict) -> Dict:
        return {"description": desc, "parameters": params, "returns": returns}
    
    @property
    def skill_icon(self) -> PluginIcon:
        """插件图标配置"""
        return PluginIcon.builtin("SP_ArrowForward")
    
    @property
    def skill_description(self) -> str:
        """插件简短描述"""
        return "提供字符串处理工具"
    
    @property
    def tags(self) -> Optional[list[str]]:
        """插件标签"""
        return ["text", "string", "formatting", "utility"]

    @property
    def dependencies(self) -> Dict[str, str]:
        """依赖项"""
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "string-tools"
