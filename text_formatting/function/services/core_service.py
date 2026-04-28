"""
文本格式化核心业务逻辑

提供文本大小写转换等基础操作，不依赖任何 UI 框架。
"""


class CoreService:
    """文本格式化核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def to_uppercase(self, text: str) -> str:
        """将文本转换为大写"""
        return text.upper()

    def to_lowercase(self, text: str) -> str:
        """将文本转换为小写"""
        return text.lower()
