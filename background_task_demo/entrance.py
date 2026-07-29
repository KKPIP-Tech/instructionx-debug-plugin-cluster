"""
后台任务演示器插件

用于演示 BackgroundTask 模块的所有功能：
1. 同步任务注册与执行
2. 异步任务注册与执行
3. 任务回调机制
4. 按插件 UUID 检索任务
5. 定时任务注册与管理
6. 任务状态查询
"""

import time
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QVBoxLayout, QWidget

from core.plugin.plugin_interface import IPlugin
from core.task import TaskStatus
from utils.logging_tools import LoggerManager, get_name

from .service import Service
from .ui.main_widget import MainWidget


class SignalBridge(QObject):
    """Qt 信号桥接器，用于线程安全的 UI 更新"""
    task_completed = Signal(str, str, str, str)
    task_updated = Signal()


_log_buffer = []


def _buffer_log(message: str):
    """缓冲区日志（供定时任务回调使用）"""
    _log_buffer.append(message)


class BackgroundTaskDemoPlugin(IPlugin):
    """后台任务演示器插件"""

    _logger = LoggerManager()

    def __init__(self):
        super().__init__()
        self._service = Service()
        self._signal_bridge = SignalBridge()
        self._main_widget = None

    def on_plugin_loaded(self) -> None:
        """插件加载完成回调"""
        if self.plugin_id:
            self._register_task_factory(self.plugin_id)

    def _register_task_factory(self, plugin_id: str):
        """注册定时任务工厂"""
        task_func = self._make_factory_task_func()
        task_callback = self._make_factory_task_callback()
        self._service.register_scheduled_task_factory(plugin_id, task_func, task_callback)

    def _make_factory_task_func(self):
        """构建定时任务工厂的演示任务函数"""
        def task_func(name: str, seconds: int):
            _buffer_log(f"任务 '{name}' 开始执行，耗时 {seconds} 秒...")
            time.sleep(seconds)
            result = f"任务 '{name}' 完成！执行时间: {seconds}秒"
            _buffer_log(f"任务 '{name}' 执行完成")
            return result
        return task_func

    def _make_factory_task_callback(self):
        """构建定时任务工厂的回调函数"""
        def task_callback(task_id: str, status: TaskStatus,
                         result: str, error: Optional[str]):
            try:
                self._signal_bridge.task_completed.emit(
                    task_id,
                    status.value,
                    str(result) if result else "",
                    error if error else ""
                )
            except Exception as e:
                self._logger.error(
                    get_name(), f"定时任务完成回调信号发送失败: {e}")
        return task_callback

    @property
    def plugin_name(self) -> str:
        return "后台任务演示"

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        widget = QWidget(parent)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._main_widget = self._create_main_widget(widget)
        main_layout.addWidget(self._main_widget)
        self._connect_signals()
        self._restore_ui_state()

        return widget

    def _create_main_widget(self, parent) -> MainWidget:
        """创建主控件"""
        return MainWidget(
            self._service,
            self.plugin_id,
            self._signal_bridge,
            parent=parent
        )

    def _connect_signals(self):
        """连接信号"""
        self._signal_bridge.task_completed.connect(
            self._main_widget.on_task_completed
        )
        self._signal_bridge.task_updated.connect(
            self._main_widget._refresh_task_list
        )

    def _restore_ui_state(self):
        """恢复 UI 状态（刷新日志缓冲区和任务列表）"""
        self._main_widget.flush_log_buffer(_log_buffer)
        self._main_widget._refresh_task_list()
