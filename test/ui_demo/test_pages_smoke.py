# -*- coding: utf-8 -*-
"""ui_demo 各演示页 UI 冒烟测试（offscreen）。

覆盖范围：
- NAV 注册表自身结构（键唯一、工厂可调用）；
- 每个页面工厂 ``create_page(i18n=None)`` 能实例化为 QWidget 且不抛异常；
- 蓝图页重点用例：节点类型注册幂等、预置图结构（6 节点 / 9 边 /
  exec 拓扑序）、属性 schema 结构、运行模拟（单步 / 连续 / 重置）、
  JSON 保存-加载回环；
- MainWidget 集成冒烟：导航树叶子覆盖全部 NAV 页面、页面懒加载缓存。

不断言任何视觉细节，仅验证结构契约与「可构建、可驱动」。

i18n 说明：插件页面文案经取词门面翻译（门面缺失时降级为键名）。
本模块用 session 级 fixture 注册 ui_demo 真实语言包并注入门面，
使文案断言（「就绪」「模拟完成」等）面向真实中文译文而非键名。
"""

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from core.i18n import get_language_manager
from core.i18n.facade import PluginI18nFacade
from plugin.ui_demo.ui.main_widget import MainWidget
from plugin.ui_demo.ui.pages import NAV
from plugin.ui_demo.ui.pages.blueprint import (
    PROPERTY_SCHEMAS,
    BlueprintDemoPage,
    exec_order,
    register_demo_node_types,
)

#: ui_demo 插件目录（text/zh.xml 语言包所在）
_UI_DEMO_DIR = Path(__file__).resolve().parents[2] / "ui_demo"

#: 预置流水线节点数（开始→加载→预处理→推理→后处理→保存）
_PRESET_NODE_COUNT = 6
#: 预置图边数（5 条 exec 链 + 4 条数据引脚）
_PRESET_EDGE_COUNT = 9

#: 展平 NAV 为 (页面键, 分类键, 工厂) 供参数化
#: （NAV 结构为 [(分类键, [(页面键, 工厂), ...]), ...]，标题由取词门面派生）
_ALL_PAGES = [
    (page_key, cat_key, factory)
    for cat_key, pages in NAV
    for page_key, factory in pages
]


@pytest.fixture(scope="session")
def i18n_facade() -> PluginI18nFacade:
    """注册 ui_demo 语言包并返回绑定测试插件 id 的取词门面（中文）。"""
    manager = get_language_manager()
    plugin_id = "pytest-ui-demo-pages"
    manager.register_plugin_texts(plugin_id, _UI_DEMO_DIR)
    manager.set_language("zh")
    return PluginI18nFacade(plugin_id)


def _settle_page(qapp, page: QWidget) -> None:
    """让页面进入「已显示」稳态并处理一轮事件。

    anim_painted 页内的 ScrollReveal 在视口未就绪时会以
    ``QTimer.singleShot(30)`` 重试扫描（最多约 1.8s）；若控件在重试
    期间被销毁，残留的 singleShot 回调会在事件循环中抛
    ``RuntimeError: C++ object already deleted``。测试侧 show + 处理
    事件使扫描一次成功、不再残留重试，保证 teardown 干净。
    """
    page.resize(1024, 768)
    page.show()
    qapp.processEvents()
    qapp.processEvents()


class TestNavStructure:
    """NAV 注册表自身结构契约。"""

    def test_nav_non_empty(self) -> None:
        """NAV 应为非空分类列表。"""
        assert isinstance(NAV, list) and NAV

    def test_page_keys_unique(self) -> None:
        """全部页面键不允许重复。"""
        keys = [key for key, _c, _f in _ALL_PAGES]
        assert len(keys) == len(set(keys))

    def test_factories_callable(self) -> None:
        """每个页面条目第二项应为可调用工厂。"""
        for key, _c, factory in _ALL_PAGES:
            assert callable(factory), f"页面 {key} 的工厂不可调用"


class TestPageFactoriesSmoke:
    """逐页实例化冒烟（每个工厂返回 QWidget 且不抛异常）。"""

    @pytest.mark.parametrize(
        "page_key,cat_key,factory",
        _ALL_PAGES,
        ids=[key for key, _c, _f in _ALL_PAGES],
    )
    def test_create_page_returns_widget(
            self, qapp, qtbot, i18n_facade, page_key, cat_key, factory) -> None:
        """页面工厂应返回 QWidget 实例（offscreen 下构建不抛异常）。"""
        page = factory(i18n_facade)
        qtbot.addWidget(page)
        assert isinstance(page, QWidget), (
            f"{cat_key} / {page_key} 未返回 QWidget")
        _settle_page(qapp, page)


class TestBlueprintNodeRegistration:
    """蓝图节点类型注册与属性 schema。"""

    def test_register_node_types_idempotent(self, qapp, qtbot, i18n_facade) -> None:
        """重复注册同名节点类型应安全（同名覆盖），页面仍可正常构建。"""
        register_demo_node_types()
        register_demo_node_types()
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        assert len(page.graph.nodes()) == _PRESET_NODE_COUNT

    def test_property_schemas_shape(self) -> None:
        """PROPERTY_SCHEMAS 每条 schema 应满足类型-长度约定且默认值合法。"""
        expected_len = {"int": 6, "float": 6, "choice": 5, "text": 4, "bool": 4}
        assert PROPERTY_SCHEMAS, "属性 schema 不允许为空"
        for type_name, specs in PROPERTY_SCHEMAS.items():
            assert isinstance(type_name, str) and type_name
            for spec in specs:
                kind = spec[0]
                assert kind in expected_len, f"未知属性类型 {kind}"
                assert len(spec) == expected_len[kind]
                self._assert_default_valid(spec)

    def _assert_default_valid(self, spec) -> None:
        """校验单条 schema 的默认值取值合法。"""
        kind, _key, _label, default = spec[:4]
        if kind in ("int", "float"):
            low, high = spec[4], spec[5]
            assert low <= default <= high, "数值默认值应落在 [最小, 最大] 区间"
            assert low <= high, "最小值不应大于最大值"
        elif kind == "choice":
            assert default in spec[4], "选项默认值应在候选列表内"


class TestBlueprintPresetGraph:
    """蓝图页预置流水线结构。"""

    def test_preset_nodes_and_edges(self, qapp, qtbot, i18n_facade) -> None:
        """预置图应含 6 个节点、9 条边，且 preset_ids 记录 6 个节点 id。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        assert len(page.graph.nodes()) == _PRESET_NODE_COUNT
        assert len(page.graph.edges()) == _PRESET_EDGE_COUNT
        assert len(page.preset_ids) == _PRESET_NODE_COUNT

    def test_exec_order_matches_preset_chain(self, qapp, qtbot, i18n_facade) -> None:
        """exec 拓扑序应与预置链顺序一致（开始 → … → 保存）。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        assert exec_order(page.graph) == page.preset_ids

    def test_preset_nodes_have_default_properties(self, qapp, qtbot, i18n_facade) -> None:
        """带 schema 的预置节点应在构建时写入默认属性（如 CNN 层数 18）。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        cnn_id = page.preset_ids[3]
        cnn = page.graph.node(cnn_id)
        assert cnn.type_name == "cnn"
        assert cnn.properties["layers"] == 18
        assert cnn.properties["channels"] == 64

    def test_exec_order_empty_graph_fallback(self, qapp) -> None:
        """无 exec 边的图应回退为节点插入序（本用例：空图返回空序列）。"""
        from InstructionX_UIKit.blueprint import BlueprintGraph
        assert exec_order(BlueprintGraph()) == []


class TestBlueprintRunSimulation:
    """蓝图页运行模拟（纯 UI 状态机，无业务逻辑）。"""

    @pytest.fixture()
    def page(self, qapp, qtbot, i18n_facade) -> BlueprintDemoPage:
        """构建零延迟的蓝图页（delay_range 置 0 加速模拟）。"""
        widget = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(widget)
        widget.delay_range = (0, 0)
        return widget

    def test_step_once_advances_nodes(self, page) -> None:
        """逐次「单步」应依次推进节点，完成后状态标签汇报总数。"""
        for _ in range(_PRESET_NODE_COUNT):
            page.step_once()
        assert "模拟完成" in page.status_label.text()
        assert str(_PRESET_NODE_COUNT) in page.status_label.text()

    def test_run_all_completes(self, page, qtbot) -> None:
        """「运行」应经 QTimer 连续推进至全部节点完成。"""
        page.run_all()
        qtbot.waitUntil(lambda: "模拟完成" in page.status_label.text(),
                        timeout=5000)

    def test_step_ignored_while_running(self, page, qtbot) -> None:
        """连续运行进行中「单步」应被忽略且按钮置灰（防 QTimer 交错推进）。"""
        page.delay_range = (50, 50)
        page.run_all()
        assert not page.step_button.isEnabled()
        idx_before = page._idx
        page.step_once()
        assert page._idx == idx_before
        qtbot.waitUntil(lambda: "模拟完成" in page.status_label.text(),
                        timeout=5000)
        assert page.step_button.isEnabled()

    def test_reset_restores_idle(self, page) -> None:
        """「重置」应中断模拟并恢复就绪状态。"""
        page.run_all()
        page.reset_run()
        assert page.status_label.text() == "就绪"


class TestBlueprintJsonRoundTrip:
    """蓝图页 JSON 序列化（offscreen 下降级路径重定向到 tmp_path）。"""

    def test_save_and_load_round_trip(self, qapp, qtbot, i18n_facade, tmp_path,
                                      monkeypatch) -> None:
        """保存后加载应还原节点/边数量，状态标签汇报加载结果。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        target = tmp_path / "graph.json"
        monkeypatch.setattr(page, "_json_path", lambda save: str(target))

        page.save_json()
        assert target.exists(), "保存后应生成 JSON 文件"
        with open(target, encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict) and data, "JSON 内容应为非空对象"

        page.load_json()
        assert len(page.graph.nodes()) == _PRESET_NODE_COUNT
        assert len(page.graph.edges()) == _PRESET_EDGE_COUNT
        assert "已加载" in page.status_label.text()

    def test_load_invalid_json_reports_failure(self, qapp, qtbot, i18n_facade, tmp_path,
                                               monkeypatch) -> None:
        """加载损坏的 JSON 应汇报失败且不抛异常、图保持原状。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        bad = tmp_path / "broken.json"
        bad.write_text("{ 这不是合法 JSON", encoding="utf-8")
        monkeypatch.setattr(page, "_json_path", lambda save: str(bad))

        page.load_json()
        assert "加载失败" in page.status_label.text()
        assert len(page.graph.nodes()) == _PRESET_NODE_COUNT

    def test_load_missing_file_reports_failure(self, qapp, qtbot, i18n_facade, tmp_path,
                                               monkeypatch) -> None:
        """加载不存在的文件应汇报失败且不抛异常。"""
        page = BlueprintDemoPage(i18n=i18n_facade)
        qtbot.addWidget(page)
        missing = tmp_path / "not_exist.json"
        monkeypatch.setattr(page, "_json_path", lambda save: str(missing))

        page.load_json()
        assert "加载失败" in page.status_label.text()


class TestMainWidgetIntegration:
    """主控件集成冒烟：导航树与懒加载缓存。"""

    def test_nav_leaves_cover_all_pages(self, qapp, qtbot, i18n_facade) -> None:
        """导航树叶子节点应覆盖 NAV 全部页面（数量一致、键一致）。"""
        widget = MainWidget(i18n=i18n_facade)
        qtbot.addWidget(widget)
        leaves = widget.nav_leaves()
        assert len(leaves) == len(_ALL_PAGES)
        assert [key for key, _t, _i in leaves] == [k for k, _c, _f in _ALL_PAGES]

    def test_show_page_lazy_cache(self, qapp, qtbot, i18n_facade) -> None:
        """同一页面键两次 show_page 应复用缓存实例（懒加载只构建一次）。"""
        widget = MainWidget(i18n=i18n_facade)
        qtbot.addWidget(widget)
        page_key, _c, factory = _ALL_PAGES[0]

        widget.show_page(page_key, factory)
        first = widget._page_cache[page_key]
        widget.show_page(page_key, factory)
        assert widget._page_cache[page_key] is first
        assert widget._stack.currentWidget() is first

    def test_iterate_all_leaves_no_exception(self, qapp, qtbot, i18n_facade) -> None:
        """经主控件遍历全部导航叶子加载页面，均不抛异常。"""
        widget = MainWidget(i18n=i18n_facade)
        qtbot.addWidget(widget)
        _settle_page(qapp, widget)
        for page_key, _title, item in widget.nav_leaves():
            _key, factory = item.data(0, Qt.UserRole)
            widget.show_page(page_key, factory)
        qapp.processEvents()
        assert len(widget._page_cache) == len(_ALL_PAGES)
