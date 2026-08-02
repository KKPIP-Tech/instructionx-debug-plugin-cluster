# -*- coding: utf-8 -*-
"""UI Demo 核心业务服务：对外提供 UIKit 组件橱窗目录查询。"""

from ..component_catalog import COMPONENT_CATALOG


class CoreService:
    """UI Demo 核心服务。

    职责：以「分类 · 页面标题」字符串列表形式返回
    InstructionX_UIKit 组件橱窗的完整目录（数据来自
    ``function/component_catalog.py``，与 ui/pages/NAV 同步维护）。
    """

    def get_control_list(self) -> list:
        """获取全部可演示的 UIKit 组件/页面清单。

        Returns:
            list[str]: 形如「组件 · 输入 · Button 按钮」的条目列表，
            顺序与导航树一致。
        """
        items = []
        for category, pages in COMPONENT_CATALOG:
            for title in pages:
                items.append(f"{category} · {title}")
        return items
