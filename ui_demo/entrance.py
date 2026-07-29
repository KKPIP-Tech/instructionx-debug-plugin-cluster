# -*- coding: utf-8 -*-
"""UI Demo 插件入口（胶水层）：协调框架与插件 UI/服务。"""

from core.plugin.plugin_interface import IPlugin

from .ui.main_widget import MainWidget


class UiDemoPlugin(IPlugin):
    """InstructionX_UIKit 组件橱窗插件。

    以导航树分页演示 UIKit 的设计令牌、12 个布局、57 个组件、
    动画、图表与蓝图节点图，页面移植自 UIKit 仓库 Demo。
    """

    @property
    def plugin_name(self) -> str:
        return "UI\nDemo"

    def _create_widget(self, parent=None, data_provider=None) -> MainWidget:
        """创建插件主控件（导航树 + 演示页堆叠）。"""
        return MainWidget(parent=parent)
