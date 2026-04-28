"""
颜色转换核心业务逻辑

提供颜色格式之间的转换算法，不依赖任何 UI 框架。
"""

import json
from pathlib import Path


class CoreService:
    """颜色转换核心服务"""

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

    def hex_to_rgb(self, hex_str: str) -> str:
        """将 HEX 颜色格式转换为 RGB 格式"""
        cfg = self._config
        prefix = cfg.get("hex_prefix", "#")
        expected_len = cfg.get("hex_length", 6)
        error_msg = cfg.get("error_message", "无效的 HEX 格式")
        if hex_str.startswith(prefix):
            hex_str = hex_str[len(prefix):]
        if len(hex_str) != expected_len:
            return error_msg
        try:
            r, g, b = int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16)
            return f"rgb({r}, {g}, {b})"
        except ValueError:
            return error_msg
