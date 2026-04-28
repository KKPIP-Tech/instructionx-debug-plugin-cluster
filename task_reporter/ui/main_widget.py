"""
任务报告生成器 UI
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QComboBox, QMessageBox,
    QInputDialog, QListWidget, QHBoxLayout, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer
from pathlib import Path
from utils.style_qss.registry import QssRegistry


class MainWidget(QWidget):
    """任务报告生成器主界面"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("MainWidget")
        self._service = service
        self._load_config()
        self._setup_ui()
        self._load_stylesheet()
        self._start_auto_refresh()

    def _load_config(self):
        try:
            cfg_path = Path(__file__).parent.parent / "config" / "default.json"
            import json
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            self._interval_ms = cfg.get("refresh", {}).get("interval_ms", 3000)
        except Exception:
            self._interval_ms = 3000

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        content = self._create_content_widget()
        scroll_area.setWidget(content)
        layout.addWidget(scroll_area)

    def _create_scroll_area(self):
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setFrameShape(QFrame.Shape.NoFrame)
        return area

    def _create_content_widget(self):
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        layout.addWidget(self._create_title())
        layout.addWidget(self._create_subscribe_group())
        layout.addWidget(self._create_stats_group())
        layout.addWidget(self._create_report_group())
        layout.addWidget(self._create_event_group())
        layout.addStretch()
        return content

    def _create_title(self):
        title = QLabel("任务报告生成器")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        title.setProperty("heading", "true")
        return title

    def _create_subscribe_group(self):
        group = QGroupBox("订阅管理")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(QLabel("任务管理器插件ID:"))
        id_layout = QHBoxLayout()
        self.manager_id_input = QListWidget()
        self._init_manager_id_list()
        self.manager_id_input.itemDoubleClicked.connect(self._edit_manager_id)
        id_layout.addWidget(self.manager_id_input)
        layout.addLayout(id_layout)
        btn_layout = self._create_subscribe_buttons()
        layout.addLayout(btn_layout)
        group.setLayout(layout)
        return group

    def _init_manager_id_list(self):
        active_id = self._service.get_active_task_manager_id()
        if active_id:
            self.manager_id_input.addItem(active_id)
            self.manager_id_input.addItem("双击修改ID...")
        else:
            self.manager_id_input.addItem("未找到活跃的TaskManager")
            self.manager_id_input.addItem("双击手动输入...")

    def _create_subscribe_buttons(self):
        btn_layout = QHBoxLayout()
        for label, handler in [("订阅", self._subscribe), ("取消订阅", self._unsubscribe)]:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            btn_layout.addWidget(btn)
        return btn_layout

    def _create_stats_group(self):
        group = QGroupBox("统计报告")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        self.stats_display = QTextEdit()
        self.stats_display.setReadOnly(True)
        self.stats_display.setMaximumHeight(150)
        layout.addWidget(self.stats_display)
        refresh_btn = QPushButton("刷新统计")
        refresh_btn.clicked.connect(self._refresh_stats)
        layout.addWidget(refresh_btn)
        group.setLayout(layout)
        return group

    def _create_report_group(self):
        group = QGroupBox("生成报告")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("格式:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["json", "txt", "html"])
        format_row.addWidget(self.format_combo)
        layout.addLayout(format_row)
        generate_btn = QPushButton("生成报告")
        generate_btn.clicked.connect(self._generate_report)
        layout.addWidget(generate_btn)
        group.setLayout(layout)
        return group

    def _create_event_group(self):
        group = QGroupBox("事件历史")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        self.event_list = QListWidget()
        self.event_list.setMaximumHeight(150)
        layout.addWidget(self.event_list)
        for label, handler in [("刷新事件", self._refresh_events), ("清除历史", self._clear_events)]:
            btn = QPushButton(label)
            btn.clicked.connect(handler)
            layout.addWidget(btn)
        group.setLayout(layout)
        return group

    def _start_auto_refresh(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(self._interval_ms)

    def _load_stylesheet(self):
        style_dir = Path(__file__).parent.parent / "style"
        if not style_dir.exists():
            return
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))
        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            self.setStyleSheet(self._qss_content)
            self.destroyed.connect(self._unload_stylesheet)

    def _unload_stylesheet(self):
        self.setStyleSheet("")

    def _edit_manager_id(self):
        current_id = self.manager_id_input.item(0).text()
        if current_id in ["未找到活跃的TaskManager", "双击手动输入..."]:
            current_id = ""

        new_id, ok = QInputDialog.getText(
            None, "修改任务管理器ID",
            "请输入任务管理器插件ID:",
            text=current_id
        )

        if ok and new_id:
            self.manager_id_input.clear()
            self.manager_id_input.addItem(new_id)
            self.manager_id_input.addItem("双击修改ID...")

    def _subscribe(self):
        manager_id = self.manager_id_input.item(0).text()
        if manager_id in ["未找到活跃的TaskManager", "双击手动输入...", "双击修改ID..."]:
            manager_id = None

        if self._service.subscribe_to_task_manager(manager_id):
            actual_id = self._service.get_active_task_manager_id() or manager_id
            if actual_id and actual_id != manager_id:
                self.manager_id_input.clear()
                self.manager_id_input.addItem(actual_id)
                self.manager_id_input.addItem("双击修改ID...")
            QMessageBox.information(None, "成功", "订阅成功！")
        else:
            QMessageBox.warning(None, "失败", "订阅失败，请确保 TaskManager 插件已激活")

    def _unsubscribe(self):
        manager_id = self.manager_id_input.item(0).text()
        if manager_id in ["未找到活跃的TaskManager", "双击手动输入...", "双击修改ID..."]:
            manager_id = None

        self._service.unsubscribe_from_task_manager(manager_id)
        QMessageBox.information(None, "成功", "已取消订阅")

    def _refresh_stats(self):
        manager_id = self._get_manager_id()
        report = self._service.get_statistics_report(manager_id)
        if "error" in report:
            self.stats_display.setText(f"错误: {report['error']}")
        else:
            self.stats_display.setText(self._format_stats_report(report))

    def _get_manager_id(self):
        mid = self.manager_id_input.item(0).text()
        if mid in ["未找到活跃的TaskManager", "双击手动输入...", "双击修改ID..."]:
            return None
        return mid

    def _format_stats_report(self, report):
        parts = []
        parts.append(f"生成时间: {report['generated_at']}")
        if "task_manager_id" in report:
            parts.append(f"TaskManager ID: {report['task_manager_id']}")
        parts.append("")
        if "statistics" in report:
            parts.extend(self._format_statistics(report["statistics"]))
        if "metrics" in report:
            parts.extend(self._format_metrics(report["metrics"]))
        return "\n".join(parts)

    def _format_statistics(self, stats):
        labels = [
            ("总计", "total"), ("待办", "pending"),
            ("进行中", "in_progress"), ("已完成", "completed"), ("已取消", "cancelled")
        ]
        lines = ["统计信息:"]
        for label, key in labels:
            lines.append(f"  {label}: {stats.get(key, 0)}")
        lines.append("")
        return lines

    def _format_metrics(self, metrics):
        labels = [
            ("完成率", "completion_rate"),
            ("待办比例", "pending_ratio"),
            ("进行中比例", "in_progress_ratio")
        ]
        lines = ["性能指标:"]
        for label, key in labels:
            lines.append(f"  {label}: {metrics.get(key, 0)}%")
        return lines

    def _auto_refresh(self):
        self._refresh_stats()
        self._refresh_events()

    def _refresh_events(self):
        events = self._service.get_event_history(20)
        self.event_list.clear()
        for event in events:
            event_type = event.get("type", "unknown")
            timestamp = event.get("timestamp", "")
            item_text = f"[{timestamp}] {event_type}"
            self.event_list.addItem(item_text)

    def _clear_events(self):
        reply = QMessageBox.question(
            None, "确认清除", "确定要清除所有事件历史吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self._service.clear_event_log()
            self._refresh_events()
            QMessageBox.information(None, "成功", "事件历史已清除")

    def _generate_report(self):
        manager_id = self.manager_id_input.item(0).text()
        if manager_id in ["未找到活跃的TaskManager", "双击手动输入...", "双击修改ID..."]:
            manager_id = None

        format_type = self.format_combo.currentText()

        try:
            path = self._service.generate_report(manager_id, format_type)
            QMessageBox.information(None, "生成成功", f"报告已生成到:\n{path}")
        except Exception as e:
            QMessageBox.critical(None, "生成失败", f"生成失败: {str(e)}")
