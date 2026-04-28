"""
Framework API Demo 插件入口

展示 InstructionX 框架提供的所有核心 API 接口的使用方法。
"""

import uuid
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QGroupBox,
    QLineEdit, QComboBox, QSpinBox, QListWidget,
    QMessageBox, QFormLayout,
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
        self._data_provider = DataProvider()
        self._signal_bridge = SignalBridge()
        self._log_widget = None

        # 初始化服务
        self.data_service: Optional[DataDemoService] = None
        self.task_service: Optional[TaskDemoService] = None
        self.llm_service: Optional[LLMDemoService] = None
        self.api_service: Optional[APIDemoService] = None
        self.info_service: Optional[FrameworkInfoService] = None

    @property
    def plugin_name(self) -> str:
        return "Framework\nAPI Demo"

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
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
        dp = data_provider if data_provider else DataProvider()
        plugin_id = self._ensure_plugin_id()
        self._setup_plugin(dp, plugin_id)

        widget = QWidget(parent)
        widget.setObjectName("FrameworkApiDemoWidget")
        self._load_plugin_style(widget)
        widget.destroyed.connect(lambda qss=self._qss_content: widget.setStyleSheet(""))

        self._build_widget_layout(widget)

        self._log_widget = self.log_text
        self._log("Framework API Demo 插件已加载")
        self._log(f"插件 ID: {plugin_id}")
        return widget

    def _setup_plugin(self, dp: DataProvider, plugin_id: str):
        """初始化插件服务和注册"""
        self._register_with_provider(dp, plugin_id)
        self._init_services(plugin_id, dp)
        self._signal_bridge.log_message.connect(self._on_log_message)

    def _build_widget_layout(self, widget: QWidget):
        """构建主控件布局"""
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_scroll_area())

    def _ensure_plugin_id(self) -> str:
        """确保 plugin_id 存在，必要时生成"""
        if not self.plugin_id:
            self._plugin_id = f"framework-api-demo-{uuid.uuid4().hex[:8]}"
        return self.plugin_id

    def _register_with_provider(self, dp: DataProvider, plugin_id: str):
        """向 DataProvider 注册插件"""
        try:
            dp.register_plugin(plugin_id, "FrameworkAPIDemo")
            dp.set_active_instance(plugin_id)
        except DataProviderError:
            pass

    def _init_services(self, plugin_id: str, dp: DataProvider):
        """初始化所有演示服务"""
        self.data_service = DataDemoService(plugin_id, dp)
        self.task_service = TaskDemoService(plugin_id, dp)
        self.llm_service = LLMDemoService(plugin_id, dp)
        self.api_service = APIDemoService(plugin_id, dp)
        self.info_service = FrameworkInfoService(plugin_id, dp)

    def _build_scroll_area(self) -> QScrollArea:
        """构建滚动区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        content_layout.addWidget(self._build_scroll_header())
        content_layout.addWidget(self._build_tab_widget())
        content_layout.addWidget(self._build_log_group())

        scroll_area.setWidget(content)
        return scroll_area

    def _build_scroll_header(self) -> QLabel:
        """构建标题和 UUID 显示"""
        title = QLabel("Framework API Demo")
        title.setProperty("heading", "true")

        self.plugin_id_label = QLabel(f"插件 UUID: {self.plugin_id}")
        self.plugin_id_label.setProperty("muted", "true")
        return self.plugin_id_label

    def _build_tab_widget(self) -> QTabWidget:
        """构建标签页控件"""
        tab_widget = QTabWidget()
        tab_widget.addTab(self._create_data_tab(), "DataProvider")
        tab_widget.addTab(self._create_task_tab(), "Task")
        tab_widget.addTab(self._create_llm_tab(), "LLM")
        tab_widget.addTab(self._create_api_tab(), "API")
        tab_widget.addTab(self._create_info_tab(), "Info")
        return tab_widget

    def _build_log_group(self) -> QGroupBox:
        """构建日志区域"""
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(12)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        return log_group

    # ===== DataProvider Tab =====

    def _create_data_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_data_register_controls())
        layout.addWidget(self._build_data_operation_group())
        layout.addWidget(self._build_data_assets_section())
        layout.addStretch()
        return widget

    def _build_data_register_controls(self) -> QGroupBox:
        group = QGroupBox("插件注册")
        row = QHBoxLayout()
        row.setSpacing(10)

        self.register_plugin_btn = QPushButton("注册演示插件")
        self.register_plugin_btn.setMinimumWidth(120)
        self.register_plugin_btn.clicked.connect(self._on_register_plugin)
        row.addWidget(self.register_plugin_btn)

        self.unregister_plugin_btn = QPushButton("注销演示插件")
        self.unregister_plugin_btn.setMinimumWidth(120)
        self.unregister_plugin_btn.clicked.connect(self._on_unregister_plugin)
        row.addWidget(self.unregister_plugin_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    def _build_data_operation_group(self) -> QGroupBox:
        group = QGroupBox("数据操作")
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addLayout(self._build_data_private_row())
        layout.addLayout(self._build_data_public_row())
        layout.addLayout(self._build_data_query_row())
        group.setLayout(layout)
        return group

    def _build_data_private_row(self) -> QHBoxLayout:
        """构建 Private 数据操作行"""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._build_data_row_label("Private 数据:"))
        row.addWidget(self._build_data_row_input("key", "test_key", "private_key_input"))
        row.addWidget(self._build_data_row_input("value", "test_value", "private_value_input"))
        row.addWidget(self._build_data_row_button("写入 Private", self._on_write_private))
        row.addWidget(self._build_data_row_button("读取 Private", self._on_read_private))
        row.addStretch()
        return row

    def _build_data_public_row(self) -> QHBoxLayout:
        """构建 Public 数据操作行"""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self._build_data_row_label("Public 数据:"))
        row.addWidget(self._build_data_row_input("key", "shared_key", "public_key_input"))
        row.addWidget(self._build_data_row_input("value", "shared_value", "public_value_input"))
        row.addWidget(self._build_data_row_button("写入 Public", self._on_write_public))
        row.addWidget(self._build_data_row_button("读取 Public", self._on_read_public))
        row.addStretch()
        return row

    def _build_data_row_label(self, text: str) -> QLabel:
        """构建数据操作行中的标签"""
        label = QLabel(text)
        label.setMinimumWidth(80)
        return label

    def _build_data_row_input(self, placeholder: str, default: str, attr_name: str) -> QLineEdit:
        """构建数据操作行中的输入框"""
        field = QLineEdit()
        field.setPlaceholderText(placeholder)
        field.setText(default)
        field.setMinimumWidth(100)
        setattr(self, attr_name, field)
        return field

    def _build_data_row_button(self, text: str, handler) -> QPushButton:
        """构建数据操作行中的按钮"""
        btn = QPushButton(text)
        btn.setMinimumWidth(90)
        btn.clicked.connect(handler)
        return btn

    def _build_data_query_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)

        label = QLabel("查询:")
        label.setMinimumWidth(80)
        row.addWidget(label)

        self.get_all_data_btn = QPushButton("获取所有数据")
        self.get_all_data_btn.setMinimumWidth(120)
        self.get_all_data_btn.clicked.connect(self._on_get_all_data)
        row.addWidget(self.get_all_data_btn)

        row.addStretch()
        return row

    def _build_data_assets_section(self) -> QGroupBox:
        group = QGroupBox("资源管理")
        row = QHBoxLayout()
        row.setSpacing(10)

        self.save_asset_btn = QPushButton("保存资源")
        self.save_asset_btn.setMinimumWidth(120)
        self.save_asset_btn.clicked.connect(self._on_save_asset)
        row.addWidget(self.save_asset_btn)

        self.load_asset_btn = QPushButton("加载资源")
        self.load_asset_btn.setMinimumWidth(120)
        self.load_asset_btn.clicked.connect(self._on_load_asset)
        row.addWidget(self.load_asset_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    # ===== Task Tab =====

    def _create_task_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_task_create_group())
        layout.addWidget(self._build_task_query_group())
        layout.addStretch()
        return widget

    def _build_task_create_group(self) -> QGroupBox:
        group = QGroupBox("创建任务")
        form = QFormLayout()
        form.addRow("任务名称:", self._build_task_name_field())
        form.addRow("任务类型:", self._build_task_type_field())
        form.addRow("间隔(定时任务):", self._build_task_interval_field())
        form.addRow("", self._build_create_task_btn())
        group.setLayout(form)
        return group

    def _build_task_name_field(self) -> QLineEdit:
        self.task_name_input = QLineEdit("demo_task")
        return self.task_name_input

    def _build_task_type_field(self) -> QComboBox:
        self.task_type_combo = QComboBox()
        self.task_type_combo.addItems(["sync", "async", "scheduled"])
        return self.task_type_combo

    def _build_task_interval_field(self) -> QSpinBox:
        self.task_interval_spin = QSpinBox()
        self.task_interval_spin.setRange(5, 3600)
        self.task_interval_spin.setValue(60)
        self.task_interval_spin.setSuffix(" 秒")
        return self.task_interval_spin

    def _build_create_task_btn(self) -> QPushButton:
        self.create_task_btn = QPushButton("创建任务")
        self.create_task_btn.clicked.connect(self._on_create_task)
        return self.create_task_btn

    def _build_task_query_group(self) -> QGroupBox:
        group = QGroupBox("任务查询")
        layout = QVBoxLayout()

        self.query_tasks_btn = QPushButton("查询所有任务")
        self.query_tasks_btn.clicked.connect(self._on_query_tasks)
        layout.addWidget(self.query_tasks_btn)

        self.tasks_list = QListWidget()
        self.tasks_list.setMaximumHeight(150)
        layout.addWidget(self.tasks_list)

        self.clear_tasks_btn = QPushButton("清理已完成任务")
        self.clear_tasks_btn.clicked.connect(self._on_clear_tasks)
        layout.addWidget(self.clear_tasks_btn)

        group.setLayout(layout)
        return group

    # ===== LLM Tab =====

    def _create_llm_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_llm_provider_group())
        layout.addWidget(self._build_llm_chat_group())
        layout.addWidget(self._build_llm_embed_group())
        layout.addStretch()
        return widget

    def _build_llm_provider_group(self) -> QGroupBox:
        group = QGroupBox("Provider 信息")
        layout = QVBoxLayout()

        self.get_providers_btn = QPushButton("获取 Provider 列表")
        self.get_providers_btn.clicked.connect(self._on_get_providers)
        layout.addWidget(self.get_providers_btn)

        self.providers_list = QListWidget()
        self.providers_list.setMaximumHeight(80)
        layout.addWidget(self.providers_list)

        self.get_models_btn = QPushButton("获取模型列表")
        self.get_models_btn.clicked.connect(self._on_get_models)
        layout.addWidget(self.get_models_btn)

        group.setLayout(layout)
        return group

    def _build_llm_chat_group(self) -> QGroupBox:
        group = QGroupBox("聊天测试")
        form = QFormLayout()

        self.chat_message_input = QLineEdit("你好，请介绍一下自己")
        form.addRow("消息:", self.chat_message_input)

        self.chat_btn = QPushButton("发送聊天")
        self.chat_btn.clicked.connect(self._on_send_chat)
        form.addRow("", self.chat_btn)

        self.chat_result_text = QTextEdit()
        self.chat_result_text.setReadOnly(True)
        self.chat_result_text.setMaximumHeight(100)
        form.addRow("结果:", self.chat_result_text)

        group.setLayout(form)
        return group

    def _build_llm_embed_group(self) -> QGroupBox:
        group = QGroupBox("嵌入测试")
        row = QHBoxLayout()

        self.embed_text_input = QLineEdit("Hello world")
        row.addWidget(self.embed_text_input)

        self.embed_btn = QPushButton("发送嵌入")
        self.embed_btn.clicked.connect(self._on_send_embed)
        row.addWidget(self.embed_btn)

        group.setLayout(row)
        return group

    # ===== API Tab =====

    def _create_api_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_api_plugin_group())
        layout.addWidget(self._build_api_query_group())
        layout.addWidget(self._build_api_function_group())
        layout.addWidget(self._build_api_call_group())
        layout.addStretch()
        return widget

    def _build_api_plugin_group(self) -> QGroupBox:
        group = QGroupBox("插件查询")
        layout = QVBoxLayout()

        self.get_all_plugins_btn = QPushButton("获取所有插件")
        self.get_all_plugins_btn.clicked.connect(self._on_get_all_plugins)
        layout.addWidget(self.get_all_plugins_btn)

        self.plugins_list = QListWidget()
        self.plugins_list.setMaximumHeight(120)
        layout.addWidget(self.plugins_list)

        group.setLayout(layout)
        return group

    def _build_api_query_group(self) -> QGroupBox:
        group = QGroupBox("API 查询")
        layout = QVBoxLayout()

        self.get_all_apis_btn = QPushButton("获取所有 API")
        self.get_all_apis_btn.clicked.connect(self._on_get_all_apis)
        layout.addWidget(self.get_all_apis_btn)

        self.apis_list = QListWidget()
        self.apis_list.setMaximumHeight(100)
        layout.addWidget(self.apis_list)

        group.setLayout(layout)
        return group

    def _build_api_function_group(self) -> QGroupBox:
        group = QGroupBox("Function Calling")
        layout = QVBoxLayout()

        self.get_function_tools_btn = QPushButton("获取所有 Function Tools")
        self.get_function_tools_btn.clicked.connect(self._on_get_function_tools)
        layout.addWidget(self.get_function_tools_btn)

        self.function_tools_list = QListWidget()
        self.function_tools_list.setMaximumHeight(100)
        layout.addWidget(self.function_tools_list)

        group.setLayout(layout)
        return group

    def _build_api_call_group(self) -> QGroupBox:
        group = QGroupBox("跨插件调用")
        form = QFormLayout()

        self.call_plugin_input = QLineEdit()
        self.call_plugin_input.setPlaceholderText("输入 plugin_id.method")
        form.addRow("调用:", self.call_plugin_input)

        self.call_method_btn = QPushButton("调用插件方法")
        self.call_method_btn.clicked.connect(self._on_call_plugin_method)
        form.addRow("", self.call_method_btn)

        self.call_result_text = QTextEdit()
        self.call_result_text.setReadOnly(True)
        self.call_result_text.setMaximumHeight(80)
        form.addRow("结果:", self.call_result_text)

        group.setLayout(form)
        return group

    # ===== Info Tab =====

    def _create_info_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self._build_info_group())
        layout.addWidget(self._build_info_doc_group())
        layout.addStretch()
        return widget

    def _build_info_group(self) -> QGroupBox:
        group = QGroupBox("框架信息")
        layout = QVBoxLayout()

        self.get_info_btn = QPushButton("获取框架信息")
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

    # ===== Logging =====

    def _log(self, message: str):
        """添加日志"""
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

    # ===== DataProvider Handlers =====

    def _on_register_plugin(self):
        result = self.data_service.register_demo_plugin()
        self._log(f"注册插件: {result}")
        QMessageBox.information(None, "结果", str(result))

    def _on_unregister_plugin(self):
        result = self.data_service.unregister_demo_plugin()
        self._log(f"注销插件: {result}")
        QMessageBox.information(None, "结果", str(result))

    def _on_write_private(self):
        key = self.private_key_input.text()
        value = self.private_value_input.text()
        result = self.data_service.write_private_data(key, value)
        self._log(f"写入Private: {result}")

    def _on_read_private(self):
        key = self.private_key_input.text()
        result = self.data_service.read_private_data(key)
        self._log(f"读取Private: {result}")

    def _on_write_public(self):
        key = self.public_key_input.text()
        value = self.public_value_input.text()
        result = self.data_service.write_public_data(key, value)
        self._log(f"写入Public: {result}")

    def _on_read_public(self):
        key = self.public_key_input.text()
        result = self.data_service.read_public_data(key)
        self._log(f"读取Public: {result}")

    def _on_get_all_data(self):
        result = self.data_service.get_all_data()
        self._log(f"获取所有数据: {result}")

    def _on_save_asset(self):
        result = self.data_service.save_demo_asset()
        self._log(f"保存资源: {result}")

    def _on_load_asset(self):
        save_result = self.data_service.save_demo_asset()
        if save_result.get("success"):
            load_result = self.data_service.load_demo_asset(save_result.get("path"))
            self._log(f"加载资源: {load_result}")
        else:
            self._log(f"保存资源失败: {save_result}")

    # ===== Task Handlers =====

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

    def _on_query_tasks(self):
        result = self.task_service.query_tasks()
        self._log(f"查询任务: {result}")
        self._populate_tasks_list(result)

    def _on_clear_tasks(self):
        result = self.task_service.clear_completed()
        self._log(f"清理任务: {result}")
        self._on_query_tasks()

    # ===== LLM Handlers =====

    def _on_get_providers(self):
        result = self.llm_service.get_providers()
        self._log(f"获取Provider: {result}")

        self.providers_list.clear()
        for p in result.get("providers", []):
            self.providers_list.addItem(p)

    def _on_get_models(self):
        result = self.llm_service.get_models()
        self._log(f"获取模型: {result}")

    def _on_send_chat(self):
        message = self.chat_message_input.text()
        result = self.llm_service.send_chat(message)
        self._log(f"聊天结果: {result}")

        if result.get("success"):
            self.chat_result_text.setPlainText(result.get("response", ""))
        else:
            self.chat_result_text.setPlainText(
                f"错误: {result.get('error')}"
            )

    def _on_send_embed(self):
        text = self.embed_text_input.text()
        result = self.llm_service.send_embedding(text)
        self._log(f"嵌入结果: {result}")
        QMessageBox.information(None, "嵌入结果", str(result))

    # ===== API Handlers =====

    def _on_get_all_plugins(self):
        result = self.api_service.get_all_plugins()
        self._log(f"获取插件: {result}")

        self.plugins_list.clear()
        for plugin in result.get("plugins", []):
            self.plugins_list.addItem(
                f"{plugin['name']} ({plugin['id']})"
            )

    def _on_get_all_apis(self):
        result = self.api_service.get_all_apis()
        self._log(f"获取API: {result}")

        self.apis_list.clear()
        for pid, info in result.get("apis", {}).items():
            self.apis_list.addItem(
                f"{info['name']}: {', '.join(info['methods'])}"
            )

    def _on_get_function_tools(self):
        result = self.api_service.get_all_function_tools()
        self._log(f"获取Function Tools: {result}")

        self.function_tools_list.clear()
        self._populate_function_tools_list(result.get("tools", []))
        self._show_function_tools_json(result.get("tools", []))

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
            QMessageBox.warning(
                None, "输入错误", "请输入格式: plugin_id.method"
            )
            return

        parts = input_text.split(".", 1)
        plugin_id = parts[0]
        method_name = parts[1]

        result = self.api_service.call_plugin_method(plugin_id, method_name)
        self._log(f"调用结果: {result}")

        if result.get("success"):
            self.call_result_text.setPlainText(
                json.dumps(result.get("result"), indent=2, ensure_ascii=False)
            )
        else:
            self.call_result_text.setPlainText(
                f"错误: {result.get('error')}"
            )

    # ===== Info Handlers =====

    def _on_get_framework_info(self):
        result = self.info_service.get_framework_info()
        self.info_text.setPlainText(
            json.dumps(result, indent=2, ensure_ascii=False)
        )
        self._log(f"框架信息: {result}")
