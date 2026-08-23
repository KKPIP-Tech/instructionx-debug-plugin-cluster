# -*- coding: utf-8 -*-
"""DataProvider 演示 Tab。

演示插件注册、Private/Public 数据读写、数据查询与资源管理。
槽函数仅取输入、调用 DataDemoService、显示结果，业务逻辑在服务层。
静态文案经 _tr 取词并登记绑定，语言切换由 retranslate() 统一重设。
"""

import json
from typing import Callable, Optional

from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, Message

from core.interfaces import ILocalizationFacade
from utils.thread_utils import run_in_ui_thread

from .base_tab import BaseTab


class DataTab(BaseTab):
    """DataProvider 演示 Tab

    职责：构建 DataProvider 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, data_service, display_result: Callable, append_log: Callable,
                 i18n: Optional[ILocalizationFacade] = None):
        """初始化 DataProvider 演示 Tab

        参数:
            data_service: DataDemoService 实例（DataProvider 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
            i18n: 插件取词门面（可选）
        """
        super().__init__(display_result, append_log, i18n=i18n)
        self.data_service = data_service
        # 订阅回调在工作线程触发，经 run_in_ui_thread 封送到 UI 线程写日志
        self.data_service.set_event_notifier(self._on_subscription_notify)

    def _on_subscription_notify(self, message: str):
        """订阅事件通知（工作线程）：封送到 UI 线程追加日志"""
        run_in_ui_thread(self._append_log, message)

    # ------------------------------------------------------------------
    #  布局构建
    # ------------------------------------------------------------------

    def create_tab(self) -> QScrollArea:
        """构建 DataProvider Tab 内容"""
        scroll, layout = self._make_scroll_tab()
        self._message_parent = scroll
        layout.addWidget(self._build_data_register_controls())
        layout.addWidget(self._build_data_private_group())
        layout.addWidget(self._build_data_public_group())
        layout.addWidget(self._build_data_query_controls())
        layout.addWidget(self._build_data_assets_section())
        layout.addWidget(self._build_pubsub_group())
        layout.addStretch()
        return scroll

    def _make_group(self, key: str) -> QGroupBox:
        """创建本 Tab 分组框（标题取 tab_data 分组 group.* 键并登记绑定）"""
        return super()._make_group("tab_data", key)

    def _make_button(self, key: str, slot, variant: Optional[str] = None) -> Button:
        """创建本 Tab 按钮（文案取 tab_data 分组 btn.* 键并登记绑定）"""
        return super()._make_button("tab_data", key, slot, variant=variant)

    def _build_data_register_controls(self) -> QGroupBox:
        group = self._make_group("group.register")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.register_plugin_btn = self._make_button(
            "btn.register", self._on_register_plugin, variant="primary")
        row.addWidget(self.register_plugin_btn)
        self.unregister_plugin_btn = self._make_button(
            "btn.unregister", self._on_unregister_plugin)
        row.addWidget(self.unregister_plugin_btn)
        row.addStretch()
        group.setLayout(row)
        return group

    def _build_data_private_group(self) -> QGroupBox:
        group = self._make_group("group.private")
        form = QFormLayout()
        form.setSpacing(6)
        self.private_key_input = LineEdit(text="test_key", placeholder="key")
        form.addRow(self._make_label("common", "label.key"), self.private_key_input)
        self.private_value_input = LineEdit(text="test_value", placeholder="value")
        form.addRow(self._make_label("common", "label.value"), self.private_value_input)
        form.addRow("", self._build_write_read_row(
            self._on_write_private, self._on_read_private))
        group.setLayout(form)
        return group

    def _build_data_public_group(self) -> QGroupBox:
        group = self._make_group("group.public")
        form = QFormLayout()
        form.setSpacing(6)
        self.public_key_input = LineEdit(text="shared_key", placeholder="key")
        form.addRow(self._make_label("common", "label.key"), self.public_key_input)
        self.public_value_input = LineEdit(text="shared_value", placeholder="value")
        form.addRow(self._make_label("common", "label.value"), self.public_value_input)
        form.addRow("", self._build_write_read_row(
            self._on_write_public, self._on_read_public))
        group.setLayout(form)
        return group

    def _build_write_read_row(self, write_slot, read_slot) -> QHBoxLayout:
        """构建写入/读取按钮行（Private 与 Public 分组共用）"""
        row = QHBoxLayout()
        row.addWidget(self._make_button("btn.write", write_slot, variant="primary"))
        row.addWidget(self._make_button("btn.read", read_slot))
        return row

    def _build_data_query_controls(self) -> QGroupBox:
        group = self._make_group("group.query")
        layout = QVBoxLayout()
        self.get_all_data_btn = self._make_button(
            "btn.get_all", self._on_get_all_data, variant="primary")
        layout.addWidget(self.get_all_data_btn)
        group.setLayout(layout)
        return group

    def _build_data_assets_section(self) -> QGroupBox:
        group = self._make_group("group.assets")
        row = QHBoxLayout()
        row.setSpacing(8)
        self.save_asset_btn = self._make_button(
            "btn.save_asset", self._on_save_asset, variant="primary")
        row.addWidget(self.save_asset_btn)
        self.load_asset_btn = self._make_button("btn.load_asset", self._on_load_asset)
        row.addWidget(self.load_asset_btn)
        row.addStretch()
        group.setLayout(row)
        return group

    def _build_pubsub_group(self) -> QGroupBox:
        """构建发布订阅演示分组（按钮拆为两行，适配收窄后的面板宽度）"""
        group = self._make_group("group.pubsub")
        form = QFormLayout()
        form.setSpacing(6)
        self.pubsub_key_input = LineEdit(text="demo_event", placeholder="key")
        form.addRow(self._make_label("common", "label.key"), self.pubsub_key_input)
        self.pubsub_value_input = LineEdit(text="hello", placeholder="value")
        form.addRow(self._make_label("common", "label.value"), self.pubsub_value_input)
        form.addRow("", self._build_pubsub_op_row())
        form.addRow("", self._build_pubsub_manage_row())
        group.setLayout(form)
        return group

    def _build_pubsub_op_row(self) -> QHBoxLayout:
        """构建发布订阅操作行：订阅 / 发布 / 取消订阅"""
        row = QHBoxLayout()
        row.addWidget(self._make_button("btn.subscribe", self._on_subscribe, variant="primary"))
        row.addWidget(self._make_button("btn.publish", self._on_publish))
        row.addWidget(self._make_button("btn.unsubscribe", self._on_unsubscribe))
        return row

    def _build_pubsub_manage_row(self) -> QHBoxLayout:
        """构建发布订阅管理行：查看事件 / 活跃实例"""
        row = QHBoxLayout()
        row.addWidget(self._make_button("btn.show_events", self._on_show_events))
        row.addWidget(self._make_button("btn.active_instance", self._on_get_active_instance))
        row.addStretch()
        return row

    # ------------------------------------------------------------------
    #  结果展示辅助（成功/失败标题模板统一取词）
    # ------------------------------------------------------------------

    def _show_result(self, title_key: str, result: dict,
                     ok_content: Optional[str] = None):
        """统一展示操作结果：标题按语言取词，success 决定成败分支"""
        title = self._tr("tab_data", title_key)
        if result.get("success"):
            content = ok_content if ok_content is not None else result.get("message", "")
            self._display_result(self._tr("common", "result.success", title=title), content)
        else:
            self._display_result(self._tr("common", "result.fail", title=title),
                                 result.get("error", ""), is_error=True)

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_register_plugin(self):
        result = self.data_service.register_demo_plugin()
        self._log(self._tr("tab_data", "log.register", result=result))
        self._show_result("title.register", result)
        Message.info(self._message_parent, str(result))

    def _on_unregister_plugin(self):
        result = self.data_service.unregister_demo_plugin()
        self._log(self._tr("tab_data", "log.unregister", result=result))
        self._show_result("title.unregister", result)
        Message.info(self._message_parent, str(result))

    def _on_write_private(self):
        key = self.private_key_input.text()
        value = self.private_value_input.text()
        result = self.data_service.write_private_data(key, value)
        self._log(self._tr("tab_data", "log.write_private", result=result))
        self._show_result("title.write_private", result, ok_content=f"{key} = {value}")

    def _on_read_private(self):
        key = self.private_key_input.text()
        result = self.data_service.read_private_data(key)
        self._log(self._tr("tab_data", "log.read_private", result=result))
        self._show_result("title.read_private", result,
                          ok_content=f"{key} = {result.get('value')}")

    def _on_write_public(self):
        key = self.public_key_input.text()
        value = self.public_value_input.text()
        result = self.data_service.write_public_data(key, value)
        self._log(self._tr("tab_data", "log.write_public", result=result))
        self._show_result("title.write_public", result, ok_content=f"{key} = {value}")

    def _on_read_public(self):
        key = self.public_key_input.text()
        result = self.data_service.read_public_data(key)
        self._log(self._tr("tab_data", "log.read_public", result=result))
        self._show_result("title.read_public", result,
                          ok_content=f"{key} = {result.get('value')}")

    def _on_get_all_data(self):
        result = self.data_service.get_all_data()
        self._log(self._tr("tab_data", "log.get_all", result=result))
        if result.get("success"):
            content = json.dumps(result, indent=2, ensure_ascii=False)
            self._display_result(self._tr("tab_data", "title.all_data"), content)
        else:
            self._display_result(self._tr("tab_data", "title.get_data_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_save_asset(self):
        result = self.data_service.save_demo_asset()
        self._log(self._tr("tab_data", "log.save_asset", result=result))
        self._show_result("title.save_asset", result, ok_content=self._tr(
            "tab_data", "msg.asset_path", path=result.get("path", "")))

    def _on_load_asset(self):
        result = self.data_service.load_demo_asset()
        self._log(self._tr("tab_data", "log.load_asset", result=result))
        self._show_result("title.load_asset", result, ok_content=self._tr(
            "tab_data", "msg.asset_content", content=result.get("content", "")))

    def _on_subscribe(self):
        result = self.data_service.subscribe_demo(self.pubsub_key_input.text())
        self._log(self._tr("tab_data", "log.subscribe", result=result))
        self._show_result("title.subscribe", result)

    def _on_publish(self):
        key = self.pubsub_key_input.text()
        result = self.data_service.publish_demo(key, self.pubsub_value_input.text())
        self._log(self._tr("tab_data", "log.publish", result=result))
        self._show_result("title.publish", result)

    def _on_unsubscribe(self):
        result = self.data_service.unsubscribe_demo()
        self._log(self._tr("tab_data", "log.unsubscribe", result=result))
        self._show_result("title.unsubscribe", result)

    def _on_show_events(self):
        result = self.data_service.get_subscription_events()
        events = result.get("events", [])
        content = json.dumps(events, indent=2, ensure_ascii=False, default=str)
        self._log(self._tr("tab_data", "log.events_count", count=len(events)))
        self._display_result(self._tr("tab_data", "title.events"), content)

    def _on_get_active_instance(self):
        result = self.data_service.get_active_instance_demo()
        self._log(self._tr("tab_data", "log.active_instance", result=result))
        ok_content = self._tr("tab_data", "msg.active_instance",
                              plugin_type=result.get("plugin_type"),
                              active_instance=result.get("active_instance"))
        if result.get("success"):
            self._display_result(self._tr("tab_data", "title.active_instance"), ok_content)
        else:
            self._display_result(self._tr("tab_data", "title.active_instance_fail"),
                                 result.get("error", ""), is_error=True)
