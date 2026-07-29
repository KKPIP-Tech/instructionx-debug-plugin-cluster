# -*- coding: utf-8 -*-
"""API Demo 插件主控件。

展示如何通过 PluginManager 调用其他插件的 API。
样式全面使用 InstructionX_UIKit 组件（Button/ListWidget/TextArea/Message）
与 T() 令牌，随全局主题自动换肤。
"""

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import T
from InstructionX_UIKit.components import Button, ListWidget, Message, TextArea


class MainWidget(QWidget):
    """API Demo 主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.setObjectName("ApiDemoWidget")
        self._service = service
        self._setup_ui()
        self._refresh_api_list()

    def _setup_ui(self):
        """构建 UI"""
        cfg = self._load_config()
        layout = QVBoxLayout(self)
        self._apply_layout_config(layout, cfg)
        self._add_title(layout)
        self._add_description(layout)
        splitter = self._create_splitter(cfg)
        layout.addWidget(splitter)
        self.api_list.itemClicked.connect(self._on_api_selected)

    def _apply_layout_config(self, layout, cfg):
        ui_cfg = cfg.get("ui", {})
        layout.setContentsMargins(*ui_cfg.get("margins", [16, 16, 16, 16]))
        layout.setSpacing(ui_cfg.get("spacing", 12))

    def _add_title(self, layout):
        """添加标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("API 调用演示")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft)
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _add_description(self, layout):
        desc = QLabel("此插件演示如何通过 PluginManager 调用其他插件的 API 方法。")
        desc.setWordWrap(True)
        layout.addWidget(desc)

    def _create_splitter(self, cfg):
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_panel = self._build_left_panel(cfg)
        right_panel = self._build_right_panel(cfg)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        return splitter

    def _load_config(self) -> dict:
        cfg_path = Path(__file__).parent.parent / "config" / "default.json"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _build_left_panel(self, cfg):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(cfg.get("ui", {}).get("spacing", 12))
        group = self._create_api_group(cfg)
        layout.addWidget(group)
        return panel

    def _create_api_group(self, cfg):
        group = QGroupBox("可用 API 方法")
        layout = QVBoxLayout()
        layout.setSpacing(cfg.get("ui", {}).get("spacing", 12))
        self._setup_api_list(cfg, layout)
        self._setup_buttons(layout)
        group.setLayout(layout)
        return group

    def _setup_api_list(self, cfg, layout):
        self.api_list = ListWidget()
        self.api_list.setSelectionMode(ListWidget.SelectionMode.SingleSelection)
        layout.addWidget(self.api_list)

    def _setup_buttons(self, layout):
        for btn_text, handler in [
            ("刷新 API 列表", self._refresh_api_list),
            ("查看所有插件 API", self._view_all_apis),
            ("查看 Function Tools", self._view_tools)
        ]:
            btn = Button(btn_text, variant="default")
            btn.clicked.connect(handler)
            layout.addWidget(btn)

    def _build_right_panel(self, cfg):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(cfg.get("ui", {}).get("spacing", 12))
        layout.addWidget(self._create_input_group(cfg))
        layout.addLayout(self._create_button_layout(cfg))
        layout.addWidget(self._create_output_group(cfg))
        return panel

    def _create_input_group(self, cfg):
        group = QGroupBox("输入参数")
        layout = QVBoxLayout()
        layout.setSpacing(cfg.get("ui", {}).get("spacing", 12))
        self.input_text = TextArea(placeholder="在此输入要处理的文本...")
        h = cfg.get("ui", {}).get("input_min_height", 80)
        self.input_text.setMinimumHeight(h)
        layout.addWidget(self.input_text)
        group.setLayout(layout)
        return group

    def _create_button_layout(self, cfg):
        layout = QHBoxLayout()
        self.execute_btn = Button("执行 API 调用", variant="primary")
        self.execute_btn.setEnabled(False)
        self.execute_btn.clicked.connect(self._do_execute)
        layout.addWidget(self.execute_btn)
        return layout

    def _create_output_group(self, cfg):
        group = QGroupBox("调用结果")
        layout = QVBoxLayout()
        layout.setSpacing(cfg.get("ui", {}).get("spacing", 12))
        self.output_text = TextArea()
        self.output_text.setReadOnly(True)
        h = cfg.get("ui", {}).get("output_min_height", 100)
        self.output_text.setMinimumHeight(h)
        layout.addWidget(self.output_text)
        group.setLayout(layout)
        return group

    def _on_api_selected(self, item):
        method_name = item.data(Qt.ItemDataRole.UserRole)
        if method_name:
            self.execute_btn.setEnabled(True)
            self.output_text.clear()

    def _refresh_api_list(self):
        self.api_list.clear()
        string_tools_id = self._service.get_target_plugin_id("string-tools")
        if not string_tools_id:
            self.api_list.addItem("未找到字符串工具插件")
            return
        plugin_api = self._service.get_plugin_api(string_tools_id)
        if plugin_api:
            self._populate_api_list(plugin_api.get("methods", []))
        else:
            self.api_list.addItem("字符串工具插件未注册 API")

    def _populate_api_list(self, methods):
        for method_name in methods:
            item = QListWidgetItem(f"{method_name}()")
            item.setData(Qt.ItemDataRole.UserRole, method_name)
            self.api_list.addItem(item)

    def _do_execute(self):
        current_item = self.api_list.currentItem()
        if not current_item:
            Message.warning(self, "请先选择一个 API 方法")
            return
        method_name = current_item.data(Qt.ItemDataRole.UserRole)
        text_input = self.input_text.toPlainText()
        if not text_input:
            Message.warning(self, "请输入文本参数")
            return
        string_tools_id = self._service.get_target_plugin_id("string-tools")
        if not string_tools_id:
            self.output_text.setText("错误: 未找到字符串工具插件")
            return
        self._execute_api_call(string_tools_id, method_name, text_input)

    def _execute_api_call(self, plugin_id, method, text):
        try:
            result = self._service.call_plugin_method(plugin_id, method, text)
            self.output_text.setText(f"调用成功\n\n结果: {result}")
        except ValueError as e:
            self.output_text.setText(f"API 不可用\n\n错误: {str(e)}")
        except RuntimeError as e:
            self.output_text.setText(f"调用失败\n\n错误: {str(e)}")
        except Exception as e:
            self.output_text.setText(f"未知错误\n\n{type(e).__name__}: {str(e)}")

    def _view_all_apis(self):
        all_apis = self._service.get_all_apis()
        info_text = "所有已注册的 API:\n\n"
        for plugin_id, api_info in all_apis.items():
            info_text += self._format_api_info(plugin_id, api_info)
        self.output_text.setText(info_text)

    def _format_api_info(self, plugin_id, api_info):
        return (f"插件: {api_info['plugin_name']} (ID: {plugin_id})\n"
                f"类型: {api_info['plugin_type']}\n"
                f"方法: {', '.join(api_info['methods'])}\n"
                + "-" * 50 + "\n")

    def _view_tools(self):
        tools = self._service.get_all_function_tools()
        info_text = f"Function Tools 定义 (共 {len(tools)} 个):\n\n"
        for tool in tools:
            info_text += self._format_tool(tool)
        self.output_text.setText(info_text)

    def _format_tool(self, tool):
        func = tool["function"]
        info = f"名称: {func['name']}\n描述: {func['description']}\n"
        params = func.get("parameters", {}).get("properties", {})
        if params:
            info += "参数:\n"
            for pname, pinfo in params.items():
                info += f"  - {pname} ({pinfo['type']}): {pinfo['description']}\n"
        return info + "-" * 50 + "\n"
