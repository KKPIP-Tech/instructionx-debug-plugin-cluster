# -*- coding: utf-8 -*-
"""框架信息演示 Tab。

演示框架信息获取、框架 utils 工具（日志级别、线程封送、图片转 Base64）、
FontManager 字体子系统（只读）、ILocalizationFacade 多语言门面（只读）、
UIKit 主题跟随，并展示可用接口文档文本。
槽函数仅调用 FrameworkInfoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

import json
from typing import Any, Callable, Dict, Optional

from PySide6.QtWidgets import QFormLayout, QGroupBox, QLabel, QVBoxLayout, QScrollArea

from InstructionX_UIKit import ThemeManager
from InstructionX_UIKit.components import Button, LineEdit, TextArea

from core.interfaces import ILocalizationFacade

from .base_tab import BaseTab

# 结果面板展示 JSON 的缩进宽度
_JSON_INDENT = 2

# 分组内布局默认间距（像素）
_GROUP_SPACING = 8


class InfoTab(BaseTab):
    """框架信息演示 Tab

    职责：构建信息演示页的控件布局（含框架信息、utils 工具演示、
    主题跟随演示与可用接口文档）并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, info_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化信息演示 Tab

        参数:
            info_service: FrameworkInfoService 实例（框架信息演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
        self.info_service = info_service

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 Info Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        layout.addWidget(self._build_info_group())
        layout.addWidget(self._build_log_group())
        layout.addWidget(self._build_thread_group())
        layout.addWidget(self._build_asset_group())
        layout.addWidget(self._build_font_group())
        layout.addWidget(self._build_i18n_group())
        layout.addWidget(self._build_theme_group())
        layout.addWidget(self._build_info_doc_group())
        layout.addStretch()
        return scroll

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_info 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_info", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_info 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_info", key, slot, variant=variant)

    def _build_info_group(self) -> QGroupBox:
        group = self._make_group("group.info")
        layout = QVBoxLayout()
        layout.setSpacing(8)
        self.get_info_btn = self._make_button(
            "btn.get_info", self._on_get_framework_info, variant="primary")
        layout.addWidget(self.get_info_btn)
        self.info_text = TextArea()
        self.info_text.setReadOnly(True)
        layout.addWidget(self.info_text)
        group.setLayout(layout)
        return group

    def _build_log_group(self) -> QGroupBox:
        """构建「日志级别」分组：写入 LoggerManager 五级日志"""
        group = self._make_group("group.log")
        layout = QVBoxLayout()
        self.log_levels_btn = self._make_button(
            "btn.log_levels", self._on_write_log_levels, variant="primary")
        layout.addWidget(self.log_levels_btn)
        group.setLayout(layout)
        return group

    def _build_thread_group(self) -> QGroupBox:
        """构建「线程工具」分组：演示 is_ui_thread 与 run_in_ui_thread(_sync)"""
        group = self._make_group("group.thread")
        layout = QVBoxLayout()
        self.thread_utils_btn = self._make_button(
            "btn.thread", self._on_demo_thread_utils, variant="primary")
        layout.addWidget(self.thread_utils_btn)
        group.setLayout(layout)
        return group

    def _build_asset_group(self) -> QGroupBox:
        """构建「资源工具」分组：image_utils 图片转 Base64"""
        group = self._make_group("group.asset")
        layout = QVBoxLayout()
        self.image_base64_btn = self._make_button(
            "btn.base64", self._on_demo_image_base64, variant="primary")
        layout.addWidget(self.image_base64_btn)
        group.setLayout(layout)
        return group

    def _build_font_group(self) -> QGroupBox:
        """构建「字体子系统」分组（FontManager 只读演示，不含安装/卸载写操作）"""
        group = self._make_group("group.font")
        form = QFormLayout()
        self.font_family_input = LineEdit(
            text=self._tr("tab_info", "default.font_family"))
        form.addRow(self._make_label("tab_info", "label.font_family"),
                    self.font_family_input)
        self.list_fonts_btn = self._make_button(
            "btn.list_fonts", self._on_list_fonts, variant="primary")
        form.addRow("", self.list_fonts_btn)
        self.resolve_font_btn = self._make_button(
            "btn.resolve_font", self._on_resolve_font)
        form.addRow("", self.resolve_font_btn)
        group.setLayout(form)
        return group

    def _build_i18n_group(self) -> QGroupBox:
        """构建「多语言门面」分组（ILocalizationFacade 只读能力演示）"""
        group = self._make_group("group.i18n")
        layout = QVBoxLayout()
        self.i18n_info_btn = self._make_button(
            "btn.i18n_info", self._on_show_i18n_info, variant="primary")
        layout.addWidget(self.i18n_info_btn)
        group.setLayout(layout)
        return group

    def _build_theme_group(self) -> QGroupBox:
        """构建「主题跟随」分组：监听 ThemeManager.theme_changed

        UIKit 组件本身随全局 QSS 自动跟随主题，无需监听信号；
        只有插件自建样式（自定义 QSS/绘制）才需要监听 theme_changed 做适配。
        """
        group = self._make_group("group.theme")
        layout = QVBoxLayout()
        theme_manager = ThemeManager.instance()
        # 主题标签文案含 {mode} 参数，不走无参绑定，由 _update_theme_label 管理
        self.theme_status_label = QLabel()
        self._update_theme_label(theme_manager.mode)
        layout.addWidget(self.theme_status_label)
        theme_manager.theme_changed.connect(self._on_theme_changed)
        group.setLayout(layout)
        return group

    def _update_theme_label(self, mode: str):
        """按当前语言与主题模式更新主题状态标签"""
        self.theme_status_label.setText(self._tr("tab_info", "label.theme", mode=mode))

    def _build_info_doc_group(self) -> QGroupBox:
        self._doc_text = TextArea()
        self._doc_text.setReadOnly(True)
        self._doc_text.setPlainText(self._tr("tab_info", "doc.api_text"))
        group = self._make_group("group.doc")
        layout = QVBoxLayout()
        layout.addWidget(self._doc_text)
        group.setLayout(layout)
        return group

    def retranslate(self) -> None:
        """语言切换后重设静态文案，并按当前语言重取 API 文档文本"""
        super().retranslate()
        self._doc_text.setPlainText(self._tr("tab_info", "doc.api_text"))
        self._update_theme_label(ThemeManager.instance().mode)

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_get_framework_info(self):
        result = self.info_service.get_framework_info()
        self._log(self._tr("tab_info", "log.info", result=result))
        if result:
            content = json.dumps(result, indent=_JSON_INDENT, ensure_ascii=False)
            self._display_result(self._tr("tab_info", "title.info"), content)
            self.info_text.setPlainText(content)
        else:
            self._display_result(self._tr("tab_info", "title.info_fail"),
                                 self._tr("tab_info", "msg.no_data"), is_error=True)

    def _on_write_log_levels(self):
        """写入五级日志并展示结果"""
        result = self.info_service.demo_log_levels()
        self._show_service_result(self._tr("tab_info", "op.log_demo"), result)

    def _on_demo_thread_utils(self):
        """演示线程封送：is_ui_thread 对照经服务任务回传"""
        result = self.info_service.demo_thread_utils()
        self._show_service_result(self._tr("tab_info", "op.thread_demo"), result)

    def _on_demo_image_base64(self):
        """演示图片转 Base64"""
        result = self.info_service.demo_load_image_base64()
        self._show_service_result(self._tr("tab_info", "op.base64_demo"), result)

    def _on_list_fonts(self):
        """列出框架已注册字体（FontManager 只读演示）"""
        result = self.info_service.demo_list_fonts()
        self._show_service_result(self._tr("tab_info", "op.font_list"), result)

    def _on_resolve_font(self):
        """演示系统字体回退解析（输入故意不存在的家族名可观察到回退链）"""
        family = self.font_family_input.text().strip()
        result = self.info_service.demo_resolve_family(family)
        self._show_service_result(self._tr("tab_info", "op.font_resolve"), result)

    def _on_show_i18n_info(self):
        """查看多语言门面信息（当前语言 / 插件语言包清单 / 语言目录存在性）"""
        result = self.info_service.demo_localization_info()
        self._show_service_result(self._tr("tab_info", "op.i18n_demo"), result)

    def _on_theme_changed(self, mode: str):
        """主题切换回调：更新状态标签并记录日志（UIKit 组件本身自动跟随主题）"""
        self._update_theme_label(mode)
        self._log(self._tr("tab_info", "log.theme_changed", mode=mode))

    def _show_service_result(self, title: str, result: Dict[str, Any]):
        """统一展示服务返回结果（含失败分支）"""
        self._log(f"{title}: {result}")
        content = json.dumps(result, indent=_JSON_INDENT, ensure_ascii=False)
        self._display_result(title, content, is_error=not result.get("success", False))
