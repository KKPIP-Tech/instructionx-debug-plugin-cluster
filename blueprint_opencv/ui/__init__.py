# -*- coding: utf-8 -*-
"""Blueprint OpenCV 插件 ui 包。

对外契约：``MainWidget(service, parent=None)``（见 main_widget.py）。
导入本包即触发节点类型幂等注册（node_bootstrap 经 main_widget 模块级调用）。
"""

from .main_widget import MainWidget

__all__ = ["MainWidget"]
