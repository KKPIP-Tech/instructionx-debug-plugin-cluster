"""
单位转换核心业务逻辑

提供长度、重量、温度单位之间的转换算法，不依赖任何 UI 框架。
"""

import json
from pathlib import Path


class CoreService:
    """单位转换核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self._config = self._load_config()

    def _load_config(self) -> dict:
        """加载配置文件"""
        config_path = Path(__file__).parent.parent.parent / "config" / "default.json"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def length_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        长度单位转换

        Args:
            value: 数值
            from_unit: 源单位 (m, km, cm, mm, inch, ft)
            to_unit: 目标单位

        Returns:
            转换后的数值
        """
        factors = self._config.get("conversion_factors", {}).get("length", {}).get("to_base", {})
        value_in_meters = value * factors.get(from_unit, 1)
        return value_in_meters / factors.get(to_unit, 1)

    def weight_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        """
        重量单位转换

        Args:
            value: 数值
            from_unit: 源单位 (kg, g, mg, lb, oz)
            to_unit: 目标单位

        Returns:
            转换后的数值
        """
        factors = self._config.get("conversion_factors", {}).get("weight", {}).get("to_base", {})
        value_in_kg = value * factors.get(from_unit, 1)
        return value_in_kg / factors.get(to_unit, 1)

    def _to_celsius(self, value: float, from_unit: str) -> float:
        """转换为摄氏度"""
        cfg = self._config.get("conversion_factors", {}).get("temperature", {})
        if from_unit == 'C':
            return value
        elif from_unit == 'F':
            return (value - cfg.get("fahrenheit_offset", 32)) / cfg.get("fahrenheit_slope", 1.8)
        elif from_unit == 'K':
            return value - cfg.get("celsius_offset", 273.15)
        return value

    def _from_celsius(self, value_in_c: float, to_unit: str) -> float:
        """从摄氏度转换"""
        cfg = self._config.get("conversion_factors", {}).get("temperature", {})
        if to_unit == 'C':
            return value_in_c
        elif to_unit == 'F':
            return value_in_c * cfg.get("fahrenheit_slope", 1.8) + cfg.get("fahrenheit_offset", 32)
        elif to_unit == 'K':
            return value_in_c + cfg.get("celsius_offset", 273.15)
        return value_in_c

    def temperature_converter(self, value: float, from_unit: str, to_unit: str) -> float:
        """温度单位转换"""
        return self._from_celsius(self._to_celsius(value, from_unit), to_unit)
