"""
代码格式化核心业务逻辑

提供 JSON 格式化、注释移除、代码压缩等功能，不依赖任何 UI 框架。
"""

import json
import re
from xml.dom.minidom import parseString


class CoreService:
    """代码格式化核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def format_json(self, json_str: str) -> str:
        """格式化 JSON 字符串"""
        try:
            data = json.loads(json_str)
            return json.dumps(data, indent=4, ensure_ascii=False)
        except Exception as e:
            return f"JSON格式错误: {e}"

    def format_xml(self, xml_str: str) -> str:
        """格式化 XML 字符串"""
        try:
            dom = parseString(xml_str)
            return dom.toprettyxml(indent="  ")
        except Exception as e:
            return f"XML格式错误: {e}"

    def remove_comments(self, code: str, language: str = "python") -> str:
        """移除代码注释"""
        try:
            handlers = {
                "python": lambda c: '\n'.join(
                    re.sub(r'#.*$', '', line) for line in c.split('\n')),
                "javascript": lambda c: re.sub(
                    r'/\*.*?\*/', '', re.sub(r'//.*', '', c), flags=re.DOTALL),
            }
            return handlers.get(language, lambda c: c)(code)
        except Exception as e:
            return f"移除注释错误: {e}"

    def compress_code(self, code: str) -> str:
        """压缩代码（移除空白字符）"""
        try:
            lines = []
            for line in code.split('\n'):
                stripped = line.strip()
                if stripped:
                    lines.append(stripped)
            return '\n'.join(lines)
        except Exception as e:
            return f"压缩代码错误: {e}"
