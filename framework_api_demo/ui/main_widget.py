# -*- coding: utf-8 -*-
"""Framework API Demo 插件主控件（布局壳）。

负责左右分栏布局、公共结果面板/日志面板与 Tabs 容器装配；
各演示 Tab 的控件构建与事件处理位于 ui/tabs/ 包，
业务逻辑委托给 function/services 中的演示服务。
样式全面使用 InstructionX_UIKit 组件与 T() 令牌，随全局主题自动换肤。
"""

from datetime import datetime
from html import escape

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QWidget,
)

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import Button, Tabs, TextArea

from .tabs import APITab, DataTab, InfoTab, LLMTab, MCPTab, TaskTab

# 右侧 Tab 操作面板固定宽度（像素）：各 Tab 的宽按钮行已压缩为多行排布，
# 按压缩后最宽表单行（标签 + 输入框 + 按钮，约 300px）加边距得出 320px；
# 窗口拉伸时多余空间全部分配给左侧结果面板
RIGHT_PANEL_FIXED_WIDTH = 320


class MainWidget(QWidget):
    """Framework API Demo 插件主控件

    左右分栏布局：左侧显示操作结果与执行日志，右侧为 6 个演示 Tab
    （DataProvider / Task / LLM / API / Info / MCP），固定宽度 320px。
    控件由 entrance.py 在 _create_widget 中实例化并注入各演示服务。
    """

    def __init__(self, data_service, task_service, llm_service,
                 api_service, info_service, mcp_service, parent=None):
        """初始化主控件

        参数:
            data_service: DataDemoService 实例（DataProvider 演示）
            task_service: TaskDemoService 实例（后台任务演示）
            llm_service: LLMDemoService 实例（LLM 演示）
            api_service: APIDemoService 实例（跨插件 API 演示）
            info_service: FrameworkInfoService 实例（框架信息演示）
            mcp_service: MCPDemoService 实例（MCP 演示）
            parent: 父控件
        """
        super().__init__(parent)
        self.setObjectName("FrameworkApiDemoWidget")
        self.data_service = data_service
        self.task_service = task_service
        self.llm_service = llm_service
        self.api_service = api_service
        self.info_service = info_service
        self.mcp_service = mcp_service
        self._build_widget_layout()

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def _build_widget_layout(self):
        """构建主控件左右分栏布局（右侧固定宽度，左侧弹性）"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(self._build_left_panel(), stretch=1)
        layout.addWidget(self._build_right_panel(), stretch=0)

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

        self.result_display = TextArea()
        self.result_display.setReadOnly(True)
        self.result_display.setFont(QFont(MONO_FAMILY))
        result_layout.addWidget(self.result_display)

        clear_btn = Button("清除结果")
        clear_btn.clicked.connect(lambda: self.result_display.clear())
        result_layout.addWidget(clear_btn)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group, stretch=3)

        # 执行日志
        log_group = QGroupBox("执行日志")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(4)

        self.log_text = TextArea()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont(MONO_FAMILY))
        self.log_text.setMaximumHeight(160)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group, stretch=1)

        return panel

    def _build_right_panel(self) -> QWidget:
        """构建右侧操作面板（实例化各演示 Tab 类，固定宽度 320px 防截断）"""
        panel = QWidget()
        panel.setFixedWidth(RIGHT_PANEL_FIXED_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tab_widget = Tabs()
        # 实例级收窄标签头内边距（UIKit 默认左右 16px），使 6 个标签在
        # 固定宽度内完整显示；仅作用于本实例 tabBar，不影响全局主题
        tab_widget.tabBar().setStyleSheet(
            "QTabBar::tab { padding-left: 6px; padding-right: 6px; }"
        )
        tab_widget.addTab(self._create_data_tab(), "Data")
        tab_widget.addTab(self._create_task_tab(), "Task")
        tab_widget.addTab(self._create_llm_tab(), "LLM")
        tab_widget.addTab(self._create_api_tab(), "API")
        tab_widget.addTab(self._create_info_tab(), "Info")
        tab_widget.addTab(self._create_mcp_tab(), "MCP")

        layout.addWidget(tab_widget)
        return panel

    def _create_data_tab(self):
        """创建 DataProvider 演示 Tab"""
        self.data_tab = DataTab(self.data_service, self._display_result, self.append_log)
        return self.data_tab.create_tab()

    def _create_task_tab(self):
        """创建后台任务演示 Tab"""
        self.task_tab = TaskTab(self.task_service, self._display_result, self.append_log)
        return self.task_tab.create_tab()

    def _create_llm_tab(self):
        """创建 LLM 演示 Tab"""
        self.llm_tab = LLMTab(self.llm_service, self._display_result, self.append_log)
        return self.llm_tab.create_tab()

    def _create_api_tab(self):
        """创建跨插件 API 演示 Tab"""
        self.api_tab = APITab(self.api_service, self._display_result, self.append_log)
        return self.api_tab.create_tab()

    def _create_info_tab(self):
        """创建框架信息演示 Tab"""
        self.info_tab = InfoTab(self.info_service, self._display_result, self.append_log)
        return self.info_tab.create_tab()

    def _create_mcp_tab(self):
        """创建 MCP 演示 Tab"""
        self.mcp_tab = MCPTab(self.mcp_service, self._display_result, self.append_log)
        return self.mcp_tab.create_tab()

    # ------------------------------------------------------------------
    #  结果展示与日志
    # ------------------------------------------------------------------

    def _display_result(self, title: str, content: str, is_error: bool = False):
        """在左侧操作结果面板中显示彩色卡片式结果

        颜色取 UIKit 语义令牌（color.danger / color.success）的当前值；
        历史卡片不随主题切换刷新（详见 SPEC 说明）。
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        if is_error:
            border_color = T("color.danger")
            title_color = T("color.danger")
            content_color = T("color.danger")
        else:
            border_color = T("color.success")
            title_color = T("color.success")
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

    def append_log(self, message: str):
        """追加一条日志到执行日志面板（自动带时间戳并滚动到底部）

        参数:
            message: 日志文本
        """
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _log(self, message: str):
        """添加日志到下方日志面板"""
        self.append_log(message)
