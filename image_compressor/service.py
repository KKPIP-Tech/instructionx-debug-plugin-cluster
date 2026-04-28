"""Image Compressor Service - Interface Layer"""

from .function.services.core_service import CoreService

# 导出核心服务
Service = CoreService

__all__ = ['Service', 'CoreService']
