# -*- coding: utf-8 -*-
"""ui_demo 服务层（Service / CoreService）方法路径测试。

覆盖范围：
- ``Service()`` 无参实例化（兼容框架签名分析的实例化约定）；
- ``get_control_list`` 正常路径：返回「分类 · 页面标题」字符串列表，
  数量、顺序与 COMPONENT_CATALOG / NAV 一致；
- 边界与一致性：条目非空白、无重复、与 NAV 页面一一对应；
- 多次调用返回独立列表（修改返回值不影响后续调用）。
"""

from plugin.ui_demo.function.component_catalog import COMPONENT_CATALOG
from plugin.ui_demo.service import Service
from plugin.ui_demo.ui.pages import NAV

from ._helpers import nav_title_map

#: 目录页面总数（预期清单长度）
_EXPECTED_COUNT = sum(len(pages) for _c, pages in COMPONENT_CATALOG)


class TestServiceInstantiation:
    """Service 实例化约定。"""

    def test_no_arg_instantiation(self) -> None:
        """Service 应支持无参构造（框架签名分析的兜底组合之一）。"""
        service = Service()
        assert service is not None


class TestGetControlList:
    """get_control_list 正常路径与一致性。"""

    def setup_method(self) -> None:
        """每个用例构造独立 Service 并取一次清单。"""
        self.service = Service()
        self.items = self.service.get_control_list()

    def test_returns_list_of_str(self) -> None:
        """返回值应为非空字符串列表，条目均为非空白字符串。"""
        assert isinstance(self.items, list) and self.items
        for item in self.items:
            assert isinstance(item, str)
            assert item.strip(), "清单条目不允许为空白"

    def test_count_matches_catalog(self) -> None:
        """清单长度应等于目录页面总数。"""
        assert len(self.items) == _EXPECTED_COUNT

    def test_item_format(self) -> None:
        """条目应遵循「分类 · 页面标题」格式（含分隔符）。"""
        for item in self.items:
            category, sep, title = item.partition(" · ")
            assert sep, f"条目缺少分隔符：{item}"
            assert category.strip() and title.strip()

    def test_order_and_content_match_catalog(self) -> None:
        """清单条目应与目录逐条一致（含顺序）。"""
        expected = [f"{category} · {title}"
                    for category, pages in COMPONENT_CATALOG
                    for title in pages]
        assert self.items == expected

    def test_matches_nav_titles(self) -> None:
        """清单条目应与 NAV 页面标题一一对应（含顺序，标题经 zh.xml 翻译）。"""
        titles = nav_title_map()
        expected = [f"{titles[f'cat.{cat_key}']} · {titles[f'page.{page_key}']}"
                    for cat_key, pages in NAV
                    for page_key, _f in pages]
        assert self.items == expected

    def test_first_and_last_entries(self) -> None:
        """首条目为设计令牌总览、末条目为蓝图节点图（顺序锚点）。"""
        assert self.items[0] == "设计令牌 · 设计令牌总览"
        assert self.items[-1] == "蓝图 · 蓝图（节点图）"

    def test_no_duplicate_items(self) -> None:
        """清单条目不允许重复。"""
        assert len(self.items) == len(set(self.items))


class TestGetControlListRobustness:
    """get_control_list 边界与隔离性。"""

    def test_repeated_calls_return_independent_lists(self) -> None:
        """多次调用应返回内容相同的独立列表（改返回值不污染后续调用）。"""
        service = Service()
        first = service.get_control_list()
        first.append("被污染的条目")
        second = service.get_control_list()
        assert "被污染的条目" not in second
        assert len(second) == _EXPECTED_COUNT

    def test_result_is_plain_data(self) -> None:
        """返回值应为纯数据（可 JSON 序列化），不携带 Qt 对象。"""
        import json
        service = Service()
        json.dumps(service.get_control_list(), ensure_ascii=False)
