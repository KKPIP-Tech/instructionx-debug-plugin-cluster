"""
Task Manager Service - Interface Layer
仅对外暴露 API，所有业务逻辑委托至 function/services/core_service.py
"""

from .function.services.core_service import TaskService

__all__ = ["TaskService"]
