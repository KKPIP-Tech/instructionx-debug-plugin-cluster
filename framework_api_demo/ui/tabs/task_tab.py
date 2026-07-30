# -*- coding: utf-8 -*-
"""后台任务演示 Tab。

演示同步/异步/定时/长期任务的创建、任务取消与状态查询、
定时任务启用/禁用/注销，以及任务回调经 run_in_ui_thread 上抛 UI。
槽函数仅取输入、调用 TaskDemoService、显示结果，业务逻辑在服务层。
"""

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QListWidgetItem, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, ComboBox, LineEdit, ListWidget, Message, SpinBox

from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab


class TaskTab(BaseTab):
    """后台任务演示 Tab

    职责：构建任务演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, task_service, display_result: Callable, append_log: Callable):
        """初始化任务演示 Tab

        参数:
            task_service: TaskDemoService 实例（后台任务演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
        self.task_service = task_service
        # 任务回调在工作线程触发，经 run_in_ui_thread 封送到 UI 线程写日志
        self.task_service.set_event_notifier(self._on_task_event_notify)

    def _on_task_event_notify(self, message: str):
        """任务事件通知（工作线程）：封送到 UI 线程追加日志"""
        run_in_ui_thread(self._append_log, message)

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 Task Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_task_create_group())
        layout.addWidget(self._build_task_query_group())
        layout.addWidget(self._build_scheduled_control_group())
        layout.addStretch()
        return scroll

    def _build_task_create_group(self) -> QGroupBox:
        group = QGroupBox("创建任务")
        form = QFormLayout()
        form.setSpacing(6)

        self.task_name_input = LineEdit(text="demo_task")
        form.addRow("名称:", self.task_name_input)

        self.task_type_combo = ComboBox(items=["sync", "async", "scheduled", "long_running"])
        form.addRow("类型:", self.task_type_combo)

        self.task_interval_spin = SpinBox(minimum=5, maximum=3600, value=60)
        self.task_interval_spin.setSuffix(" 秒")
        form.addRow("间隔:", self.task_interval_spin)

        self.create_task_btn = Button("创建任务", variant="primary")
        self.create_task_btn.clicked.connect(self._on_create_task)
        form.addRow("", self.create_task_btn)

        group.setLayout(form)
        return group

    def _build_task_query_group(self) -> QGroupBox:
        group = QGroupBox("任务查询")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.query_tasks_btn = Button("查询所有任务", variant="primary")
        self.query_tasks_btn.clicked.connect(self._on_query_tasks)
        layout.addWidget(self.query_tasks_btn)

        self.tasks_list = ListWidget()
        self.tasks_list.setMaximumHeight(100)
        layout.addWidget(self.tasks_list)

        layout.addLayout(self._build_task_action_row())

        self.clear_tasks_btn = Button("清理已完成任务")
        self.clear_tasks_btn.clicked.connect(self._on_clear_tasks)
        layout.addWidget(self.clear_tasks_btn)

        group.setLayout(layout)
        return group

    def _build_task_action_row(self) -> QHBoxLayout:
        """构建任务操作按钮行（取消/停止长期/查询状态，作用于列表选中项）"""
        row = QHBoxLayout()
        row.setSpacing(8)

        self.cancel_task_btn = Button("取消任务")
        self.cancel_task_btn.clicked.connect(self._on_cancel_task)
        row.addWidget(self.cancel_task_btn)

        self.stop_long_btn = Button("停止长期任务")
        self.stop_long_btn.clicked.connect(self._on_stop_long_task)
        row.addWidget(self.stop_long_btn)

        self.status_btn = Button("查询状态")
        self.status_btn.clicked.connect(self._on_query_status)
        row.addWidget(self.status_btn)

        return row

    def _build_scheduled_control_group(self) -> QGroupBox:
        group = QGroupBox("定时任务控制")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        form = QFormLayout()
        form.setSpacing(6)
        self.scheduled_id_input = LineEdit(placeholder="定时任务 task_id（留空则取列表选中项）")
        form.addRow("任务 ID:", self.scheduled_id_input)
        layout.addLayout(form)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.enable_scheduled_btn = Button("启用")
        self.enable_scheduled_btn.clicked.connect(self._on_enable_scheduled)
        row.addWidget(self.enable_scheduled_btn)

        self.disable_scheduled_btn = Button("禁用")
        self.disable_scheduled_btn.clicked.connect(self._on_disable_scheduled)
        row.addWidget(self.disable_scheduled_btn)

        self.unregister_scheduled_btn = Button("注销")
        self.unregister_scheduled_btn.clicked.connect(self._on_unregister_scheduled)
        row.addWidget(self.unregister_scheduled_btn)
        layout.addLayout(row)

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_create_task(self):
        name = self.task_name_input.text()
        result = self._dispatch_create(name, self.task_type_combo.currentText())
        self._log(f"创建任务: {result}")
        if result.get("success"):
            self._display_result("创建任务成功", result.get("message", ""))
        else:
            self._display_result("创建任务失败", result.get("error", ""), is_error=True)

    def _dispatch_create(self, name: str, task_type: str) -> dict:
        """按任务类型分发创建请求"""
        if task_type == "sync":
            return self.task_service.create_sync_task(name)
        if task_type == "async":
            return self.task_service.create_async_task(name)
        if task_type == "long_running":
            return self.task_service.create_long_running_task(name)
        return self.task_service.create_scheduled_task(name, self.task_interval_spin.value())

    def _on_query_tasks(self):
        result = self.task_service.query_tasks()
        self._log(f"查询任务: {result}")
        self._populate_tasks_list(result)
        if result.get("success"):
            self._display_result("任务列表", self._format_task_lines(result))
        else:
            self._display_result("查询任务失败", result.get("error", ""), is_error=True)

    def _format_task_lines(self, result: dict) -> str:
        """格式化任务列表为展示文本"""
        lines = [f"• {t['name']} [{t['status']}]" for t in result.get("tasks", [])]
        for t in result.get("scheduled_tasks", []):
            status = "运行中" if t["enabled"] else "已禁用"
            lines.append(f"• [定时] {t['name']} ({t['interval']}s) [{status}]")
        for t in result.get("long_running_tasks", []):
            lines.append(f"• [长期] {t['name']} [{t['status']}]")
        return "\n".join(lines) if lines else "暂无任务"

    def _on_clear_tasks(self):
        result = self.task_service.clear_completed()
        self._log(f"清理任务: {result}")
        if result.get("success"):
            self._display_result("清理任务成功", result.get("message", ""))
        else:
            self._display_result("清理任务失败", result.get("error", ""), is_error=True)
        self._on_query_tasks()

    def _on_cancel_task(self):
        task_id = self._selected_task_id()
        if task_id:
            self._show_op_result("取消任务", self.task_service.cancel_task_demo(task_id))

    def _on_stop_long_task(self):
        task_id = self._selected_task_id()
        if task_id:
            self._show_op_result("停止长期任务", self.task_service.stop_long_task(task_id))
            self._on_query_tasks()

    def _on_query_status(self):
        task_id = self._selected_task_id()
        if task_id:
            self._show_op_result("查询状态", self.task_service.get_task_status_demo(task_id))

    def _on_enable_scheduled(self):
        self._set_scheduled_enabled(True)

    def _on_disable_scheduled(self):
        self._set_scheduled_enabled(False)

    def _on_unregister_scheduled(self):
        task_id = self._scheduled_target_id()
        if task_id:
            self._show_op_result("注销定时任务", self.task_service.unregister_scheduled(task_id))
            self._on_query_tasks()

    def _set_scheduled_enabled(self, enabled: bool):
        """启用/禁用定时任务公共处理"""
        task_id = self._scheduled_target_id()
        if not task_id:
            return
        action = "启用" if enabled else "禁用"
        result = self.task_service.set_scheduled_enabled(task_id, enabled)
        self._show_op_result(f"{action}定时任务", result)
        self._on_query_tasks()

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------

    def _populate_tasks_list(self, result: dict):
        """填充任务列表，task_id 存入 item 的 UserRole 数据"""
        self.tasks_list.clear()
        for task in result.get("tasks", []):
            self._add_task_item(f"{task['name']} [{task['status']}]", task["task_id"])
        for task in result.get("scheduled_tasks", []):
            status = "运行中" if task["enabled"] else "已禁用"
            text = f"[定时] {task['name']} ({task['interval']}s) [{status}]"
            self._add_task_item(text, task["task_id"])
        for task in result.get("long_running_tasks", []):
            text = f"[长期] {task['name']} [{task['status']}]"
            self._add_task_item(text, task["task_id"])

    def _add_task_item(self, text: str, task_id: str):
        """向列表添加一行，并把 task_id 绑定到 UserRole"""
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, task_id)
        self.tasks_list.addItem(item)

    def _selected_task_id(self) -> Optional[str]:
        """取当前列表选中项的 task_id；无选中时弹提示"""
        item = self.tasks_list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        Message.warning(self._message_parent, "请先在任务列表中选中一项")
        return None

    def _scheduled_target_id(self) -> Optional[str]:
        """取定时任务控制目标 ID：输入框优先，留空时回退列表选中项"""
        task_id = self.scheduled_id_input.text().strip()
        if task_id:
            return task_id
        return self._selected_task_id()

    def _show_op_result(self, title: str, result: dict):
        """统一展示操作结果（成功/失败）"""
        self._log(f"{title}: {result}")
        if result.get("success"):
            content = result.get("message", "") or str(result)
            self._display_result(f"{title}成功", content)
        else:
            self._display_result(f"{title}失败", result.get("error", ""), is_error=True)
