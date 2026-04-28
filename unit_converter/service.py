"""
单位转换插件 — 接口层

封装 CoreService，提供插件所需的转换方法。
"""

from .function.services.core_service import CoreService as _CoreService


class UnitConverterService:
    """单位转换服务（接口层）"""

    def __init__(self, plugin_id: str):
        self._core = _CoreService(plugin_id)

    def length_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        return self._core.length_converter(value, from_unit, to_unit)

    def weight_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        return self._core.weight_converter(value, from_unit, to_unit)

    def temperature_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        return self._core.temperature_converter(value, from_unit, to_unit)
