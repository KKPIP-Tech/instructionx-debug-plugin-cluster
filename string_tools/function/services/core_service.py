"""
字符串工具核心业务逻辑

提供各种字符串处理算法，不依赖任何 UI 框架。
"""


class CoreService:
    """字符串工具核心服务"""

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id

    def to_uppercase(self, text: str) -> str:
        """将文本转换为大写"""
        return text.upper()

    def to_lowercase(self, text: str) -> str:
        """将文本转换为小写"""
        return text.lower()

    def reverse_text(self, text: str) -> str:
        """反转文本"""
        return text[::-1]

    def capitalize_words(self, text: str) -> str:
        """将每个单词的首字母大写"""
        return ' '.join(word.capitalize() for word in text.split())

    def count_words(self, text: str) -> int:
        """统计单词数量"""
        return len(text.split())

    def count_chars(self, text: str, include_spaces: bool = True) -> int:
        """统计字符数量"""
        if include_spaces:
            return len(text)
        return len(text.replace(" ", ""))

    def remove_whitespace(self, text: str) -> str:
        """移除所有空白字符"""
        return ''.join(text.split())
