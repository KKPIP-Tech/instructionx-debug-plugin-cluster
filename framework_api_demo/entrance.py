"""
Framework API Demo 插件入口

展示 InstructionX 框架提供的所有核心 API 接口的使用方法。
采用左右分栏布局：左侧显示操作结果，右侧放置操作控件。
"""

import uuid
import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QListWidget,
    QMessageBox, QFormLayout, QGridLayout,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal, QObject, Slot

from utils.style_qss.registry import QssRegistry

from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError
from utils.logging_tools import LoggerManager, get_name

from .function.services.core_service import (
    DataDemoService, TaskDemoService, LLMDemoService,
    APIDemoService, FrameworkInfoService
)


class SignalBridge(QObject):
    """Qt 信号桥接器，用于线程安全的 UI 更新"""
    log_message = Signal(str)


class FrameworkAPIDemoPlugin(IPlugin):
    """Framework API Demo 插件"""

    _logger = LoggerManager()

    def __init__(self):
        super().__init__()
        self._signal_bridge = SignalBridge()
        self._log_widget = None

        # 服务实例（在 on_plugin_loaded 中初始化）
        self.data_service: Optional[DataDemoService] = None
        self.task_service: Optional[TaskDemoService] = None
        self.llm_service: Optional[LLMDemoService] = None
        self.api_service: Optional[APIDemoService] = None
        self.info_service: Optional[FrameworkInfoService] = None

    @property
    def plugin_name(self) -> str:
        return "Framework\nAPI Demo"

    def on_plugin_loaded(self, plugin_id=None, **kwargs):
        """插件加载完成后初始化服务和注册（仅执行一次）"""
        dp = self._get_data_provider()
        self._register_with_provider(dp)
        self._init_services(dp)
        self._signal_bridge.log_message.connect(self._on_log_message)

    def _get_data_provider(self) -> DataProvider:
        """获取 DataProvider 实例（优先使用框架注入的）"""
        services = getattr(self, '_services', None)
        if services and hasattr(services, 'data_provider'):
            return services.data_provider
        return DataProvider()

    def _register_with_provider(self, dp: DataProvider):
        """向 DataProvider 注册插件并设置活跃实例"""
        plugin_id = self.plugin_id
        try:
            dp.register_plugin(plugin_id, "FrameworkAPIDemo")
        except DataProviderError as e:
            err = str(e)
            if "已存在" not in err and "exists" not in err.lower():
                self._log(f"注册插件失败: {err}")
                return
        try:
            dp.set_active_instance(plugin_id)
        except DataProviderError as e:
            self._log(f"设置活跃实例失败: {e}")

    def _init_services(self, dp: DataProvider):
        """初始化所有演示服务"""
        pid = self.plugin_id
        self.data_service = DataDemoService(pid, dp)
        self.task_service = TaskDemoService(pid, dp)
        self.llm_service = LLMDemoService(pid, dp)
        self.api_service = APIDemoService(pid, dp)
        self.info_service = FrameworkInfoService(pid, dp)

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            old_widget = self._cached_widget
            self._cached_widget = None
            self._cached_parent = None
            if old_widget is not None:
                old_widget.deleteLater()
        return super().get_widget(parent, data_provider)

    def _load_plugin_style(self, widget: QWidget):
        """加载插件目录下的 style/*.qss，支持 {variable} 变量替换"""
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

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        widget = QWidget(parent)
        widget.setObjectName("FrameworkApiDemoWidget")
        self._load_plugin_style(widget)

        def _on_destroyed(obj):
            try:
                obj.setStyleSheet("")
            except RuntimeError:
                pass
        widget.destroyed.connect(_on_destroyed)

        self._build_widget_layout(widget)
        self._log_widget = self.log_text
        self._log("Framework API Demo 插件已加载")
        self._log(f"插件 ID: {self.plugin_id}")
        return widget

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def _build_widget_layout(self, widget: QWidget):
        """构建主控件左右分栏布局"""
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_left_panel(), stretch=2)
        layout.addWidget(self._build_right_panel(), stretch=1)

    def _build_left_panel(self) -> QWidget:
        """构建左侧输出面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 操作结果
        result_group = QGroupBox("操作结果")
        result_layout = QVBoxLayout()
        result_layout.setSpacing(4)

        self.result_display = QTextEdit()
        self.result_display.setObjectName("resultDisplay")
        self.result_display.setReadOnly(True)
        result_layout.addWidget(self.result_display)

        clear_btn = QPushButton("清除结果")
        clear_btn.setProperty("class", "subtle")
        clear_btn.clicked.connect(lambda: self.result_display.clear())
        result_layout.addWidget(clear_btn)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group, stretch=3)

        # 执行日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(4)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(160)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)

        return panel

    def _build_right_panel(self) -> QWidget:
        """构建右侧操作面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_data_tab(), "DataProvider")
        tab_widget.addTab(self._create_task_tab(), "Task")
        tab_widget.addTab(self._create_llm_tab(), "LLM")
        tab_widget.addTab(self._create_api_tab(), "API")
        tab_widget.addTab(self._create_info_tab(), "Info")

        layout.addWidget(tab_widget)
        return panel

    def _make_scroll_tab(self) -> tuple[QScrollArea, QVBoxLayout]:
        """创建带滚动区域的 Tab 内容容器"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll.setWidget(widget)
        return scroll, layout

    # ===== DataProvider Tab =====

    def _create_data_tab(self) -> QScrollArea:
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_data_register_controls())
        layout.addWidget(self._build_data_private_group())
        layout.addWidget(self._build_data_public_group())
        layout.addWidget(self._build_data_query_controls())
        layout.addWidget(self._build_data_assets_section())
        layout.addStretch()
        return scroll

    def _build_data_register_controls(self) -> QGroupBox:
        group = QGroupBox("插件注册")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.register_plugin_btn = QPushButton("注册演示插件")
        self.register_plugin_btn.setProperty("class", "primary")
        self.register_plugin_btn.clicked.connect(self._on_register_plugin)
        row.addWidget(self.register_plugin_btn)

        self.unregister_plugin_btn = QPushButton("注销演示插件")
        self.unregister_plugin_btn.clicked.connect(self._on_unregister_plugin)
        row.addWidget(self.unregister_plugin_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    def _build_data_private_group(self) -> QGroupBox:
        group = QGroupBox("Private 数据操作")
        form = QFormLayout()
        form.setSpacing(6)

        self.private_key_input = QLineEdit("test_key")
        self.private_key_input.setPlaceholderText("key")
        form.addRow("键:", self.private_key_input)

        self.private_value_input = QLineEdit("test_value")
        self.private_value_input.setPlaceholderText("value")
        form.addRow("值:", self.private_value_input)

        row = QHBoxLayout()
        btn_write = QPushButton("写入")
        btn_write.setProperty("class", "primary")
        btn_write.clicked.connect(self._on_write_private)
        row.addWidget(btn_write)

        btn_read = QPushButton("读取")
        btn_read.clicked.connect(self._on_read_private)
        row.addWidget(btn_read)
        form.addRow("", row)

        group.setLayout(form)
        return group

    def _build_data_public_group(self) -> QGroupBox:
        group = QGroupBox("Public 数据操作")
        form = QFormLayout()
        form.setSpacing(6)

        self.public_key_input = QLineEdit("shared_key")
        self.public_key_input.setPlaceholderText("key")
        form.addRow("键:", self.public_key_input)

        self.public_value_input = QLineEdit("shared_value")
        self.public_value_input.setPlaceholderText("value")
        form.addRow("值:", self.public_value_input)

        row = QHBoxLayout()
        btn_write = QPushButton("写入")
        btn_write.setProperty("class", "primary")
        btn_write.clicked.connect(self._on_write_public)
        row.addWidget(btn_write)

        btn_read = QPushButton("读取")
        btn_read.clicked.connect(self._on_read_public)
        row.addWidget(btn_read)
        form.addRow("", row)

        group.setLayout(form)
        return group

    def _build_data_query_controls(self) -> QGroupBox:
        group = QGroupBox("数据查询")
        layout = QVBoxLayout()

        self.get_all_data_btn = QPushButton("获取所有数据")
        self.get_all_data_btn.setProperty("class", "primary")
        self.get_all_data_btn.clicked.connect(self._on_get_all_data)
        layout.addWidget(self.get_all_data_btn)

        group.setLayout(layout)
        return group

    def _build_data_assets_section(self) -> QGroupBox:
        group = QGroupBox("资源管理")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.save_asset_btn = QPushButton("保存资源")
        self.save_asset_btn.setProperty("class", "primary")
        self.save_asset_btn.clicked.connect(self._on_save_asset)
        row.addWidget(self.save_asset_btn)

        self.load_asset_btn = QPushButton("加载资源")
        self.load_asset_btn.clicked.connect(self._on_load_asset)
        row.addWidget(self.load_asset_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    # ===== Task Tab =====

    def _create_task_tab(self) -> QScrollArea:
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_task_create_group())
        layout.addWidget(self._build_task_query_group())
        layout.addStretch()
        return scroll

    def _build_task_create_group(self) -> QGroupBox:
        group = QGroupBox("创建任务")
        form = QFormLayout()
        form.setSpacing(6)

        self.task_name_input = QLineEdit("demo_task")
        form.addRow("名称:", self.task_name_input)

        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(["sync", "async", "scheduled"])
        form.addRow("类型:", self.task_type_combo)

        self.task_interval_spin = QSpinBox()
        self.task_interval_spin.setRange(5, 3600)
        self.task_interval_spin.setValue(60)
        self.task_interval_spin.setSuffix(" 秒")
        form.addRow("间隔:", self.task_interval_spin)

        self.create_task_btn = QPushButton("创建任务")
        self.create_task_btn.setProperty("class", "primary")
        self.create_task_btn.clicked.connect(self._on_create_task)
        form.addRow("", self.create_task_btn)

        group.setLayout(form)
        return group

    def _build_task_query_group(self) -> QGroupBox:
        group = QGroupBox("任务查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.query_tasks_btn = QPushButton("查询所有任务")
        self.query_tasks_btn.setProperty("class", "primary")
        self.query_tasks_btn.clicked.connect(self._on_query_tasks)
        layout.addWidget(self.query_tasks_btn)

        self.tasks_list = QListWidget()
        self.tasks_list.setMaximumHeight(100)
        layout.addWidget(self.tasks_list)

        self.clear_tasks_btn = QPushButton("清理已完成任务")
        self.clear_tasks_btn.clicked.connect(self._on_clear_tasks)
        layout.addWidget(self.clear_tasks_btn)

        group.setLayout(layout)
        return group

    # ===== LLM Tab =====

    def _create_llm_tab(self) -> QScrollArea:
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_llm_provider_group())
        layout.addWidget(self._build_llm_chat_group())
        layout.addWidget(self._build_llm_embed_group())
        layout.addStretch()
        return scroll

    def _build_llm_provider_group(self) -> QGroupBox:
        group = QGroupBox("Provider 信息")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_providers_btn = QPushButton("获取 Provider 列表")
        self.get_providers_btn.setProperty("class", "primary")
        self.get_providers_btn.clicked.connect(self._on_get_providers)
        layout.addWidget(self.get_providers_btn)

        self.providers_list = QListWidget()
        self.providers_list.setMaximumHeight(80)
        layout.addWidget(self.providers_list)

        self.get_models_btn = QPushButton("获取模型列表")
        self.get_models_btn.setProperty("class", "primary")
        self.get_models_btn.clicked.connect(self._on_get_models)
        layout.addWidget(self.get_models_btn)

        self.models_list = QListWidget()
        self.models_list.setMaximumHeight(80)
        layout.addWidget(self.models_list)

        group.setLayout(layout)
        return group

    def _build_llm_chat_group(self) -> QGroupBox:
        group = QGroupBox("聊天测试")
        form = QFormLayout()
        form.setSpacing(6)

        self.chat_message_input = QLineEdit("你好，请介绍一下自己")
        form.addRow("消息:", self.chat_message_input)

        self.chat_btn = QPushButton("发送聊天")
        self.chat_btn.setProperty("class", "primary")
        self.chat_btn.clicked.connect(self._on_send_chat)
        form.addRow("", self.chat_btn)

        self.chat_result_text = QTextEdit()
        self.chat_result_text.setReadOnly(True)
        self.chat_result_text.setMaximumHeight(80)
        form.addRow("结果:", self.chat_result_text)

        group.setLayout(form)
        return group

    def _build_llm_embed_group(self) -> QGroupBox:
        group = QGroupBox("嵌入测试")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.embed_text_input = QLineEdit("Hello world")
        row.addWidget(self.embed_text_input)

        self.embed_btn = QPushButton("发送嵌入")
        self.embed_btn.setProperty("class", "primary")
        self.embed_btn.clicked.connect(self._on_send_embed)
        row.addWidget(self.embed_btn)

        group.setLayout(row)
        return group

    # ===== API Tab =====

    def _create_api_tab(self) -> QScrollArea:
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_api_plugin_group())
        layout.addWidget(self._build_api_query_group())
        layout.addWidget(self._build_api_function_group())
        layout.addWidget(self._build_api_call_group())
        layout.addStretch()
        return scroll

    def _build_api_plugin_group(self) -> QGroupBox:
        group = QGroupBox("插件查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_all_plugins_btn = QPushButton("获取所有插件")
        self.get_all_plugins_btn.setProperty("class", "primary")
        self.get_all_plugins_btn.clicked.connect(self._on_get_all_plugins)
        layout.addWidget(self.get_all_plugins_btn)

        self.plugins_list = QListWidget()
        self.plugins_list.setMaximumHeight(80)
        layout.addWidget(self.plugins_list)

        group.setLayout(layout)
        return group

    def _build_api_query_group(self) -> QGroupBox:
        group = QGroupBox("API 查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_all_apis_btn = QPushButton("获取所有 API")
        self.get_all_apis_btn.setProperty("class", "primary")
        self.get_all_apis_btn.clicked.connect(self._on_get_all_apis)
        layout.addWidget(self.get_all_apis_btn)

        self.apis_list = QListWidget()
        self.apis_list.setMaximumHeight(80)
        layout.addWidget(self.apis_list)

        group.setLayout(layout)
        return group

    def _build_api_function_group(self) -> QGroupBox:
        group = QGroupBox("Function Calling")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_function_tools_btn = QPushButton("获取所有 Function Tools")
        self.get_function_tools_btn.setProperty("class", "primary")
        self.get_function_tools_btn.clicked.connect(self._on_get_function_tools)
        layout.addWidget(self.get_function_tools_btn)

        self.function_tools_list = QListWidget()
        self.function_tools_list.setMaximumHeight(80)
        layout.addWidget(self.function_tools_list)

        group.setLayout(layout)
        return group

    def _build_api_call_group(self) -> QGroupBox:
        group = QGroupBox("跨插件调用")
        form = QFormLayout()
        form.setSpacing(6)

        self.call_plugin_input = QLineEdit()
        self.call_plugin_input.setPlaceholderText("输入 plugin_id.method")
        form.addRow("调用:", self.call_plugin_input)

        self.call_method_btn = QPushButton("调用插件方法")
        self.call_method_btn.setProperty("class", "primary")
        self.call_method_btn.clicked.connect(self._on_call_plugin_method)
        form.addRow("", self.call_method_btn)

        self.call_result_text = QTextEdit()
        self.call_result_text.setReadOnly(True)
        self.call_result_text.setMaximumHeight(60)
        form.addRow("结果:", self.call_result_text)

        group.setLayout(form)
        return group

    # ===== Info Tab =====

    def _create_info_tab(self) -> QScrollArea:
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_info_group())
        layout.addWidget(self._build_info_doc_group())
        layout.addStretch()
        return scroll

    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("框架信息")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.get_info_btn = QPushButton("获取框架信息")
        self.get_info_btn.setProperty("class", "primary")
        self.get_info_btn.clicked.connect(self._on_get_framework_info)
        layout.addWidget(self.get_info_btn)

        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        layout.addWidget(self.info_text)

        group.setLayout(layout)
        return group

    def _build_info_doc_group(self) -> QGroupBox:
        doc_text = QTextEdit()
        doc_text.setReadOnly(True)
        doc_text.setPlainText(self._get_api_doc_text())

        group = QGroupBox("可用接口文档")
        layout = QVBoxLayout()
        layout.addWidget(doc_text)
        group.setLayout(layout)
        return group

    def _get_api_doc_text(self) -> str:
        """获取 API 文档文本"""
        return """Framework API Demo 演示以下接口:

1. DataProvider
   - register_plugin() / unregister_plugin()
   - get_plugin_data() / set_plugin_data()
   - save_asset() / load_asset()

2. BackgroundTaskManager
   - register_sync_task() / register_async_task()
   - register_scheduled_task()
   - get_tasks_by_plugin() / clear_completed_tasks()

3. LLMProvider
   - get_all_providers() / get_cached_models()
   - chat() / stream_chat()
   - embed()

4. PluginManager
   - get_all_plugins() / get_plugin_by_id()
   - get_all_apis() / call_plugin_method()
   - get_all_function_tools() (Function Calling)
   - get_api_description()

5. LoggerManager
   - debug() / info() / warning() / error() / critical()
"""

    # ------------------------------------------------------------------
    #  结果展示与日志
    # ------------------------------------------------------------------

    def _display_result(self, title: str, content: str, is_error: bool = False):
        """在左侧操作结果面板中显示彩色卡片式结果"""
        if not hasattr(self, 'result_display') or self.result_display is None:
            return
        timestamp = datetime.now().strftime('%H:%M:%S')
        if is_error:
            border_color = "#EF4444"
            title_color = "#EF4444"
            content_color = "#EF4444"
        else:
            border_color = "#10B981"
            title_color = "#10B981"
            content_color = "inherit"

        safe_content = escape(str(content))
        html = (
            f'<div style="margin: 8px 0; border-left: 3px solid {border_color}; '
            f'padding-left: 10px;">'
            f'<div style="color: {title_color}; font-weight: bold; font-size: 13px; '
            f'margin-bottom: 4px;">[{timestamp}] {escape(title)}</div>'
            f'<pre style="margin: 0; font-family: Consolas, monospace; font-size: 12px; '
            f'color: {content_color}; white-space: pre-wrap; word-wrap: break-word;">'
            f'{safe_content}</pre>'
            f'</div>'
        )
        self.result_display.append(html)
        scrollbar = self.result_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _log(self, message: str):
        """添加日志到下方日志面板"""
        if hasattr(self, "log_text") and self.log_text:
            self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        else:
            self._signal_bridge.log_message.emit(message)

    @Slot(str)
    def _on_log_message(self, message: str):
        if hasattr(self, "log_text") and self.log_text:
            self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    # ------------------------------------------------------------------
    #  DataProvider Handlers
    # ------------------------------------------------------------------

    def _on_register_plugin(self):
        result = self.data_service.register_demo_plugin()
        self._log(f"注册插件: {result}")
        if result.get("success"):
            self._display_result("注册插件成功", result.get("message", ""))
        else:
            self._display_result("注册插件失败", result.get("error", ""), is_error=True)
        QMessageBox.information(None, "结果", str(result))

    def _on_unregister_plugin(self):
        result = self.data_service.unregister_demo_plugin()
        self._log(f"注销插件: {result}")
        if result.get("success"):
            self._display_result("注销插件成功", result.get("message", ""))
        else:
            self._display_result("注销插件失败", result.get("error", ""), is_error=True)
        QMessageBox.information(None, "结果", str(result))

    def _on_write_private(self):
        key = self.private_key_input.text()
        value = self.private_value_input.text()
        result = self.data_service.write_private_data(key, value)
        self._log(f"写入Private: {result}")
        if result.get("success"):
            self._display_result("写入 Private 成功", f"{key} = {value}")
        else:
            self._display_result("写入 Private 失败", result.get("error", ""), is_error=True)

    def _on_read_private(self):
        key = self.private_key_input.text()
        result = self.data_service.read_private_data(key)
        self._log(f"读取Private: {result}")
        if result.get("success"):
            self._display_result("读取 Private 成功", f"{key} = {result.get('value')}")
        else:
            self._display_result("读取 Private 失败", result.get("error", ""), is_error=True)

    def _on_write_public(self):
        key = self.public_key_input.text()
        value = self.public_value_input.text()
        result = self.data_service.write_public_data(key, value)
        self._log(f"写入Public: {result}")
        if result.get("success"):
            self._display_result("写入 Public 成功", f"{key} = {value}")
        else:
            self._display_result("写入 Public 失败", result.get("error", ""), is_error=True)

    def _on_read_public(self):
        key = self.public_key_input.text()
        result = self.data_service.read_public_data(key)
        self._log(f"读取Public: {result}")
        if result.get("success"):
            self._display_result("读取 Public 成功", f"{key} = {result.get('value')}")
        else:
            self._display_result("读取 Public 失败", result.get("error", ""), is_error=True)

    def _on_get_all_data(self):
        result = self.data_service.get_all_data()
        self._log(f"获取所有数据: {result}")
        if result.get("success"):
            content = json.dumps(result, indent=2, ensure_ascii=False)
            self._display_result("所有数据", content)
        else:
            self._display_result("获取数据失败", result.get("error", ""), is_error=True)

    def _on_save_asset(self):
        result = self.data_service.save_demo_asset()
        self._log(f"保存资源: {result}")
        if result.get("success"):
            self._display_result("保存资源成功", f"路径: {result.get('path', '')}")
        else:
            self._display_result("保存资源失败", result.get("error", ""), is_error=True)

    def _on_load_asset(self):
        result = self.data_service.load_demo_asset()
        self._log(f"加载资源: {result}")
        if result.get("success"):
            self._display_result("加载资源成功", f"内容:\n{result.get('content', '')}")
        else:
            self._display_result("加载资源失败", result.get("error", ""), is_error=True)

    # ------------------------------------------------------------------
    #  Task Handlers
    # ------------------------------------------------------------------

    def _on_create_task(self):
        name = self.task_name_input.text()
        task_type = self.task_type_combo.currentText()

        if task_type == "sync":
            result = self.task_service.create_sync_task(name)
        elif task_type == "async":
            result = self.task_service.create_async_task(name)
        else:
            interval = self.task_interval_spin.value()
            result = self.task_service.create_scheduled_task(name, interval)

        self._log(f"创建任务: {result}")
        if result.get("success"):
            self._display_result("创建任务成功", result.get("message", ""))
        else:
            self._display_result("创建任务失败", result.get("error", ""), is_error=True)

    def _on_query_tasks(self):
        result = self.task_service.query_tasks()
        self._log(f"查询任务: {result}")
        self._populate_tasks_list(result)
        if result.get("success"):
            lines = []
            for t in result.get("tasks", []):
                lines.append(f"• {t['name']} [{t['status']}]")
            for t in result.get("scheduled_tasks", []):
                status = "运行中" if t["enabled"] else "已禁用"
                lines.append(f"• [定时] {t['name']} ({t['interval']}s) [{status}]")
            content = "\n".join(lines) if lines else "暂无任务"
            self._display_result("任务列表", content)
        else:
            self._display_result("查询任务失败", result.get("error", ""), is_error=True)

    def _on_clear_tasks(self):
        result = self.task_service.clear_completed()
        self._log(f"清理任务: {result}")
        if result.get("success"):
            self._display_result("清理任务成功", result.get("message", ""))
        else:
            self._display_result("清理任务失败", result.get("error", ""), is_error=True)
        self._on_query_tasks()

    # ------------------------------------------------------------------
    #  LLM Handlers
    # ------------------------------------------------------------------

    def _on_get_providers(self):
        result = self.llm_service.get_providers()
        self._log(f"获取Provider: {result}")

        self.providers_list.clear()
        if result.get("success"):
            for p in result.get("providers", []):
                self.providers_list.addItem(p)
            self._display_result("Provider 列表", "\n".join(result.get("providers", [])))
        else:
            self.providers_list.addItem(f"错误: {result.get('error')}")
            self._display_result("获取 Provider 失败", result.get("error", ""), is_error=True)

    def _on_get_models(self):
        result = self.llm_service.get_models()
        self._log(f"获取模型: {result}")

        self.models_list.clear()
        if result.get("success"):
            models = result.get("models", {})
            lines = []
            if isinstance(models, dict):
                for provider, model_list in models.items():
                    for m in model_list:
                        name = m.get("name", m.get("id", "unknown"))
                        lines.append(f"{provider}: {name}")
                        self.models_list.addItem(f"{provider}: {name}")
            else:
                for m in models:
                    name = m.get("name", m.get("id", "unknown"))
                    lines.append(name)
                    self.models_list.addItem(name)
            self._display_result("模型列表", "\n".join(lines))
        else:
            self.models_list.addItem(f"错误: {result.get('error')}")
            self._display_result("获取模型失败", result.get("error", ""), is_error=True)

    def _on_send_chat(self):
        message = self.chat_message_input.text()
        result = self.llm_service.send_chat(message)
        self._log(f"聊天结果: {result}")

        if result.get("success"):
            content = (
                f"模型: {result.get('model', 'unknown')}\n"
                f"Provider: {result.get('provider', 'unknown')}\n\n"
                f"{result.get('response', '')}"
            )
            self._display_result("聊天响应", content)
            self.chat_result_text.setPlainText(result.get("response", ""))
        else:
            self._display_result("聊天失败", result.get("error", ""), is_error=True)
            self.chat_result_text.setPlainText(f"错误: {result.get('error')}")

    def _on_send_embed(self):
        text = self.embed_text_input.text()
        result = self.llm_service.send_embedding(text)
        self._log(f"嵌入结果: {result}")
        if result.get("success"):
            self._display_result(
                "嵌入成功",
                f"维度: {result.get('embedding_size', 0)}\nProvider: {result.get('provider', 'unknown')}"
            )
        else:
            self._display_result("嵌入失败", result.get("error", ""), is_error=True)
        QMessageBox.information(None, "嵌入结果", str(result))

    # ------------------------------------------------------------------
    #  API Handlers
    # ------------------------------------------------------------------

    def _on_get_all_plugins(self):
        result = self.api_service.get_all_plugins()
        self._log(f"获取插件: {result}")

        self.plugins_list.clear()
        if result.get("success"):
            lines = []
            for plugin in result.get("plugins", []):
                self.plugins_list.addItem(f"{plugin['name']} ({plugin['id']})")
                lines.append(f"• {plugin['name']} ({plugin['id']})")
            self._display_result("插件列表", "\n".join(lines))
        else:
            self._display_result("获取插件失败", result.get("error", ""), is_error=True)

    def _on_get_all_apis(self):
        result = self.api_service.get_all_apis()
        self._log(f"获取API: {result}")

        self.apis_list.clear()
        if result.get("success"):
            lines = []
            for pid, info in result.get("apis", {}).items():
                self.apis_list.addItem(f"{info['name']}: {', '.join(info['methods'])}")
                lines.append(f"• {info['name']}: {', '.join(info['methods'])}")
            self._display_result("API 列表", "\n".join(lines))
        else:
            self._display_result("获取 API 失败", result.get("error", ""), is_error=True)

    def _on_get_function_tools(self):
        result = self.api_service.get_all_function_tools()
        self._log(f"获取Function Tools: {result}")

        self.function_tools_list.clear()
        self._populate_function_tools_list(result.get("tools", []))
        self._show_function_tools_json(result.get("tools", []))

        if result.get("success"):
            lines = []
            for tool in result.get("tools", []):
                func = tool.get("function", {})
                name = func.get("name", "unknown")
                lines.append(f"• {name}")
            self._display_result("Function Tools", "\n".join(lines) if lines else "暂无工具")
        else:
            self._display_result("获取 Function Tools 失败", result.get("error", ""), is_error=True)

    def _populate_function_tools_list(self, tools: list):
        """填充 Function Tools 列表"""
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")[:50]
            self.function_tools_list.addItem(f"{name}: {desc}...")

    def _show_function_tools_json(self, tools: list):
        """显示 Function Tools JSON 信息"""
        raw_json = json.dumps(tools, indent=2, ensure_ascii=False)[:2000]
        QMessageBox.information(None, "Function Tools", raw_json)

    def _populate_tasks_list(self, result: dict):
        """填充任务列表"""
        self.tasks_list.clear()
        for task in result.get("tasks", []):
            self.tasks_list.addItem(f"{task['name']} [{task['status']}]")
        for task in result.get("scheduled_tasks", []):
            status = "运行中" if task["enabled"] else "已禁用"
            self.tasks_list.addItem(
                f"[定时] {task['name']} ({task['interval']}s) [{status}]"
            )

    def _on_call_plugin_method(self):
        input_text = self.call_plugin_input.text()
        if not input_text or "." not in input_text:
            self._display_result("输入错误", "请输入格式: plugin_id.method", is_error=True)
            QMessageBox.warning(None, "输入错误", "请输入格式: plugin_id.method")
            return

        parts = input_text.split(".", 1)
        plugin_id = parts[0]
        method_name = parts[1]

        result = self.api_service.call_plugin_method(plugin_id, method_name)
        self._log(f"调用结果: {result}")

        if result.get("success"):
            content = json.dumps(result.get("result"), indent=2, ensure_ascii=False)
            self._display_result("跨插件调用成功", content)
            self.call_result_text.setPlainText(content)
        else:
            self._display_result("跨插件调用失败", result.get("error", ""), is_error=True)
            self.call_result_text.setPlainText(f"错误: {result.get('error')}")

    # ------------------------------------------------------------------
    #  Info Handlers
    # ------------------------------------------------------------------

    def _on_get_framework_info(self):
        result = self.info_service.get_framework_info()
        self._log(f"框架信息: {result}")
        if result:
            content = json.dumps(result, indent=2, ensure_ascii=False)
            self._display_result("框架信息", content)
            self.info_text.setPlainText(content)
        else:
            self._display_result("获取框架信息失败", "无返回数据", is_error=True)
