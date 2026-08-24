# -*- coding: utf-8 -*-
"""UI Demo 插件元数据（InstructionX_UIKit 组件橱窗）。"""

from typing import Any, Dict, Optional

from core.interfaces import IPluginInfo
from core.plugin.plugin_icon import PluginIcon
from core.plugin.plugin_version import PluginVersion


class UiDemoPluginInfo(IPluginInfo):
    """UI Demo 插件元数据：组件橱窗定位与对外 service_api 描述。"""

    @property
    def version(self) -> PluginVersion:
        return PluginVersion.from_string("release.1.0.4")

    @property
    def developer(self) -> str:
        return "InstructionX"

    @property
    def developer_email(self) -> str:
        return "support@example.com"

    @property
    def developer_website(self) -> str:
        return "https://github.com/InstructionX"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def description(self) -> str:
        return """
        InstructionX_UIKit 组件橱窗：以导航树分页演示设计令牌、
        12 个布局预设、57 个组件、属性/自绘动画、原生图表与蓝图节点图，
        每页附最小用法示例，是插件开发的 UI 参考。
        """

    @property
    def service_api(self) -> Dict[str, Any]:
        return {
            "get_control_list": {
                "description": "获取全部可演示的 UIKit 组件/页面清单（分类 · 名称）",
                "parameters": {},
                "returns": {
                    "type": "list",
                    "description": "组件清单（字符串列表，按导航树顺序）",
                },
            }
        }

    @property
    def skill_icon(self) -> PluginIcon:
        return PluginIcon.builtin("SP_DesktopIcon")

    @property
    def skill_description(self) -> str:
        return "UIKit 组件橱窗"

    @property
    def tags(self) -> Optional[list[str]]:
        return ["ui", "demo", "uikit", "components"]

    @property
    def dependencies(self) -> Dict[str, str]:
        return {}

    @property
    def plugin_type_id(self) -> str:
        """插件类型标识符"""
        return "ui-demo"
