# -*- coding: utf-8 -*-
"""Framework API Demo 插件主控件（布局壳）。

负责左右分栏布局、公共结果面板/日志面板与 Tabs 容器装配；
各演示 Tab 的控件构建与事件处理位于 ui/tabs/ 包，
业务逻辑委托给 function/services 中的演示服务。
样式全面使用 InstructionX_UIKit 组件与 T() 令牌，随全局主题自动换肤。
"""

from datetime import datetime
from html import escape
from typing import Optional

from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox, QHBoxLayout, QVBoxLayout, QWidget,
)

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import Button, Tabs, TextArea

from core.i18n import get_language_manager
from core.interfaces import ILocalizationFacade

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
                 api_service, info_service, mcp_service, parent=None,
                 i18n: Optional[ILocalizationFacade] = None,
                 plugin_id: Optional[str] = None):
        """初始化主控件（参数为六个演示服务实例、父控件、取词门面与插件 UUID）"""
        super().__init__(parent)
        self.setObjectName("FrameworkApiDemoWidget")
        self._store_services(data_service, task_service, llm_service,
                             api_service, info_service, mcp_service)
        self._i18n = i18n
        self._plugin_id = plugin_id
        self._build_widget_layout()
        self._connect_language_signals()

    def _store_services(self, data_service, task_service, llm_service,
                        api_service, info_service, mcp_service):
        """保存六个演示服务实例（DataProvider/任务/LLM/API/Info/MCP 演示）"""
        self.data_service = data_service
        self.task_service = task_service
        self.llm_service = llm_service
        self.api_service = api_service
        self.info_service = info_service
        self.mcp_service = mcp_service

    # ------------------------------------------------------------------
    #  多语言取词与实时刷新
    # ------------------------------------------------------------------

    def _tr(self, group: str, key: str, /, **params) -> str:
        """取插件文案；门面未注入时优雅降级返回键名（正常加载路径框架始终注入）"""
        if self._i18n is None:
            return key
        return self._i18n.tr(group, key, **params)

    def tr_text(self, group: str, key: str, /, **params) -> str:
        """公开的取词入口：供 entrance 等外部调用方记录启动日志使用"""
        return self._tr(group, key, **params)

    def _connect_language_signals(self):
        """连接框架语言信号：框架语言变化与每插件语言覆盖变化均触发重翻译"""
        manager = get_language_manager()
        manager.language_changed.connect(self._retranslate_ui)
        manager.plugin_language_changed.connect(self._on_plugin_language_changed)

    def _on_plugin_language_changed(self, plugin_id: str, language: str):
        """每插件语言覆盖回调：仅当目标为本插件时重翻译"""
        if self._plugin_id is not None and plugin_id == self._plugin_id:
            self._retranslate_ui()

    def _retranslate_ui(self):
        """语言切换后重设全部用户可见文案（就地重设，不清空结果/日志历史）"""
        self._result_group.setTitle(self._tr("main", "panel.result.title"))
        self._clear_result_btn.setText(self._tr("main", "btn.clear_result"))
        self._log_group.setTitle(self._tr("main", "panel.log.title"))
        self._retranslate_tab_titles()
        for tab in self._iter_tabs():
            tab.retranslate()

    def _retranslate_tab_titles(self):
        """按当前语言重设 6 个 Tab 标签标题"""
        for index, key in enumerate(("data", "task", "llm", "api", "info", "mcp")):
            self._tab_widget.setTabText(index, self._tr("main", f"tab.{key}"))

    def _iter_tabs(self):
        """返回全部演示 Tab 实例（构造完成后均可用）"""
        return (self.data_tab, self.task_tab, self.llm_tab,
                self.api_tab, self.info_tab, self.mcp_tab)

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
        layout.addWidget(self._build_result_group(), stretch=3)
        layout.addWidget(self._build_log_group(), stretch=1)
        return panel

    def _build_result_group(self) -> QGroupBox:
        """构建「操作结果」分组：只读展示区 + 清除按钮"""
        self._result_group = QGroupBox(self._tr("main", "panel.result.title"))
        layout = QVBoxLayout()
        layout.setSpacing(4)
        self.result_display = TextArea()
        self.result_display.setReadOnly(True)
        self.result_display.setFont(QFont(MONO_FAMILY))
        layout.addWidget(self.result_display)
        self._clear_result_btn = Button(self._tr("main", "btn.clear_result"))
        self._clear_result_btn.clicked.connect(lambda: self.result_display.clear())
        layout.addWidget(self._clear_result_btn)
        self._result_group.setLayout(layout)
        return self._result_group

    def _build_log_group(self) -> QGroupBox:
        """构建「执行日志」分组：只读限高日志区"""
        self._log_group = QGroupBox(self._tr("main", "panel.log.title"))
        layout = QVBoxLayout()
        layout.setSpacing(4)
        self.log_text = TextArea()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont(MONO_FAMILY))
        self.log_text.setMaximumHeight(160)
        layout.addWidget(self.log_text)
        self._log_group.setLayout(layout)
        return self._log_group

    def _build_right_panel(self) -> QWidget:
        """构建右侧操作面板（实例化各演示 Tab 类，固定宽度 320px 防截断）"""
        panel = QWidget()
        panel.setFixedWidth(RIGHT_PANEL_FIXED_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tab_widget = Tabs()
        # 实例级收窄标签头内边距（UIKit 默认左右 16px），使 6 个标签在
        # 固定宽度内完整显示；仅作用于本实例 tabBar，不影响全局主题
        self._tab_widget.tabBar().setStyleSheet(
            "QTabBar::tab { padding-left: 6px; padding-right: 6px; }"
        )
        self._populate_tabs()
        layout.addWidget(self._tab_widget)
        return panel

    def _populate_tabs(self):
        """实例化 6 个演示 Tab 并按序加入标签容器（标签名取词）"""
        self._tab_widget.addTab(self._create_data_tab(), self._tr("main", "tab.data"))
        self._tab_widget.addTab(self._create_task_tab(), self._tr("main", "tab.task"))
        self._tab_widget.addTab(self._create_llm_tab(), self._tr("main", "tab.llm"))
        self._tab_widget.addTab(self._create_api_tab(), self._tr("main", "tab.api"))
        self._tab_widget.addTab(self._create_info_tab(), self._tr("main", "tab.info"))
        self._tab_widget.addTab(self._create_mcp_tab(), self._tr("main", "tab.mcp"))

    def _create_data_tab(self):
        """创建 DataProvider 演示 Tab"""
        self.data_tab = DataTab(self.data_service, self._display_result, self.append_log,
                                i18n=self._i18n)
        return self.data_tab.create_tab()

    def _create_task_tab(self):
        """创建后台任务演示 Tab"""
        self.task_tab = TaskTab(self.task_service, self._display_result, self.append_log,
                                i18n=self._i18n)
        return self.task_tab.create_tab()

    def _create_llm_tab(self):
        """创建 LLM 演示 Tab"""
        self.llm_tab = LLMTab(self.llm_service, self._display_result, self.append_log,
                              i18n=self._i18n)
        return self.llm_tab.create_tab()

    def _create_api_tab(self):
        """创建跨插件 API 演示 Tab"""
        self.api_tab = APITab(self.api_service, self._display_result, self.append_log,
                              i18n=self._i18n)
        return self.api_tab.create_tab()

    def _create_info_tab(self):
        """创建框架信息演示 Tab"""
        self.info_tab = InfoTab(self.info_service, self._display_result, self.append_log,
                                i18n=self._i18n)
        return self.info_tab.create_tab()

    def _create_mcp_tab(self):
        """创建 MCP 演示 Tab"""
        self.mcp_tab = MCPTab(self.mcp_service, self._display_result, self.append_log,
                              i18n=self._i18n)
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
