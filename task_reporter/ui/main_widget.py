# -*- coding: utf-8 -*-
"""任务报告生成器主控件。

负责构建和管理所有 UI 元素，通过 Service 实例调用业务逻辑。
样式全面使用 InstructionX_UIKit 组件（Button/ComboBox/ListWidget/TextArea/
Dialog/LineEdit/Message）与 T() 令牌，随全局主题自动换肤。
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
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
    TextArea,
)

#: 自动刷新默认间隔（毫秒），配置缺失时回退
_DEFAULT_INTERVAL_MS = 3000
#: 统计展示区最大高度（px）
_STATS_MAX_HEIGHT = 150
#: 事件历史列表最大高度（px）
_EVENT_LIST_MAX_HEIGHT = 150
#: 事件历史单次刷新条数
_EVENT_DISPLAY_LIMIT = 20
#: 管理器 ID 列表占位提示文案
_NO_MANAGER_HINT = "未找到活跃的TaskManager"
_MANUAL_INPUT_HINT = "双击手动输入..."
_EDIT_ID_HINT = "双击修改ID..."
#: 全部占位提示（出现时视为「无有效 ID」）
_PLACEHOLDER_HINTS = (_NO_MANAGER_HINT, _MANUAL_INPUT_HINT, _EDIT_ID_HINT)
#: 报告格式选项
_REPORT_FORMATS = ("json", "txt", "html")


class MainWidget(QWidget):
    """任务报告生成器主界面"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._load_config()
        self._setup_ui()
        self._start_auto_refresh()

    def _load_config(self):
        """读取刷新间隔配置，读取失败时回退默认值"""
        try:
            cfg_path = Path(__file__).parent.parent / "config" / "default.json"
            cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
            self._interval_ms = cfg.get("refresh", {}).get(
                "interval_ms", _DEFAULT_INTERVAL_MS)
        except (OSError, ValueError):
            self._interval_ms = _DEFAULT_INTERVAL_MS

    def _setup_ui(self):
        """构建 UI：滚动区包裹内容区"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        scroll_area = self._create_scroll_area()
        scroll_area.setWidget(self._create_content_widget())
        layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        """创建纵向滚动区域"""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setFrameShape(QFrame.Shape.NoFrame)
        return area

    def _create_content_widget(self) -> QWidget:
        """创建内容区：标题 + 四个功能分组"""
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

    def _create_title(self) -> QLabel:
        """创建标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("任务报告生成器")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight.Bold)
        title.setFont(font)
        return title

    def _create_subscribe_group(self) -> QGroupBox:
        """创建订阅管理分组"""
        group = QGroupBox("订阅管理")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(QLabel("任务管理器插件ID:"))
        self.manager_id_input = ListWidget()
        self._init_manager_id_list()
        self.manager_id_input.itemDoubleClicked.connect(self._edit_manager_id)
        layout.addWidget(self.manager_id_input)
        layout.addLayout(self._create_subscribe_buttons())
        group.setLayout(layout)
        return group

    def _init_manager_id_list(self):
        """按当前活跃 TaskManager 初始化 ID 列表"""
        active_id = self._service.get_active_task_manager_id()
        if active_id:
            self.manager_id_input.addItem(active_id)
            self.manager_id_input.addItem(_EDIT_ID_HINT)
        else:
            self.manager_id_input.addItem(_NO_MANAGER_HINT)
            self.manager_id_input.addItem(_MANUAL_INPUT_HINT)

    def _create_subscribe_buttons(self) -> QHBoxLayout:
        """创建订阅/取消订阅按钮行"""
        btn_layout = QHBoxLayout()
        subscribe_btn = Button("订阅", variant="primary")
        subscribe_btn.clicked.connect(self._subscribe)
        unsubscribe_btn = Button("取消订阅", variant="default")
        unsubscribe_btn.clicked.connect(self._unsubscribe)
        btn_layout.addWidget(subscribe_btn)
        btn_layout.addWidget(unsubscribe_btn)
        return btn_layout

    def _create_stats_group(self) -> QGroupBox:
        """创建统计报告分组"""
        group = QGroupBox("统计报告")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        self.stats_display = TextArea()
        self.stats_display.setReadOnly(True)
        self.stats_display.setMaximumHeight(_STATS_MAX_HEIGHT)
        layout.addWidget(self.stats_display)
        refresh_btn = Button("刷新统计", variant="default")
        refresh_btn.clicked.connect(self._refresh_stats)
        layout.addWidget(refresh_btn)
        group.setLayout(layout)
        return group

    def _create_report_group(self) -> QGroupBox:
        """创建生成报告分组"""
        group = QGroupBox("生成报告")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("格式:"))
        self.format_combo = ComboBox(list(_REPORT_FORMATS))
        format_row.addWidget(self.format_combo)
        layout.addLayout(format_row)
        generate_btn = Button("生成报告", variant="primary")
        generate_btn.clicked.connect(self._generate_report)
        layout.addWidget(generate_btn)
        group.setLayout(layout)
        return group

    def _create_event_group(self) -> QGroupBox:
        """创建事件历史分组"""
        group = QGroupBox("事件历史")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        self.event_list = ListWidget()
        self.event_list.setMaximumHeight(_EVENT_LIST_MAX_HEIGHT)
        layout.addWidget(self.event_list)
        refresh_btn = Button("刷新事件", variant="default")
        refresh_btn.clicked.connect(self._refresh_events)
        layout.addWidget(refresh_btn)
        clear_btn = Button("清除历史", variant="danger")
        clear_btn.clicked.connect(self._clear_events)
        layout.addWidget(clear_btn)
        group.setLayout(layout)
        return group

    def _start_auto_refresh(self):
        """启动 QTimer 定时自动刷新"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._auto_refresh)
        self.timer.start(self._interval_ms)

    def _current_manager_id(self):
        """取列表首项中的有效管理器 ID，占位提示时返回 None"""
        item = self.manager_id_input.item(0)
        if item is None or item.text() in _PLACEHOLDER_HINTS:
            return None
        return item.text()

    def _set_manager_id(self, manager_id: str):
        """以指定 ID 重建管理器 ID 列表内容"""
        self.manager_id_input.clear()
        self.manager_id_input.addItem(manager_id)
        self.manager_id_input.addItem(_EDIT_ID_HINT)

    def _edit_manager_id(self):
        """双击列表时弹出对话框编辑任务管理器 ID"""
        dialog = Dialog(self, title="修改任务管理器ID")
        editor = LineEdit(placeholder="请输入任务管理器插件ID")
        editor.setText(self._current_manager_id() or "")
        dialog.set_content(editor)
        accepted = dialog.exec() == QDialog.DialogCode.Accepted
        if accepted and editor.text():
            self._set_manager_id(editor.text())

    def _subscribe(self):
        """订阅任务管理器数据变更"""
        manager_id = self._current_manager_id()
        if not self._service.subscribe_to_task_manager(manager_id):
            Message.warning(self, "订阅失败，请确保 TaskManager 插件已激活")
            return
        actual_id = self._service.get_active_task_manager_id() or manager_id
        if actual_id and actual_id != manager_id:
            self._set_manager_id(actual_id)
        Message.info(self, "订阅成功！")

    def _unsubscribe(self):
        """取消订阅任务管理器"""
        self._service.unsubscribe_from_task_manager(self._current_manager_id())
        Message.info(self, "已取消订阅")

    def _refresh_stats(self):
        """刷新统计报告展示区"""
        report = self._service.get_statistics_report(self._current_manager_id())
        if "error" in report:
            self.stats_display.setText(f"错误: {report['error']}")
        else:
            self.stats_display.setText(self._format_stats_report(report))

    def _format_stats_report(self, report) -> str:
        """将统计报告字典格式化为多行文本"""
        parts = [f"生成时间: {report['generated_at']}"]
        if "task_manager_id" in report:
            parts.append(f"TaskManager ID: {report['task_manager_id']}")
        parts.append("")
        if "statistics" in report:
            parts.extend(self._format_statistics(report["statistics"]))
        if "metrics" in report:
            parts.extend(self._format_metrics(report["metrics"]))
        return "\n".join(parts)

    def _format_statistics(self, stats) -> list:
        """格式化统计信息行"""
        labels = [
            ("总计", "total"), ("待办", "pending"),
            ("进行中", "in_progress"), ("已完成", "completed"), ("已取消", "cancelled")
        ]
        lines = ["统计信息:"]
        for label, key in labels:
            lines.append(f"  {label}: {stats.get(key, 0)}")
        lines.append("")
        return lines

    def _format_metrics(self, metrics) -> list:
        """格式化性能指标行"""
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
        """定时器回调：刷新统计与事件历史"""
        self._refresh_stats()
        self._refresh_events()

    def _refresh_events(self):
        """刷新事件历史列表"""
        events = self._service.get_event_history(_EVENT_DISPLAY_LIMIT)
        self.event_list.clear()
        for event in events:
            event_type = event.get("type", "unknown")
            timestamp = event.get("timestamp", "")
            self.event_list.addItem(f"[{timestamp}] {event_type}")

    def _clear_events(self):
        """弹出确认对话框，确认后清除事件历史"""
        Dialog.confirm(self, "确认清除", "确定要清除所有事件历史吗？",
                       on_result=self._on_clear_confirmed)

    def _on_clear_confirmed(self, confirmed: bool):
        """确认清除回调：清除事件日志并刷新列表"""
        if not confirmed:
            return
        self._service.clear_event_log()
        self._refresh_events()
        Message.info(self, "事件历史已清除")

    def _generate_report(self):
        """按所选格式生成报告并以轻提示反馈结果"""
        format_type = self.format_combo.currentText()
        try:
            path = self._service.generate_report(
                self._current_manager_id(), format_type)
            Message.info(self, f"报告已生成到:\n{path}")
        except Exception as e:
            Message.warning(self, f"生成失败: {e}")
