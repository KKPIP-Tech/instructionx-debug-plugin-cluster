"""
字符串工具插件服务层

作为接口层，仅封装 function 子模块的方法，不包含任何业务逻辑和 UI 操作。
"""

from .function.services.core_service import CoreService as _Impl


class Service:
    """字符串工具服务类（接口层）"""

    def __init__(self, plugin_id: str):
        self._impl = _Impl(plugin_id)

    def to_uppercase(self, text: str) -> str:
        return self._impl.to_uppercase(text)

    def to_lowercase(self, text: str) -> str:
        return self._impl.to_lowercase(text)

    def reverse_text(self, text: str) -> str:
        return self._impl.reverse_text(text)

    def capitalize_words(self, text: str) -> str:
        return self._impl.capitalize_words(text)

    def count_words(self, text: str) -> int:
        return self._impl.count_words(text)

    def count_chars(self, text: str, include_spaces: bool = True) -> int:
        return self._impl.count_chars(text, include_spaces)

    def remove_whitespace(self, text: str) -> str:
        return self._impl.remove_whitespace(text)