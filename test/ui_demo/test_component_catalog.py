# -*- coding: utf-8 -*-
"""ui_demo 组件目录（component_catalog）完整性测试。

覆盖范围：
- ``COMPONENT_CATALOG`` 自身结构（分类/页面条目形态、无重复）；
- 目录与 ``ui/pages/__init__.py`` 的 ``NAV`` 注册表一致性
  （分类顺序一致、每个 NAV 条目在目录中有对应声明、逐页标题对齐）。
"""

from plugin.ui_demo.function.component_catalog import COMPONENT_CATALOG
from plugin.ui_demo.ui.pages import NAV


def _nav_categories() -> list:
    """提取 NAV 的分类标题序列。"""
    return [cat_title for _key, cat_title, _pages in NAV]


def _nav_titles_by_category() -> dict:
    """提取 NAV 的 {分类标题: [页面标题, ...]} 映射（保持顺序）。"""
    return {cat_title: [title for _key, title, _f in pages]
            for _key, cat_title, pages in NAV}


class TestCatalogStructure:
    """COMPONENT_CATALOG 数据自身结构。"""

    def test_catalog_non_empty(self) -> None:
        """目录应为非空列表。"""
        assert isinstance(COMPONENT_CATALOG, list)
        assert len(COMPONENT_CATALOG) > 0

    def test_entry_shape(self) -> None:
        """每个条目应为 (分类标题, [页面标题, ...])，且页面列表非空。"""
        for entry in COMPONENT_CATALOG:
            assert isinstance(entry, tuple) and len(entry) == 2
            category, pages = entry
            assert isinstance(category, str) and category.strip()
            assert isinstance(pages, list) and pages
            assert all(isinstance(title, str) and title.strip() for title in pages)

    def test_no_duplicate_categories(self) -> None:
        """分类标题不允许重复。"""
        categories = [category for category, _pages in COMPONENT_CATALOG]
        assert len(categories) == len(set(categories))

    def test_no_duplicate_pages_across_catalog(self) -> None:
        """页面标题在整份目录中不允许重复（跨分类同样去重）。"""
        titles = [title for _category, pages in COMPONENT_CATALOG
                  for title in pages]
        assert len(titles) == len(set(titles))


class TestCatalogNavConsistency:
    """目录与 NAV 注册表的一一对应关系。"""

    def test_category_order_matches_nav(self) -> None:
        """目录分类序列与 NAV 分类序列（含顺序）完全一致。"""
        catalog_categories = [c for c, _p in COMPONENT_CATALOG]
        assert catalog_categories == _nav_categories()

    def test_page_titles_match_nav_per_category(self) -> None:
        """每个分类下的页面标题序列与 NAV 完全一致（含顺序）。"""
        nav_map = _nav_titles_by_category()
        for category, pages in COMPONENT_CATALOG:
            assert category in nav_map, f"目录分类 {category} 未在 NAV 中注册"
            assert pages == nav_map[category], f"分类 {category} 页面与 NAV 不一致"

    def test_every_nav_page_declared_in_catalog(self) -> None:
        """NAV 中的每个页面条目在目录中均有对应声明（无遗漏）。"""
        catalog_titles = {title for _c, pages in COMPONENT_CATALOG
                          for title in pages}
        for _cat_key, cat_title, pages in NAV:
            for _page_key, page_title, _factory in pages:
                assert page_title in catalog_titles, (
                    f"NAV 页面「{cat_title} / {page_title}」未在目录中声明")

    def test_page_count_matches_nav(self) -> None:
        """目录页面总数与 NAV 页面总数一致。"""
        catalog_count = sum(len(p) for _c, p in COMPONENT_CATALOG)
        nav_count = sum(len(p) for _k, _t, p in NAV)
        assert catalog_count == nav_count
