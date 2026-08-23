# -*- coding: utf-8 -*-
"""UI Demo 插件入口（胶水层）：协调框架与插件 UI/服务。"""

from typing import Optional

from core.interfaces import PluginServices
from core.plugin.plugin_interface import IPlugin

from .ui.main_widget import MainWidget


class UiDemoPlugin(IPlugin):
    """InstructionX_UIKit 组件橱窗插件。

    以导航树分页演示 UIKit 的设计令牌、12 个布局、57 个组件、
    动画、图表与蓝图节点图，页面移植自 UIKit 仓库 Demo。
    """

    def __init__(self, services: Optional[PluginServices] = None):
        super().__init__()
        # 框架加载时经构造函数注入 PluginServices（见 PluginManager._instantiate_plugin）
        self._injected_services = services

    @property
    def plugin_name(self) -> str:
        return "UI\nDemo"

    def _get_services(self) -> Optional[PluginServices]:
        """获取 PluginServices：优先构造注入，其次框架注入的 _services 实例属性。"""
        if self._injected_services is not None:
            return self._injected_services
        return getattr(self, "_services", None)

    def _create_widget(self, parent=None, data_provider=None) -> MainWidget:
        """创建插件主控件（导航树 + 演示页堆叠），注入多语言取词门面。"""
        services = self._get_services()
        i18n = services.localization if services else None
        return MainWidget(parent=parent, i18n=i18n, plugin_id=self.plugin_id)
