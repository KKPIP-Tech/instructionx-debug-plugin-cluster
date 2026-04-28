"""
单位转换插件元数据
"""

from core.interfaces import IPluginInfo
from core.plugin.plugin_version import PluginVersion
from core.plugin.plugin_icon import PluginIcon
from typing import Dict, Any, Optional


class UnitConverterPluginInfo(IPluginInfo):
    """单位转换插件元数据"""
    
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
        return """
        单位转换插件提供常用的单位转换工具，包括：
        - 长度单位转换（米、千米、厘米、毫米、英寸、英尺）
        - 重量单位转换（千克、克、毫克、磅、盎司）
        - 温度单位转换（摄氏度、华氏度、开尔文）
        
        该插件适用于需要在不同单位之间转换的场景，
        如科学研究、工程计算、日常使用等。
        """
    
    @property
    def service_api(self) -> Dict[str, Any]:
        def conv_params(from_unit: str, from_desc: str) -> Dict:
            return {"value": {"type": "float", "description": "数值", "required": True}, "from_unit": {"type": "str", "description": from_desc, "required": True}, "to_unit": {"type": "str", "description": "目标单位", "required": True}}
        ret = {"type": "float", "description": "转换后的数值"}
        return {
            "length_converter": self._api("长度单位转换", conv_params("源单位 (m, km, cm, mm, inch, ft)"), ret),
            "weight_converter": self._api("重量单位转换", conv_params("源单位 (kg, g, mg, lb, oz)"), ret),
            "temperature_converter": self._api("温度单位转换", conv_params("源单位 (C, F, K)"), ret)
        }

    def _api(self, desc: str, params: Dict, returns: Dict) -> Dict:
        return {"description": desc, "parameters": params, "returns": returns}
    
    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_ArrowUp")
    
    @property
    def skill_description(self) -> str:
        return "提供单位转换工具"
    
    @property
    def tags(self) -> Optional[list[str]]:
        return ["unit", "conversion", "utility"]
    
    @property
    def dependencies(self) -> Dict[str, str]:
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "unit-converter"