"""
本地 HTTP 服务器插件入口

仅作为胶水层，负责 UI 创建和信号连接，业务逻辑委托给 service.py。
"""

import time
import threading
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit,
    QGroupBox, QSpinBox,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject

from core.plugin import IPlugin
from .service import Service


class _StatusSignalHolder(QObject):
    status_changed = Signal(dict)


class LocalServerPlugin(IPlugin):
    """本地 HTTP 服务器插件"""

    @property
    def plugin_name(self) -> str:
        return "本地\n服务器"

    def __init__(self):
        super().__init__()
        self._service = None
        self._stop_event = threading.Event()
        self._port = None
        self._status_holder = _StatusSignalHolder()
        self.status_changed = self._status_holder.status_changed

    def on_plugin_loaded(self):
        if self.plugin_id:
            self._register_long_running_factory()

    def _register_long_running_factory(self):
        tm = self._services.task_manager
        if tm is None:
            return
        tm.register_long_running_task_factory(
            plugin_id=self.plugin_id,
            func=self._create_server_func(),
            stop_callback=self._create_stop_callback(),
            status_callback=self._create_status_callback(),
            restore_callback=self._on_task_restored
        )

    def _on_task_restored(self, task_id: str, task):
        self._service._server_task_id = task_id
        self._service._is_running = True
        self._service.save_data("server_task_id", task_id)
        self._service.set_running(True)
        if hasattr(self, 'start_btn'):
            self._restore_ui_state()

    def _create_server_func(self):
        from utils.logging_tools import LoggerManager, get_name
        logger = LoggerManager()

        def server_func():
            try:
                self._service.start_http_server(
                    self._port, self._on_request
                )
                logger.info(get_name(),
                    f"Server started: http://127.0.0.1:{self._port}")
            except Exception as e:
                logger.error(get_name(), f"Server error: {e}")
            finally:
                self._cleanup_server(logger, get_name)
        return server_func

    def _cleanup_server(self, logger, get_name):
        self._service.stop_http_server()
        logger.info(get_name(), "Server stopped")

    def _create_stop_callback(self):
        def stop_callback():
            from utils.logging_tools import LoggerManager, get_name
            LoggerManager().info(get_name(), "Stopping server...")
            self._stop_event.set()
            self._service.stop_http_server()
        return stop_callback

    def _create_status_callback(self):
        from utils.logging_tools import LoggerManager, get_name
        logger = LoggerManager()

        def status_callback(task_id: str, status: str):
            logger.debug(get_name(), f"Server status: {status}")
            self.status_changed.emit({"status": status})
        return status_callback

    def _on_request(self):
        if self._service:
            self._service.increment_request_count()
            self.status_changed.emit({"action": "request"})

    def _load_plugin_style(self, widget: QWidget):
        from utils.style_qss.registry import QssRegistry
        style_dir = Path(__file__).parent / "style"
        if not style_dir.exists():
            return
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))
        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            widget.setStyleSheet(self._qss_content)

    def _set_status_class(self, status_class: str):
        self.status_label.setProperty("class", status_class)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def _init_data_provider(self, actual_plugin_id: str,
            data_provider=None) -> bool:
        from core.data.data_provider import DataProvider, DataProviderError
        try:
            dp = DataProvider()
            dp.register_plugin(actual_plugin_id, "LocalServer")
            dp.set_active_instance(actual_plugin_id)
        except DataProviderError:
            pass
        if data_provider:
            try:
                data_provider.register_plugin(actual_plugin_id, "LocalServer")
                data_provider.set_active_instance(actual_plugin_id)
                return True
            except DataProviderError:
                pass
        return False

    def _create_widget(self, parent=None, data_provider=None):
        from utils.logging_tools import LoggerManager, get_name
        logger = LoggerManager()

        if not self.plugin_id:
            self._plugin_id = "local-server-default"
        actual_plugin_id = self.plugin_id or "local-server-default"

        self._service = Service(actual_plugin_id, None)
        self._init_data_provider(actual_plugin_id, data_provider)

        widget = QWidget(parent)
        self._load_plugin_style(widget)
        widget.destroyed.connect(lambda qss=self._qss_content: widget.setStyleSheet(""))
        logger.info(get_name(),
            f"[LocalServer] _create_widget called, plugin_id={actual_plugin_id}")

        self._setup_main_layout(widget)
        return widget

    def _setup_main_layout(self, widget):
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = QWidget()
        self._build_all_groups(content)
        self.status_changed.connect(self._on_status_changed)
        layout = content.layout()
        layout.addStretch()
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)
        self._restore_ui_state()

    def _create_scroll_area(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        return scroll_area

    def _build_all_groups(self, content):
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        self._build_control_group(layout)
        self._build_status_group(layout)
        self._build_log_group(layout)

    def _build_control_group(self, layout):
        group = QGroupBox("服务器控制")
        group_layout = QVBoxLayout()
        self._build_port_row(group_layout)
        self._build_button_row(group_layout)
        group.setLayout(group_layout)
        layout.addWidget(group)

    def _build_port_row(self, group_layout):
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("端口:"))
        self.port_input = QSpinBox()
        min_p, max_p = self._service.get_port_range()
        def_port = self._service.get_default_port()
        self.port_input.setRange(min_p, max_p)
        self.port_input.setValue(def_port)
        self.port_input.setEnabled(False)
        port_layout.addWidget(self.port_input)
        port_layout.addStretch()
        group_layout.addLayout(port_layout)

    def _build_button_row(self, group_layout):
        btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("启动服务器")
        self.start_btn.clicked.connect(self._start_server)
        btn_layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("停止服务器")
        self.stop_btn.clicked.connect(self._stop_server)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        group_layout.addLayout(btn_layout)

    def _build_status_group(self, layout):
        group = QGroupBox("服务器状态")
        group_layout = QVBoxLayout()
        self.status_label = QLabel("状态: 未运行")
        self.status_label.setProperty("class", "status-info")
        group_layout.addWidget(self.status_label)
        self.request_count_label = QLabel("请求数: 0")
        group_layout.addWidget(self.request_count_label)
        self.url_label = QLabel("URL: -")
        group_layout.addWidget(self.url_label)
        group.setLayout(group_layout)
        layout.addWidget(group)

    def _build_log_group(self, layout):
        group = QGroupBox("请求日志")
        group_layout = QVBoxLayout()
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("log_edit")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMaximumHeight(150)
        group_layout.addWidget(self.log_edit)
        group.setLayout(group_layout)
        layout.addWidget(group)

    def _start_server(self):
        self._port = self.port_input.value()
        self._stop_event.clear()
        self._service.save_data("port", self._port)
        self._service.set_running(True)
        task_id = self._register_server_task()
        self._service._server_task_id = task_id
        self._service.save_data("server_task_id", task_id)
        self._update_ui_running()

    def _register_server_task(self) -> str:
        tm = self._services.task_manager
        task_id = tm.register_long_running_task(
            plugin_id=self.plugin_id,
            name="本地HTTP服务器",
            func=self._create_server_func(),
            stop_callback=self._create_stop_callback(),
            status_callback=self._create_status_callback(),
            auto_restart=False
        )
        return task_id

    def _update_ui_running(self):
        self.start_btn.setEnabled(False)
        self.port_input.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self._set_status_class("status-success")
        self.url_label.setText(f"URL: http://127.0.0.1:{self._port}")
        self._log(f"服务器已启动: http://127.0.0.1:{self._port}")

    def _stop_server(self):
        from utils.logging_tools import LoggerManager, get_name
        logger = LoggerManager()

        if self._service._server_task_id:
            tm = self._services.task_manager
            tm.stop_long_running_task(self._service._server_task_id)
            self._service._server_task_id = None
            self._service.save_data("server_task_id", None)

        self._service.set_running(False)
        self._update_ui_stopped()

    def _update_ui_stopped(self):
        self.start_btn.setEnabled(True)
        self.port_input.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("状态: 已停止")
        self._set_status_class("status-error")
        self.url_label.setText("URL: -")
        self._log("服务器已停止")

    def _on_status_changed(self, data):
        if "action" in data and data["action"] == "request":
            if self._service:
                count = self._service._request_count
                self.request_count_label.setText(f"请求数: {count}")
                self._log(f"收到请求 (总计: {count})")

    def _restore_ui_state(self):
        if not self._service:
            return
        if self._service._is_running:
            self._apply_running_ui_state()

    def _apply_running_ui_state(self):
        request_count = self._service._request_count
        self.start_btn.setEnabled(False)
        self.port_input.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("状态: 运行中")
        self._set_status_class("status-success")
        port = self._service.load_data("port",
            self._service.get_default_port())
        self.port_input.setValue(port)
        self.url_label.setText(f"URL: http://127.0.0.1:{port}")
        self.request_count_label.setText(f"请求数: {request_count}")
        self._log(f"服务器已恢复运行 (请求数: {request_count})")

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_edit.append(f"[{timestamp}] {message}")