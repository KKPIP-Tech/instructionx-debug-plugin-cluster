# -*- coding: utf-8 -*-
"""后台任务演示 Tab。

演示同步/异步/定时/长期任务的创建、任务取消与状态查询、
定时任务启用/禁用/注销，以及任务回调经 run_in_ui_thread 上抛 UI。
槽函数仅取输入、调用 TaskDemoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QListWidgetItem, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, ComboBox, LineEdit, ListWidget, Message, SpinBox

from core.interfaces import ILocalizationFacade
from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab

#: 列表项类型标记（存于 item 的 UserRole+1），用于按类型分发操作按钮
_KIND_TASK = "task"
_KIND_SCHEDULED = "scheduled"
_KIND_LONG = "long"

#: 任务类型下拉框选项（内部标识符，与 _dispatch_create 分发键一致，不国际化）
_TASK_TYPES = ["sync", "async", "scheduled", "long_running"]


class TaskTab(BaseTab):
    """后台任务演示 Tab

    职责：构建任务演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, task_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化任务演示 Tab

        参数:
            task_service: TaskDemoService 实例（后台任务演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
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

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_task 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_task", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_task 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_task", key, slot, variant=variant)

    def _make_tab_label(self, key: str):
        """创建本 Tab 表单标签（取 tab_task 分组 label.* 键并登记绑定）"""
        return self._make_label("tab_task", key)

    def _build_task_create_group(self) -> QGroupBox:
        group = self._make_group("group.create")
        form = QFormLayout()
        form.setSpacing(6)
        self.task_name_input = LineEdit(text="demo_task")
        form.addRow(self._make_tab_label("label.name"), self.task_name_input)
        self.task_type_combo = ComboBox(items=list(_TASK_TYPES))
        form.addRow(self._make_tab_label("label.type"), self.task_type_combo)
        self.task_interval_spin = self._make_interval_spin()
        form.addRow(self._make_tab_label("label.interval"), self.task_interval_spin)
        self.create_task_btn = self._make_button(
            "btn.create", self._on_create_task, variant="primary")
        form.addRow("", self.create_task_btn)
        group.setLayout(form)
        return group

    def _make_interval_spin(self) -> SpinBox:
        """构建定时任务间隔 SpinBox（范围取服务层配置，后缀取词并登记绑定）"""
        interval_cfg = self.task_service.get_interval_config()
        spin = SpinBox(
            minimum=interval_cfg["minimum"],
            maximum=interval_cfg["maximum"],
            value=interval_cfg["default"],
        )
        spin.setSuffix(self._tr("tab_task", "suffix.seconds"))
        self._bind(spin, "tab_task", "suffix.seconds", setter="setSuffix")
        return spin

    def _build_task_query_group(self) -> QGroupBox:
        group = self._make_group("group.query")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        self.query_tasks_btn = self._make_button(
            "btn.query", self._on_query_tasks, variant="primary")
        layout.addWidget(self.query_tasks_btn)
        self.tasks_list = ListWidget()
        self.tasks_list.setMaximumHeight(100)
        layout.addWidget(self.tasks_list)
        for row in self._build_task_action_rows():
            layout.addLayout(row)
        self.clear_tasks_btn = self._make_button("btn.clear", self._on_clear_tasks)
        layout.addWidget(self.clear_tasks_btn)
        group.setLayout(layout)
        return group

    def _build_task_action_rows(self) -> list:
        """构建任务操作按钮行（拆为两行，适配收窄后的面板宽度，作用于列表选中项）"""
        manage_row = QHBoxLayout()
        manage_row.setSpacing(8)
        self.cancel_task_btn = self._make_button("btn.cancel", self._on_cancel_task)
        manage_row.addWidget(self.cancel_task_btn)
        self.stop_long_btn = self._make_button("btn.stop_long", self._on_stop_long_task)
        manage_row.addWidget(self.stop_long_btn)
        status_row = QHBoxLayout()
        self.status_btn = self._make_button("btn.status", self._on_query_status)
        status_row.addWidget(self.status_btn)
        status_row.addStretch()
        return [manage_row, status_row]

    def _build_scheduled_control_group(self) -> QGroupBox:
        group = self._make_group("group.scheduled")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        form = QFormLayout()
        form.setSpacing(6)
        self.scheduled_id_input = LineEdit(
            placeholder=self._tr("tab_task", "placeholder.scheduled_id"))
        self._bind(self.scheduled_id_input, "tab_task", "placeholder.scheduled_id",
                   setter="setPlaceholderText")
        form.addRow(self._make_tab_label("label.task_id"), self.scheduled_id_input)
        layout.addLayout(form)
        layout.addLayout(self._build_scheduled_button_row())
        group.setLayout(layout)
        return group

    def _build_scheduled_button_row(self) -> QHBoxLayout:
        """构建定时任务控制按钮行：启用 / 禁用 / 注销"""
        row = QHBoxLayout()
        row.setSpacing(8)
        self.enable_scheduled_btn = self._make_button("btn.enable", self._on_enable_scheduled)
        row.addWidget(self.enable_scheduled_btn)
        self.disable_scheduled_btn = self._make_button("btn.disable", self._on_disable_scheduled)
        row.addWidget(self.disable_scheduled_btn)
        self.unregister_scheduled_btn = self._make_button(
            "btn.unregister", self._on_unregister_scheduled)
        row.addWidget(self.unregister_scheduled_btn)
        return row

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_create_task(self):
        name = self.task_name_input.text()
        result = self._dispatch_create(name, self.task_type_combo.currentText())
        self._log(self._tr("tab_task", "log.create", result=result))
        self._show_op_result(self._tr("tab_task", "title.create"), result, log=False)

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
        self._log(self._tr("tab_task", "log.query", result=result))
        self._populate_tasks_list(result)
        if result.get("success"):
            self._display_result(self._tr("tab_task", "title.list"),
                                 self._format_task_lines(result))
        else:
            self._display_result(self._tr("tab_task", "title.query_fail"),
                                 result.get("error", ""), is_error=True)

    def _format_task_lines(self, result: dict) -> str:
        """格式化任务列表为展示文本"""
        lines = [self._format_task_item("item.task", name=t["name"], status=t["status"])
                 for t in result.get("tasks", [])]
        for t in result.get("scheduled_tasks", []):
            status = self._scheduled_status_text(t["enabled"])
            lines.append(self._format_task_item(
                "item.scheduled", name=t["name"], interval=t["interval"], status=status))
        for t in result.get("long_running_tasks", []):
            lines.append(self._format_task_item("item.long", name=t["name"],
                                                status=t["status"]))
        return "\n".join(lines) if lines else self._tr("tab_task", "empty.tasks")

    def _format_task_item(self, key: str, **params) -> str:
        """按当前语言格式化一行任务展示文本（行首 • 符号各语言一致）"""
        return f"• {self._tr('tab_task', key, **params)}"

    def _scheduled_status_text(self, enabled: bool) -> str:
        """定时任务启用状态文案（运行中/已禁用）"""
        key = "status.running" if enabled else "status.disabled"
        return self._tr("tab_task", key)

    def _on_clear_tasks(self):
        result = self.task_service.clear_completed()
        self._show_op_result(self._tr("tab_task", "title.clear"), result,
                             log_key="log.clear")
        self._on_query_tasks()

    def _on_cancel_task(self):
        task_id = self._selected_task_id()
        if not task_id:
            return
        kind = self._selected_task_kind()
        if kind == _KIND_SCHEDULED:
            # 定时任务不归 cancel_task 管（仅覆盖运行中的普通任务），
            # 「取消」语义对应从调度中注销
            self._show_op_result(self._tr("tab_task", "title.unregister_scheduled"),
                                 self.task_service.unregister_scheduled(task_id))
            self._on_query_tasks()
            return
        if kind == _KIND_LONG:
            Message.warning(self._message_parent,
                            self._tr("tab_task", "warn.long_use_stop"))
            return
        self._show_op_result(self._tr("tab_task", "title.cancel"),
                             self.task_service.cancel_task_demo(task_id))

    def _on_stop_long_task(self):
        task_id = self._selected_task_id()
        if task_id:
            self._show_op_result(self._tr("tab_task", "title.stop_long"),
                                 self.task_service.stop_long_task(task_id))
            self._on_query_tasks()

    def _on_query_status(self):
        task_id = self._selected_task_id()
        if task_id:
            self._show_op_result(self._tr("tab_task", "title.status"),
                                 self.task_service.get_task_status_demo(task_id))

    def _on_enable_scheduled(self):
        self._set_scheduled_enabled(True)

    def _on_disable_scheduled(self):
        self._set_scheduled_enabled(False)

    def _on_unregister_scheduled(self):
        task_id = self._scheduled_target_id()
        if task_id:
            self._show_op_result(self._tr("tab_task", "title.unregister_scheduled"),
                                 self.task_service.unregister_scheduled(task_id))
            self._on_query_tasks()

    def _set_scheduled_enabled(self, enabled: bool):
        """启用/禁用定时任务公共处理"""
        task_id = self._scheduled_target_id()
        if not task_id:
            return
        title_key = "title.enable" if enabled else "title.disable"
        result = self.task_service.set_scheduled_enabled(task_id, enabled)
        self._show_op_result(self._tr("tab_task", title_key), result)
        self._on_query_tasks()

    # ------------------------------------------------------------------
    #  辅助方法
    # ------------------------------------------------------------------

    def _populate_tasks_list(self, result: dict):
        """填充任务列表，task_id 与类型标记存入 item 数据"""
        self.tasks_list.clear()
        for task in result.get("tasks", []):
            text = self._tr("tab_task", "item.task",
                            name=task["name"], status=task["status"])
            self._add_task_item(text, task["task_id"], _KIND_TASK)
        for task in result.get("scheduled_tasks", []):
            status = self._scheduled_status_text(task["enabled"])
            text = self._tr("tab_task", "item.scheduled", name=task["name"],
                            interval=task["interval"], status=status)
            self._add_task_item(text, task["task_id"], _KIND_SCHEDULED)
        for task in result.get("long_running_tasks", []):
            text = self._tr("tab_task", "item.long",
                            name=task["name"], status=task["status"])
            self._add_task_item(text, task["task_id"], _KIND_LONG)

    def _add_task_item(self, text: str, task_id: str, kind: str):
        """向列表添加一行，并把 task_id 与类型标记绑定到 item 数据"""
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, task_id)
        item.setData(Qt.ItemDataRole.UserRole + 1, kind)
        self.tasks_list.addItem(item)

    def _selected_task_id(self) -> Optional[str]:
        """取当前列表选中项的 task_id；无选中时弹提示"""
        item = self.tasks_list.currentItem()
        if item is not None:
            return item.data(Qt.ItemDataRole.UserRole)
        Message.warning(self._message_parent, self._tr("tab_task", "warn.select_task"))
        return None

    def _selected_task_kind(self) -> Optional[str]:
        """取当前列表选中项的类型标记（task/scheduled/long）"""
        item = self.tasks_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole + 1)

    def _scheduled_target_id(self) -> Optional[str]:
        """取定时任务控制目标 ID：输入框优先，留空时回退列表选中项"""
        task_id = self.scheduled_id_input.text().strip()
        if task_id:
            return task_id
        return self._selected_task_id()

    def _show_op_result(self, title: str, result: dict, log: bool = True,
                        log_key: Optional[str] = None):
        """统一展示操作结果（成功/失败标题模板取词）

        参数:
            title: 已取词的操作标题
            result: 服务返回结果字典
            log: 是否写执行日志（默认标题: 结果 格式）
            log_key: 自定义日志模板键（tab_task 分组 log.*）；优先于默认格式
        """
        if log_key is not None:
            self._log(self._tr("tab_task", log_key, result=result))
        elif log:
            self._log(f"{title}: {result}")
        if result.get("success"):
            content = result.get("message", "") or str(result)
            self._display_result(self._tr("common", "result.success", title=title), content)
        else:
            self._display_result(self._tr("common", "result.fail", title=title),
                                 result.get("error", ""), is_error=True)
