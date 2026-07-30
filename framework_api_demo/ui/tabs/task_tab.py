# -*- coding: utf-8 -*-
"""后台任务演示 Tab。

演示同步/异步/定时任务的创建、任务查询与已完成任务清理。
槽函数仅取输入、调用 TaskDemoService、显示结果，业务逻辑在服务层。
"""

from typing import Callable

from PySide6.QtWidgets import QFormLayout, QGroupBox, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, ComboBox, LineEdit, ListWidget, SpinBox

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

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 Task Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_task_create_group())
        layout.addWidget(self._build_task_query_group())
        layout.addStretch()
        return scroll

    def _build_task_create_group(self) -> QGroupBox:
        group = QGroupBox("创建任务")
        form = QFormLayout()
        form.setSpacing(6)

        self.task_name_input = LineEdit(text="demo_task")
        form.addRow("名称:", self.task_name_input)

        self.task_type_combo = ComboBox(items=["sync", "async", "scheduled"])
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

        self.clear_tasks_btn = Button("清理已完成任务")
        self.clear_tasks_btn.clicked.connect(self._on_clear_tasks)
        layout.addWidget(self.clear_tasks_btn)

        group.setLayout(layout)
        return group

    # ------------------------------------------------------------------
    #  事件处理
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
