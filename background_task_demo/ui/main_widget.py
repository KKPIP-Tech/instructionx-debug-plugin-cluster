"""
后台任务演示器 UI

纯 UI 层，不包含业务逻辑。业务逻辑委托给 Service。
样式全面使用 InstructionX_UIKit 组件与 T() 令牌，随全局主题自动换肤。
"""

import time
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QListWidgetItem,
    QScrollArea, QVBoxLayout, QWidget,
)

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import (
    Button, CheckBox, ComboBox, LineEdit, ListWidget, Message,
    SpinBox, TextArea,
)

from core.task import TaskStatus


class MainWidget(QWidget):
    """后台任务演示器主界面"""

    def __init__(self, service, plugin_id: str, signal_bridge, parent=None):
        super().__init__(parent)
        self._service = service
        self._plugin_id = plugin_id
        self._signal_bridge = signal_bridge
        self._log_widget = None
        self._duration_range = (1, 30)
        self._interval_range = (5, 3600)
        self._setup_ui()
        self._refresh_task_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = self._create_scroll_area()
        layout.addWidget(scroll)

    def _create_scroll_area(self) -> QScrollArea:
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)

        content_layout.addWidget(self._create_header())
        content_layout.addWidget(self._create_task_group())
        content_layout.addWidget(self._create_list_group())
        content_layout.addWidget(self._create_log_group())
        content_layout.addStretch()

        scroll_area.setWidget(content)
        return scroll_area

    def _create_header(self) -> QWidget:
        """创建标题区（字号取 UIKit 令牌，替代旧 QSS heading/muted 选择器）"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(4)

        title = QLabel("BackgroundTask 模块演示")
        title_font = QFont()
        title_font.setPixelSize(T("font.lg"))
        title_font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(title_font)
        layout.addWidget(title)

        self.plugin_id_label = QLabel(f"插件 UUID: {self._plugin_id or '加载中...'}")
        muted_color = QColor(T("color.text.secondary"))
        palette = self.plugin_id_label.palette()
        palette.setColor(self.plugin_id_label.foregroundRole(), muted_color)
        self.plugin_id_label.setPalette(palette)
        layout.addWidget(self.plugin_id_label)
        return container

    def _create_task_group(self) -> QGroupBox:
        group = QGroupBox("创建任务")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        layout.addWidget(self._create_task_type_row())
        layout.addWidget(self._create_task_name_row())
        layout.addWidget(self._create_duration_row())
        layout.addWidget(self._create_interval_row())
        layout.addWidget(self._create_button_row())

        group.setLayout(layout)
        return group

    def _create_task_type_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.addWidget(QLabel("任务类型:"))
        self.task_type_combo = ComboBox(items=[
            "同步任务 (sync)",
            "异步任务 (async)",
            "定时任务 (scheduled)"
        ])
        self.task_type_combo.currentIndexChanged.connect(
            self._on_task_type_changed
        )
        row.addWidget(self.task_type_combo)
        row.addStretch()
        return container

    def _create_task_name_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.addWidget(QLabel("任务名称:"))
        self.task_name_input = LineEdit(
            text="测试任务", placeholder="输入任务名称")
        row.addWidget(self.task_name_input)
        return container

    def _create_duration_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.addWidget(QLabel("执行时长(秒):"))
        self.duration_spin = SpinBox(
            minimum=self._duration_range[0],
            maximum=self._duration_range[1],
            value=2
        )
        row.addWidget(self.duration_spin)
        return container

    def _create_interval_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.addWidget(QLabel("间隔(秒):"))
        self.interval_spin = SpinBox(
            minimum=self._interval_range[0],
            maximum=self._interval_range[1],
            value=10
        )
        self.interval_spin.setEnabled(False)
        row.addWidget(self.interval_spin)

        self.enable_scheduled_check = CheckBox("启用", checked=True)
        row.addWidget(self.enable_scheduled_check)
        row.addStretch()
        return container

    def _create_button_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        self.create_btn = Button("创建任务", variant="primary")
        self.create_btn.clicked.connect(self._create_task)
        row.addWidget(self.create_btn)

        self.cancel_btn = Button("取消选中任务")
        self.cancel_btn.clicked.connect(self._cancel_task)
        row.addWidget(self.cancel_btn)
        return container

    def _create_list_group(self) -> QGroupBox:
        group = QGroupBox("任务列表")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.task_list = ListWidget()
        layout.addWidget(self.task_list)
        layout.addWidget(self._create_filter_row())

        group.setLayout(layout)
        return group

    def _create_filter_row(self) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.addWidget(QLabel("筛选:"))
        row.addWidget(self._create_filter_combo())
        row.addWidget(self._create_refresh_button())
        row.addWidget(self._create_clear_button())
        return container

    def _create_filter_combo(self) -> ComboBox:
        self.filter_combo = ComboBox(items=[
            "全部", "pending", "running",
            "completed", "failed", "cancelled"
        ])
        self.filter_combo.currentTextChanged.connect(self._refresh_task_list)
        return self.filter_combo

    def _create_refresh_button(self) -> Button:
        btn = Button("刷新")
        btn.clicked.connect(self._refresh_task_list)
        return btn

    def _create_clear_button(self) -> Button:
        btn = Button("清理已完成")
        btn.clicked.connect(self._clear_completed)
        return btn

    def _create_log_group(self) -> QGroupBox:
        group = QGroupBox("执行日志")
        layout = QVBoxLayout()
        layout.setSpacing(12)

        self.log_text = TextArea()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont(MONO_FAMILY))
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)
        self._log_widget = self.log_text

        group.setLayout(layout)
        return group

    def _on_task_type_changed(self, index: int):
        self.interval_spin.setEnabled(index == 2)

    def _get_task_params(self) -> tuple:
        """获取任务参数"""
        name = self.task_name_input.text().strip()
        if not name:
            name = f"任务_{datetime.now().strftime('%H:%M:%S')}"
        return name, self.duration_spin.value()

    def _get_interval_params(self) -> tuple:
        """获取间隔参数"""
        return self.interval_spin.value(), self.enable_scheduled_check.isChecked()

    def _build_task_callback(self):
        """构建任务完成回调（供同步/异步/定时任务共用）"""
        def task_callback(task_id: str, status: TaskStatus,
                         result: str, error: Optional[str]):
            self._signal_bridge.task_completed.emit(
                task_id,
                status.value,
                str(result) if result else "",
                error if error else ""
            )
        return task_callback

    def _on_create_sync_task(self, task_name: str, duration: int):
        """创建同步任务"""
        self._log(f"[同步] 创建任务: {task_name}")
        task_func = self._make_demo_task_func(task_name, duration)
        callback = self._build_task_callback()

        task_id = self._service.register_sync_task(
            plugin_id=self._plugin_id,
            name=task_name,
            func=task_func,
            callback=callback,
            args=(task_name, duration)
        )
        self._log(f"[同步] 任务已创建，ID: {task_id}")

    def _on_create_async_task(self, task_name: str, duration: int):
        """创建异步任务"""
        self._log(f"[异步] 创建任务: {task_name}")
        task_func = self._make_demo_task_func(task_name, duration)
        callback = self._build_task_callback()

        task_id = self._service.register_async_task(
            plugin_id=self._plugin_id,
            name=task_name,
            func=task_func,
            callback=callback,
            args=(task_name, duration)
        )
        self._log(f"[异步] 任务已创建，ID: {task_id}")

    def _on_create_scheduled_task(self, task_name: str):
        """创建定时任务"""
        interval, enabled = self._get_interval_params()
        self._log(f"[定时] 创建任务: {task_name}, 间隔: {interval}秒")
        task_func = self._make_demo_task_func(task_name, 1)
        callback = self._build_task_callback()

        task_id = self._service.register_scheduled_task(
            plugin_id=self._plugin_id,
            name=task_name,
            func=task_func,
            interval=interval,
            callback=callback,
            args=(f"{task_name}_定时", 1)
        )

        if not enabled:
            self._service.disable_scheduled_task(task_id)
            self._log(f"[定时] 任务已创建但已禁用，ID: {task_id}")
        else:
            self._log(f"[定时] 任务已创建，ID: {task_id}")

    def _make_demo_task_func(self, name: str, seconds: int):
        """构建演示用任务函数"""
        def task_func(n: str, s: int):
            self._log(f"任务 '{n}' 开始执行，耗时 {s} 秒...")
            time.sleep(s)
            result = f"任务 '{n}' 完成！执行时间: {s}秒"
            self._log(f"任务 '{n}' 执行完成")
            return result
        return task_func

    def _create_task(self):
        if not self._plugin_id:
            Message.warning(self, "插件未初始化")
            return

        task_type = self.task_type_combo.currentIndex()
        task_name, duration = self._get_task_params()

        try:
            self._create_task_by_type(task_type, task_name, duration)
            self._refresh_task_list()
        except Exception as e:
            Message.warning(self, f"创建任务失败: {str(e)}")
            self._log(f"[错误] 创建任务失败: {str(e)}")

    def _create_task_by_type(self, task_type: int, task_name: str, duration: int):
        """按任务类型分发创建逻辑"""
        if task_type == 0:
            self._on_create_sync_task(task_name, duration)
        elif task_type == 1:
            self._on_create_async_task(task_name, duration)
        elif task_type == 2:
            self._on_create_scheduled_task(task_name)

    def _cancel_task(self):
        current_item = self.task_list.currentItem()
        if not current_item:
            Message.warning(self, "请先选择一个任务")
            return

        task_id = current_item.data(Qt.ItemDataRole.UserRole)
        if self._service.cancel_task(task_id):
            self._log(f"[取消] 任务 {task_id} 已取消")
            self._refresh_task_list()
        else:
            Message.warning(self, "无法取消该任务（可能已完成）")

    def _clear_completed(self):
        count = self._service.clear_completed_tasks(self._plugin_id)
        self._log(f"[清理] 已清理 {count} 个已完成任务")
        self._refresh_task_list()

    def _refresh_task_list(self):
        if not self._plugin_id:
            return

        all_tasks = self._service.get_tasks_by_plugin(self._plugin_id)
        scheduled_tasks = self._service.get_scheduled_tasks(self._plugin_id)
        filter_status = self.filter_combo.currentText()

        self.task_list.clear()
        self._add_background_tasks(all_tasks, filter_status)
        self._add_scheduled_tasks(scheduled_tasks)

    def _add_background_tasks(self, tasks, filter_status: str):
        for task in tasks:
            status_value = self._extract_task_status(task)
            if filter_status != "全部" and status_value != filter_status:
                continue
            item_text = self._build_task_item_text(task, status_value)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, task.get("task_id"))
            self.task_list.addItem(item)

    def _add_scheduled_tasks(self, tasks):
        for task in tasks:
            item_text = self._build_scheduled_item_text(task)
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, f"scheduled_{task.get('task_id')}")
            self.task_list.addItem(item)

    def _extract_task_status(self, task) -> str:
        status = task.get("status", {})
        if isinstance(status, dict):
            return status.get("value", "")
        return str(status)

    def _build_task_item_text(self, task, status_value: str) -> str:
        icon = self._get_status_icon(status_value)
        text = f"{icon} {task.get('name', '未知')} [{status_value}]"

        result = task.get("result")
        if result:
            result_str = str(result)
            if len(result_str) > 30:
                result_str = result_str[:30] + "..."
            text += f" - {result_str}"

        error = task.get("error")
        if error:
            text += f" [错误: {error}]"

        return text

    def _build_scheduled_item_text(self, task) -> str:
        enabled = task.get("enabled", True)
        status_str = "运行中" if enabled else "已禁用"
        next_run = task.get("next_run")
        next_run_str = next_run.strftime("%H:%M:%S") if next_run else "N/A"
        interval = task.get("interval", 0)
        name = task.get("name", "未知")
        return f"[定时] {name} [每{interval}秒] [{status_str}] 下次: {next_run_str}"

    def _get_status_icon(self, status: str) -> str:
        """任务状态对应的语义化 Unicode 图标"""
        icons = {
            "pending": "⏳",
            "running": "▶",
            "completed": "✅",
            "failed": "❌",
            "cancelled": "⏹"
        }
        return icons.get(status, "?")

    @Slot(str, str, str, str)
    def on_task_completed(self, task_id: str, status: str,
                          result: str, error: str):
        if error:
            self._log(f"[回调] 任务 {task_id} 失败: {error}")
        else:
            self._log(f"[回调] 任务 {task_id} 完成，结果: {result}")
        if self.task_list is not None:
            self._refresh_task_list()

    def log(self, message: str):
        """添加日志（公共接口，供外部调用）"""
        self._log(message)

    def _log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        if self._log_widget is not None:
            self._log_widget.append(f"[{timestamp}] {message}")
            self._log_widget.verticalScrollBar().setValue(
                self._log_widget.verticalScrollBar().maximum()
            )

    def flush_log_buffer(self, buffer: list):
        for msg in buffer:
            self._log(msg)
        buffer.clear()
