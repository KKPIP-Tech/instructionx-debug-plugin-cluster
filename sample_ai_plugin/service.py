"""
示例 AI 插件服务接口层

作为 plugin/ 根目录下的 service.py，提供对内部 Service 的统一访问。
"""

from .function.services.core_service import CoreService

__all__ = ["CoreService"]