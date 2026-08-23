# -*- coding: utf-8 -*-
"""ui/tabs 包公共基座：BaseTab。

提供各演示 Tab 共享的滚动容器构建、结果回调与日志回调访问能力。
结果展示与日志记录由 main_widget 的公共面板统一承载，
各 Tab 通过构造注入的回调进行调用，保持行为与拆分前一致。
"""

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGroupBox, QLabel, QScrollArea, QVBoxLayout, QWidget

from InstructionX_UIKit.components import Button

from core.interfaces import ILocalizationFacade


class BaseTab:
    """演示 Tab 基类

    职责：持有演示服务实例与 main_widget 注入的结果/日志回调，
    提供带滚动区域的 Tab 内容容器构建辅助与文案重翻译绑定登记。
    子类负责各自演示主题的控件构建与事件处理（槽函数仅取输入、
    调服务、显示结果的委托模式）。
    """

    def __init__(self, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化 Tab 基座

        参数:
            display_result: 结果显示回调，签名 (title, content, is_error=False)
            append_log: 日志追加回调，签名 (message)
            i18n: 插件取词门面（框架经 PluginServices.localization 注入；
                未注入时文案优雅降级为键名）
        """
        self._display_result = display_result
        self._append_log = append_log
        self._i18n = i18n
        # Message 弹窗的父控件：create_tab 时指向本 Tab 的滚动容器
        self._message_parent: QWidget | None = None
        # 静态文案绑定表 (widget, setter, group, key)：语言切换时由
        # retranslate() 逐个重设；动态内容在生成时取词，不入表
        self._text_bindings: list[tuple] = []

    def _tr(self, group: str, key: str, /, **params) -> str:
        """取插件文案；门面未注入时优雅降级返回键名（正常加载路径框架始终注入）"""
        if self._i18n is None:
            return key
        return self._i18n.tr(group, key, **params)

    def _bind(self, widget, group: str, key: str, setter: str = "setText"):
        """登记语言切换需重设文案的控件（构造时已取词，此处仅登记绑定）

        参数:
            widget: 目标控件
            group: 语言文件分组名
            key: 分组内点分键名
            setter: 重设文案的方法名（按钮/标签 setText，分组 setTitle，
                输入框占位 setPlaceholderText）
        """
        self._text_bindings.append((widget, setter, group, key))

    def _make_label(self, group: str, key: str) -> QLabel:
        """创建已登记重翻译绑定的表单标签"""
        label = QLabel(self._tr(group, key))
        self._bind(label, group, key)
        return label

    def _make_group(self, group: str, key: str) -> QGroupBox:
        """创建已登记重翻译绑定的分组框（标题取词）"""
        box = QGroupBox(self._tr(group, key))
        self._bind(box, group, key, setter="setTitle")
        return box

    def _make_button(self, group: str, key: str, slot,
                     variant: Optional[str] = None) -> "Button":
        """创建已登记重翻译绑定的按钮并连接槽函数

        参数:
            group: 语言文件分组名
            key: 按钮文案键名
            slot: clicked 槽函数
            variant: UIKit 按钮变体（如 "primary"/"danger"），缺省为默认样式
        """
        kwargs = {"variant": variant} if variant else {}
        btn = Button(self._tr(group, key), **kwargs)
        btn.clicked.connect(slot)
        self._bind(btn, group, key)
        return btn

    def retranslate(self) -> None:
        """语言切换后按绑定表重设本 Tab 全部静态文案（动态内容生成时取词）"""
        for widget, setter, group, key in self._text_bindings:
            getattr(widget, setter)(self._tr(group, key))

    def _make_scroll_tab(self) -> tuple[QScrollArea, QVBoxLayout]:
        """创建带滚动区域的 Tab 内容容器"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(10)
        layout.setContentsMargins(4, 4, 4, 4)

        scroll.setWidget(widget)
        return scroll, layout

    def _log(self, message: str):
        """添加日志到主控件日志面板"""
        self._append_log(message)
