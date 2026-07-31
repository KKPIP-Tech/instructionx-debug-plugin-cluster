# -*- coding: utf-8 -*-
"""framework_api_demo 测试套件共享 fixture。

- ``tmp_data_provider``：指向 tmp_path 的隔离 DataProvider，
  全程不触碰框架真实 ``data/`` 目录，用例结束后关闭 SQLite 连接并复位单例；
- ``data_service`` / ``task_service`` / ``info_service``：
  注入隔离 DataProvider 与隔离 plugin_id 的演示服务实例；
- ``api_service_instance``：service.py 的 FrameworkApiDemoService 实例
  （service_api 三方法的被测入口）。
"""

import pytest

from core.data.data_provider import DataProvider

from plugin.framework_api_demo.function.services import (
    DataDemoService,
    FrameworkInfoService,
    TaskDemoService,
)
from plugin.framework_api_demo.service import FrameworkApiDemoService

# 测试用插件类型名（仅用于 DataProvider 注册，无业务含义）
PYTEST_PLUGIN_TYPE = "PytestDemo"


@pytest.fixture()
def tmp_data_provider(tmp_path):
    """隔离的 DataProvider 实例（数据落盘到 tmp_path，用例后复位单例）"""
    DataProvider._instance = None
    provider = DataProvider(data_dir=str(tmp_path))
    yield provider
    # 先关闭 SQLite 连接再让 tmp_path 清理，避免 Windows 下文件占用
    backend = getattr(provider, "_backend", None)
    if backend is not None:
        backend.close()
    DataProvider._instance = None


@pytest.fixture()
def registered_provider(plugin_id, tmp_data_provider):
    """已注册隔离 plugin_id 的 DataProvider（写读数据前必须注册）"""
    tmp_data_provider.register_plugin(plugin_id, PYTEST_PLUGIN_TYPE)
    return tmp_data_provider


@pytest.fixture()
def data_service(plugin_id, registered_provider):
    """注入隔离 DataProvider 的 DataDemoService，用例后执行卸载清理"""
    service = DataDemoService(plugin_id, data_provider=registered_provider)
    yield service
    service.cleanup()


@pytest.fixture()
def task_service(plugin_id, registered_provider):
    """注入隔离 DataProvider 的 TaskDemoService，用例后清理残留任务"""
    service = TaskDemoService(plugin_id, data_provider=registered_provider)
    yield service
    # cleanup 停止长期任务并注销定时任务，clear_completed 清理已完成记录
    service.cleanup()
    service.clear_completed()


@pytest.fixture()
def info_service(plugin_id, registered_provider):
    """注入隔离 DataProvider 的 FrameworkInfoService"""
    return FrameworkInfoService(plugin_id, data_provider=registered_provider)


@pytest.fixture()
def api_service_instance(plugin_id, registered_provider):
    """service.py 的 FrameworkApiDemoService（service_api 声明的实现实体）"""
    instance = FrameworkApiDemoService(
        plugin_id=plugin_id, data_provider=registered_provider,
    )
    yield instance
    # 若用例触发过任务创建，清理其在任务管理器中的残留
    if instance._task_service is not None:
        instance._task_service.cleanup()
        instance._task_service.clear_completed()
