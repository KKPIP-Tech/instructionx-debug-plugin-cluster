# -*- coding: utf-8 -*-
"""Blueprint OpenCV 插件 ui 包。

对外契约：``MainWidget(service, parent=None)``（见 main_widget.py）。
导入本包即触发节点类型幂等注册（node_bootstrap 经 main_widget 模块级调用）。
``NodeListPanel`` / ``GraphListPanel`` 按需 re-export（供测试 / 截图脚本断言）。
"""

from .graph_list_panel import GraphListPanel
from .main_widget import MainWidget
from .node_list_panel import NodeListPanel

__all__ = ["MainWidget", "NodeListPanel", "GraphListPanel"]
