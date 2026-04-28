"""
任务管理器 UI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox,
    QGroupBox, QComboBox, QHBoxLayout, QScrollArea, QFrame
)
from PySide6.QtCore import Qt


class MainWidget(QWidget):
    """任务管理器主界面"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._setup_ui()
        self._refresh_tasks()
        self._update_stats()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        layout.addWidget(scroll_area)

    def _create_scroll_area(self):
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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

    def _create_title(self):
        title = QLabel("任务管理器")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_add_task_group(self):
        add_group = QGroupBox("添加新任务")
        add_layout = QVBoxLayout()
        add_layout.setSpacing(12)
        self.title_input = QListWidget()
        self.title_input.addItem("双击此处添加新任务...")
        self.title_input.itemDoubleClicked.connect(self._add_task_dialog)
        add_layout.addWidget(self.title_input)
        add_layout.addLayout(self._create_add_buttons_row())
        add_group.setLayout(add_layout)
        return add_group

    def _create_add_buttons_row(self):
        button_layout = QHBoxLayout()
        add_btn = QPushButton("添加任务")
        add_btn.clicked.connect(self._add_task_dialog)
        button_layout.addWidget(add_btn)
        button_layout.addWidget(QLabel("优先级:"))
        priority_combo = QComboBox()
        priority_combo.addItems(["low", "normal", "high"])
        button_layout.addWidget(priority_combo)
        self.priority_combo = priority_combo
        return button_layout

    def _create_task_list_group(self):
        list_group = QGroupBox("任务列表")
        list_layout = QVBoxLayout()
        list_layout.setSpacing(12)
        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(self._toggle_task_status)
        list_layout.addWidget(self.task_list)
        list_layout.addLayout(self._create_filter_row())
        list_group.setLayout(list_layout)
        return list_group

    def _create_filter_row(self):
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("筛选:"))
        filter_combo = QComboBox()
        filter_combo.addItems(["全部", "pending", "in_progress", "completed", "cancelled"])
        filter_combo.currentTextChanged.connect(self._filter_tasks)
        filter_layout.addWidget(filter_combo)
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self._refresh_tasks)
        filter_layout.addWidget(refresh_btn)
        return filter_layout

    def _create_action_buttons(self):
        action_layout = QHBoxLayout()
        complete_btn = QPushButton("标记完成")
        complete_btn.clicked.connect(self._complete_task)
        action_layout.addWidget(complete_btn)
        delete_btn = QPushButton("删除任务")
        delete_btn.clicked.connect(self._delete_task)
        action_layout.addWidget(delete_btn)
        export_btn = QPushButton("导出任务")
        export_btn.clicked.connect(self._export_tasks)
        action_layout.addWidget(export_btn)
        return action_layout

    def _create_stats_group(self):
        stats_group = QGroupBox("统计信息")
        stats_layout = QVBoxLayout()
        self.stats_label = QLabel("加载中...")
        stats_layout.addWidget(self.stats_label)
        stats_group.setLayout(stats_layout)
        return stats_group

    def _add_task_dialog(self):
        title, ok = QInputDialog.getText(None, "添加任务", "请输入任务标题:")
        if ok and title:
            priority = self.priority_combo.currentText()
            task = self._service.add_task(title, priority=priority)
            QMessageBox.information(None, "成功", f"任务已添加！\nID: {task['id']}")
            self._refresh_tasks()
            self._update_stats()

    def _toggle_task_status(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.ItemDataRole.UserRole)
            tasks = self._service.get_tasks()
            current_task = None
            for task in tasks:
                if task["id"] == task_id:
                    current_task = task
                    break
            if current_task:
                status = current_task["status"]
                new_status = "completed" if status != "completed" else "pending"
                if self._service.update_task_status(task_id, new_status):
                    self._refresh_tasks()
                    self._update_stats()

    def _complete_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.ItemDataRole.UserRole)
            if self._service.update_task_status(task_id, "completed"):
                self._refresh_tasks()
                self._update_stats()
            else:
                QMessageBox.warning(None, "警告", "无法更新任务状态")
        else:
            QMessageBox.warning(None, "警告", "请先选择一个任务")

    def _delete_task(self):
        current_item = self.task_list.currentItem()
        if current_item:
            task_id = current_item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(
                None, "确认删除", "确定要删除这个任务吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if self._service.delete_task(task_id):
                    self._refresh_tasks()
                    self._update_stats()
                else:
                    QMessageBox.warning(None, "警告", "删除失败")
        else:
            QMessageBox.warning(None, "警告", "请先选择一个任务")

    def _export_tasks(self):
        try:
            path = self._service.export_tasks("json")
            QMessageBox.information(None, "导出成功", f"任务已导出到:\n{path}")
        except Exception as e:
            QMessageBox.critical(None, "导出失败", f"导出失败: {str(e)}")

    def _filter_tasks(self, status_filter):
        if status_filter == "全部":
            tasks = self._service.get_tasks()
        else:
            tasks = self._service.get_tasks(status_filter)
        self.task_list.clear()
        for task in tasks:
            item_text = f"[{task['priority']}] {task['title']} ({task['status']})"
            item = QListWidgetItem(item_text, self.task_list)
            item.setData(Qt.ItemDataRole.UserRole, task["id"])

    def _refresh_tasks(self):
        tasks = self._service.get_tasks()
        self.task_list.clear()
        for task in tasks:
            item_text = f"[{task['priority']}] {task['title']} ({task['status']})"
            item = QListWidgetItem(item_text, self.task_list)
            item.setData(Qt.ItemDataRole.UserRole, task["id"])

    def _update_stats(self):
        stats = self._service.get_statistics()
        text = (
            f"总计: {stats['total']} | 待办: {stats['pending']} | "
            f"进行中: {stats['in_progress']} | 已完成: {stats['completed']}"
        )
        self.stats_label.setText(text)
