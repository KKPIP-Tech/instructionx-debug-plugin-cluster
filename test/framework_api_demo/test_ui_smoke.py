# -*- coding: utf-8 -*-
"""MainWidget UI 冒烟测试（offscreen + pytest-qt）。

覆盖 ui/main_widget.py：
- MainWidget 实例化（注入六个真实演示服务，隔离 plugin_id + 隔离 DataProvider）；
- 右侧 Tabs 容器存在且恰为 6 个 Tab（Data/Task/LLM/API/Info/MCP）；
- 左侧公共面板：append_log 写日志面板、_display_result 写结果面板。

仅做实例化与面板读写冒烟，不触发任何 LLM 真实调用与任务执行。
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QTabWidget
from core.i18n import get_language_manager
from core.i18n.facade import PluginI18nFacade
from plugin.framework_api_demo.function.services import (
    APIDemoService,
    DataDemoService,
    FrameworkInfoService,
    LLMDemoService,
    MCPDemoService,
    TaskDemoService,
)
from plugin.framework_api_demo.ui.main_widget import MainWidget

#: framework_api_demo 插件目录（text/zh.xml 语言包所在）
_FAD_DIR = Path(__file__).resolve().parents[2] / "framework_api_demo"

#: 测试门面绑定的插件 id（注册语言包用，无业务含义）
_I18N_PLUGIN_ID = "pytest-fad-ui-smoke"

# 右侧 Tab 标题清单（与 main_widget._build_right_panel 的装配顺序一致，
# 取词门面注入后为 zh.xml 中文译文）
EXPECTED_TAB_TITLES = ["数据", "任务", "LLM", "API", "信息", "MCP"]


@pytest.fixture(scope="session")
def i18n_facade() -> PluginI18nFacade:
    """注册 framework_api_demo 语言包并返回取词门面（中文）。

    门面缺失时 UI 文案降级为键名；注入真实门面使标题断言面向
    实际中文译文而非键名。
    """
    manager = get_language_manager()
    manager.register_plugin_texts(_I18N_PLUGIN_ID, _FAD_DIR)
    manager.set_language("zh")
    return PluginI18nFacade(_I18N_PLUGIN_ID)


@pytest.fixture()
def main_widget(qtbot, qapp, plugin_id, registered_provider, i18n_facade):
    """装配完整 MainWidget（六个真实演示服务，数据落盘到 tmp_path）"""
    widget = MainWidget(
        data_service=DataDemoService(plugin_id, data_provider=registered_provider),
        task_service=TaskDemoService(plugin_id, data_provider=registered_provider),
        llm_service=LLMDemoService(plugin_id, data_provider=registered_provider),
        api_service=APIDemoService(plugin_id, data_provider=registered_provider),
        info_service=FrameworkInfoService(plugin_id, data_provider=registered_provider),
        mcp_service=MCPDemoService(plugin_id, data_provider=registered_provider),
        i18n=i18n_facade,
        plugin_id=_I18N_PLUGIN_ID,
    )
    qtbot.addWidget(widget)
    return widget


class TestMainWidgetSmoke:
    """MainWidget 实例化与结构冒烟"""

    def test_instantiation(self, main_widget):
        """主控件应能实例化且 objectName 正确"""
        assert main_widget.objectName() == "FrameworkApiDemoWidget"

    def test_six_tabs_present(self, main_widget):
        """Tabs 容器应恰含 6 个 Tab 且标题顺序正确"""
        tab_widgets = main_widget.findChildren(QTabWidget)
        assert len(tab_widgets) == 1
        tabs = tab_widgets[0]
        assert tabs.count() == len(EXPECTED_TAB_TITLES)
        assert [tabs.tabText(i) for i in range(tabs.count())] == EXPECTED_TAB_TITLES

    def test_each_tab_has_content(self, main_widget):
        """每个 Tab 页都应有实际内容控件（滚动容器）"""
        tabs = main_widget.findChildren(QTabWidget)[0]
        for index in range(tabs.count()):
            assert tabs.widget(index) is not None


class TestPublicPanels:
    """左侧公共结果/日志面板"""

    def test_append_log_writes_to_log_panel(self, main_widget):
        """append_log 应把消息追加到日志面板"""
        main_widget.append_log("pytest 冒烟日志")
        assert "pytest 冒烟日志" in main_widget.log_text.toPlainText()

    def test_display_result_writes_to_result_panel(self, main_widget):
        """_display_result 应把标题与内容写入结果面板"""
        main_widget._display_result("冒烟标题", "冒烟内容")
        html = main_widget.result_display.toHtml()
        assert "冒烟标题" in html
        assert "冒烟内容" in html

    def test_display_result_escapes_html(self, main_widget):
        """结果内容中的 HTML 应被转义，防止注入"""
        main_widget._display_result("转义校验", "<script>alert(1)</script>")
        html = main_widget.result_display.toHtml()
        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html
