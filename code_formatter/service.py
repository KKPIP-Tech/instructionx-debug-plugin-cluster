"""
代码格式化服务接口层

作为 PluginManager API 自动注册的入口，
实际业务逻辑委托给 CoreService。
"""

from .function.services.core_service import CoreService as Service
