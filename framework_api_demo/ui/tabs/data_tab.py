# -*- coding: utf-8 -*-
"""DataProvider 演示 Tab。

演示插件注册、Private/Public 数据读写、数据查询与资源管理。
槽函数仅取输入、调用 DataDemoService、显示结果，业务逻辑在服务层。
"""

import json
from typing import Callable

from PySide6.QtWidgets import QFormLayout, QGroupBox, QHBoxLayout, QVBoxLayout, QScrollArea

from InstructionX_UIKit.components import Button, LineEdit, Message

from .base_tab import BaseTab


class DataTab(BaseTab):
    """DataProvider 演示 Tab

    职责：构建 DataProvider 演示页的控件布局并处理其事件，
    通过注入的结果/日志回调与主控件公共面板交互。
    """

    def __init__(self, data_service, display_result: Callable, append_log: Callable):
        """初始化 DataProvider 演示 Tab

        参数:
            data_service: DataDemoService 实例（DataProvider 演示）
            display_result: 结果显示回调
            append_log: 日志追加回调
        """
        super().__init__(display_result, append_log)
        self.data_service = data_service

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
        layout.addStretch()
        return scroll

    def _build_data_register_controls(self) -> QGroupBox:
        group = QGroupBox("插件注册")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.register_plugin_btn = Button("注册演示插件", variant="primary")
        self.register_plugin_btn.clicked.connect(self._on_register_plugin)
        row.addWidget(self.register_plugin_btn)

        self.unregister_plugin_btn = Button("注销演示插件")
        self.unregister_plugin_btn.clicked.connect(self._on_unregister_plugin)
        row.addWidget(self.unregister_plugin_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    def _build_data_private_group(self) -> QGroupBox:
        group = QGroupBox("Private 数据操作")
        form = QFormLayout()
        form.setSpacing(6)

        self.private_key_input = LineEdit(text="test_key", placeholder="key")
        form.addRow("键:", self.private_key_input)

        self.private_value_input = LineEdit(text="test_value", placeholder="value")
        form.addRow("值:", self.private_value_input)

        row = QHBoxLayout()
        btn_write = Button("写入", variant="primary")
        btn_write.clicked.connect(self._on_write_private)
        row.addWidget(btn_write)

        btn_read = Button("读取")
        btn_read.clicked.connect(self._on_read_private)
        row.addWidget(btn_read)
        form.addRow("", row)

        group.setLayout(form)
        return group

    def _build_data_public_group(self) -> QGroupBox:
        group = QGroupBox("Public 数据操作")
        form = QFormLayout()
        form.setSpacing(6)

        self.public_key_input = LineEdit(text="shared_key", placeholder="key")
        form.addRow("键:", self.public_key_input)

        self.public_value_input = LineEdit(text="shared_value", placeholder="value")
        form.addRow("值:", self.public_value_input)

        row = QHBoxLayout()
        btn_write = Button("写入", variant="primary")
        btn_write.clicked.connect(self._on_write_public)
        row.addWidget(btn_write)

        btn_read = Button("读取")
        btn_read.clicked.connect(self._on_read_public)
        row.addWidget(btn_read)
        form.addRow("", row)

        group.setLayout(form)
        return group

    def _build_data_query_controls(self) -> QGroupBox:
        group = QGroupBox("数据查询")
        layout = QVBoxLayout()

        self.get_all_data_btn = Button("获取所有数据", variant="primary")
        self.get_all_data_btn.clicked.connect(self._on_get_all_data)
        layout.addWidget(self.get_all_data_btn)

        group.setLayout(layout)
        return group

    def _build_data_assets_section(self) -> QGroupBox:
        group = QGroupBox("资源管理")
        row = QHBoxLayout()
        row.setSpacing(8)

        self.save_asset_btn = Button("保存资源", variant="primary")
        self.save_asset_btn.clicked.connect(self._on_save_asset)
        row.addWidget(self.save_asset_btn)

        self.load_asset_btn = Button("加载资源")
        self.load_asset_btn.clicked.connect(self._on_load_asset)
        row.addWidget(self.load_asset_btn)

        row.addStretch()
        group.setLayout(row)
        return group

    # ------------------------------------------------------------------
    #  事件处理
    # ------------------------------------------------------------------

    def _on_register_plugin(self):
        result = self.data_service.register_demo_plugin()
        self._log(f"注册插件: {result}")
        if result.get("success"):
            self._display_result("注册插件成功", result.get("message", ""))
        else:
            self._display_result("注册插件失败", result.get("error", ""), is_error=True)
        Message.info(self._message_parent, str(result))

    def _on_unregister_plugin(self):
        result = self.data_service.unregister_demo_plugin()
        self._log(f"注销插件: {result}")
        if result.get("success"):
            self._display_result("注销插件成功", result.get("message", ""))
        else:
            self._display_result("注销插件失败", result.get("error", ""), is_error=True)
        Message.info(self._message_parent, str(result))

    def _on_write_private(self):
        key = self.private_key_input.text()
        value = self.private_value_input.text()
        result = self.data_service.write_private_data(key, value)
        self._log(f"写入Private: {result}")
        if result.get("success"):
            self._display_result("写入 Private 成功", f"{key} = {value}")
        else:
            self._display_result("写入 Private 失败", result.get("error", ""), is_error=True)

    def _on_read_private(self):
        key = self.private_key_input.text()
        result = self.data_service.read_private_data(key)
        self._log(f"读取Private: {result}")
        if result.get("success"):
            self._display_result("读取 Private 成功", f"{key} = {result.get('value')}")
        else:
            self._display_result("读取 Private 失败", result.get("error", ""), is_error=True)

    def _on_write_public(self):
        key = self.public_key_input.text()
        value = self.public_value_input.text()
        result = self.data_service.write_public_data(key, value)
        self._log(f"写入Public: {result}")
        if result.get("success"):
            self._display_result("写入 Public 成功", f"{key} = {value}")
        else:
            self._display_result("写入 Public 失败", result.get("error", ""), is_error=True)

    def _on_read_public(self):
        key = self.public_key_input.text()
        result = self.data_service.read_public_data(key)
        self._log(f"读取Public: {result}")
        if result.get("success"):
            self._display_result("读取 Public 成功", f"{key} = {result.get('value')}")
        else:
            self._display_result("读取 Public 失败", result.get("error", ""), is_error=True)

    def _on_get_all_data(self):
        result = self.data_service.get_all_data()
        self._log(f"获取所有数据: {result}")
        if result.get("success"):
            content = json.dumps(result, indent=2, ensure_ascii=False)
            self._display_result("所有数据", content)
        else:
            self._display_result("获取数据失败", result.get("error", ""), is_error=True)

    def _on_save_asset(self):
        result = self.data_service.save_demo_asset()
        self._log(f"保存资源: {result}")
        if result.get("success"):
            self._display_result("保存资源成功", f"路径: {result.get('path', '')}")
        else:
            self._display_result("保存资源失败", result.get("error", ""), is_error=True)

    def _on_load_asset(self):
        result = self.data_service.load_demo_asset()
        self._log(f"加载资源: {result}")
        if result.get("success"):
            self._display_result("加载资源成功", f"内容:\n{result.get('content', '')}")
        else:
            self._display_result("加载资源失败", result.get("error", ""), is_error=True)
