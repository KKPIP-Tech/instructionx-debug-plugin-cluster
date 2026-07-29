# -*- coding: utf-8 -*-
"""任务管理器 UI（InstructionX_UIKit 版）。

仅负责界面构建与用户交互，业务逻辑全部委托给 TaskService。
样式使用 UIKit 组件（Button/ComboBox/ListWidget/Dialog/Message/LineEdit）
与 T() 令牌，随全局主题自动换肤。
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import T
from InstructionX_UIKit.components import (
    Button,
    ComboBox,
    Dialog,
    LineEdit,
    ListWidget,
    Message,
)

#: 任务优先级选项
PRIORITY_OPTIONS = ["low", "normal", "high"]
#: 状态筛选选项（首项「全部」表示不筛选）
FILTER_OPTIONS = ["全部", "pending", "in_progress", "completed", "cancelled"]
#: 不筛选状态的选项文本
FILTER_ALL = "全部"


class MainWidget(QWidget):
    """任务管理器主界面"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()
        self._refresh_tasks()
        self._update_stats()

    # ------------------------------------------------------------------ 布局

    def _setup_ui(self):
        """构建 UI：滚动区承载全部内容分组。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._create_scroll_area())

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域并装配内容分组。"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        content_layout.addWidget(self._create_title())
        content_layout.addWidget(self._create_add_task_group())
        content_layout.addWidget(self._create_task_list_group())
        content_layout.addLayout(self._create_action_buttons())
        content_layout.addWidget(self._create_stats_group())
        content_layout.addStretch()
        scroll_area.setWidget(content)
        return scroll_area

    def _create_title(self) -> QLabel:
        """创建标题（字号取 UIKit 令牌，颜色随全局主题）。"""
        title = QLabel("任务管理器")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight.Bold)
        title.setFont(font)
        return title

    def _create_add_task_group(self) -> QGroupBox:
        """创建「添加新任务」分组。"""
        add_group = QGroupBox("添加新任务")
        add_layout = QVBoxLayout()
        add_layout.setSpacing(12)
        self.title_input = ListWidget()
        self.title_input.add_item("双击此处添加新任务...")
        self.title_input.itemDoubleClicked.connect(self._add_task_dialog)
        add_layout.addWidget(self.title_input)
        add_layout.addLayout(self._create_add_buttons_row())
        add_group.setLayout(add_layout)
        return add_group

    def _create_add_buttons_row(self) -> QHBoxLayout:
        """创建添加按钮与优先级选择行。"""
        button_layout = QHBoxLayout()
        add_btn = Button("添加任务", variant="primary")
        add_btn.clicked.connect(self._add_task_dialog)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(QLabel("优先级:"))
        self.priority_combo = ComboBox(PRIORITY_OPTIONS)
        button_layout.addWidget(self.priority_combo)
        return button_layout

    def _create_task_list_group(self) -> QGroupBox:
        """创建「任务列表」分组。"""
        list_group = QGroupBox("任务列表")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(12)
        self.task_list = ListWidget()
        self.task_list.itemDoubleClicked.connect(self._toggle_task_status)
        list_layout.addWidget(self.task_list)
        list_layout.addLayout(self._create_filter_row())
        list_group.setLayout(list_layout)
        return list_group

    def _create_filter_row(self) -> QHBoxLayout:
        """创建状态筛选与刷新按钮行。"""
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        filter_combo = ComboBox(FILTER_OPTIONS)
        filter_combo.currentTextChanged.connect(self._filter_tasks)
        filter_layout.addWidget(filter_combo)
        refresh_btn = Button("刷新")
        refresh_btn.clicked.connect(self._refresh_tasks)
        filter_layout.addWidget(refresh_btn)
        return filter_layout

    def _create_action_buttons(self) -> QHBoxLayout:
        """创建任务操作按钮行（完成/删除/导出）。"""
        action_layout = QHBoxLayout()
        complete_btn = Button("标记完成", variant="primary")
        complete_btn.clicked.connect(self._complete_task)
        action_layout.addWidget(complete_btn)
        delete_btn = Button("删除任务", variant="danger")
        delete_btn.clicked.connect(self._delete_task)
        action_layout.addWidget(delete_btn)
        export_btn = Button("导出任务")
        export_btn.clicked.connect(self._export_tasks)
        action_layout.addWidget(export_btn)
        return action_layout

    def _create_stats_group(self) -> QGroupBox:
        """创建「统计信息」分组。"""
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("加载中...")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        return stats_group

    # ------------------------------------------------------------------ 交互

    def _add_task_dialog(self):
        """弹出添加任务对话框（UIKit Dialog + LineEdit 文本输入）。"""
        dialog = Dialog(self, title="添加任务", ok_text="添加")
        title_edit = LineEdit(placeholder="请输入任务标题", clearable=True)
        dialog.set_content(title_edit)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        title = title_edit.text().strip()
        if not title:
            return
        task = self._service.add_task(
            title, priority=self.priority_combo.currentText())
        Message.info(self, f"任务已添加！ID: {task['id']}")
        self._refresh_tasks()
        self._update_stats()

    def _toggle_task_status(self):
        """双击任务项：在完成与待办状态间切换。"""
        item = self.task_list.currentItem()
        if not item:
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        tasks = self._service.get_tasks()
        current = next((t for t in tasks if t["id"] == task_id), None)
        if not current:
            return
        new_status = "completed" if current["status"] != "completed" else "pending"
        if self._service.update_task_status(task_id, new_status):
            self._refresh_tasks()
            self._update_stats()

    def _complete_task(self):
        """将选中任务标记为已完成。"""
        item = self.task_list.currentItem()
        if not item:
            Message.warning(self, "请先选择一个任务")
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        if self._service.update_task_status(task_id, "completed"):
            self._refresh_tasks()
            self._update_stats()
        else:
            Message.warning(self, "无法更新任务状态")

    def _delete_task(self):
        """弹出删除确认对话框（UIKit Dialog.confirm 非阻塞确认）。"""
        item = self.task_list.currentItem()
        if not item:
            Message.warning(self, "请先选择一个任务")
            return
        task_id = item.data(Qt.ItemDataRole.UserRole)
        Dialog.confirm(
            self, "确认删除", "确定要删除这个任务吗？",
            on_result=lambda ok: self._on_delete_confirmed(ok, task_id))

    def _on_delete_confirmed(self, confirmed: bool, task_id: str):
        """删除确认回调：确认后执行删除并刷新界面。"""
        if not confirmed:
            return
        if self._service.delete_task(task_id):
            self._refresh_tasks()
            self._update_stats()
        else:
            Message.warning(self, "删除失败")

    def _export_tasks(self):
        """导出任务为 JSON 文件并告知结果。"""
        try:
            path = self._service.export_tasks("json")
            Message.info(self, f"任务已导出到: {path}")
        except Exception as exc:  # 导出失败属操作结果错误，需明确告知用户
            Message.error(self, f"导出失败: {exc}")

    def _filter_tasks(self, status_filter: str):
        """按状态筛选并刷新任务列表。"""
        if status_filter == FILTER_ALL:
            tasks = self._service.get_tasks()
        else:
            tasks = self._service.get_tasks(status_filter)
        self._fill_task_list(tasks)

    # ------------------------------------------------------------------ 刷新

    def _refresh_tasks(self):
        """从服务层重新拉取全部任务并刷新列表。"""
        self._fill_task_list(self._service.get_tasks())

    def _fill_task_list(self, tasks):
        """将任务填充到列表控件（UserRole 存任务 ID）。"""
        self.task_list.clear()
        for task in tasks:
            item_text = f"[{task['priority']}] {task['title']} ({task['status']})"
            self.task_list.add_item(item_text, data=task["id"])

    def _update_stats(self):
        """刷新统计信息文本。"""
        stats = self._service.get_statistics()
        text = (
            f"总计: {stats['total']} | 待办: {stats['pending']} | "
            f"进行中: {stats['in_progress']} | 已完成: {stats['completed']}"
        )
        self.stats_label.setText(text)
