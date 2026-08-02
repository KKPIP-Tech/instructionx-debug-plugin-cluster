# -*- coding: utf-8 -*-
"""UI Demo 插件服务层（对框架的接口门面，仅委托 function/ 实现）。"""

from .function.services.core_service import CoreService


class Service(CoreService):
    """UI Demo 服务类（框架自动注册跨插件 API 的入口）。

    继承 ``CoreService`` 的全部公开方法；构造函数保持无参，
    兼容框架 Service 签名分析的全部 5 种实例化组合。
    """
