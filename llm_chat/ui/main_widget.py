# -*- coding: utf-8 -*-
"""LLM Chat 插件主控件（视图层）。

负责全部 UI 构建与事件分发，业务逻辑委托给 Service 实例。
控件全面使用 InstructionX_UIKit 组件（Button/ComboBox/TextArea/
ListWidget/Slider/Message/Dialog），随全局主题自动换肤。
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.components import (
    Button,
    ComboBox,
    Dialog,
    ListWidget,
    Message,
    Slider,
    TextArea,
)
from InstructionX_UIKit.theme import set_property
from utils.logging_tools import LoggerManager, get_name

from .chat_worker import ChatWorker

# UI 文案常量（避免在下拉框匹配中散落魔法字符串）
_TEXT_NO_PROVIDER = "无可用 Provider"
_TEXT_NO_MODEL = "无可用模型"
_TEXT_MAX_TOKENS_UNLIMITED = "无限制"
_MAX_TOKENS_OPTIONS = ["256", "512", "1024", "2048", "4096", _TEXT_MAX_TOKENS_UNLIMITED]
# 温度滑块为整数 0-100，显示时换算为 0.0-1.0
_TEMP_SLIDER_SCALE = 100
# 历史条目预览截断长度
_HISTORY_PREVIEW_LEN = 50


class MainWidget(QWidget):
    """LLM Chat 插件主控件"""

    _logger = LoggerManager()

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self.service = service
        self._chat_worker = None
        self._images = []
        self._setup_ui()
        self._init_providers()

    # ---- UI 子控件创建方法 ----

    def _build_provider_combo(self, layout):
        """构建 Provider 下拉框"""
        layout.addWidget(QLabel("供应商:"))
        self.provider_combo = ComboBox()
        self.provider_combo.currentTextChanged.connect(
            self._on_provider_changed
        )
        layout.addWidget(self.provider_combo)

    def _build_model_combo(self, layout):
        """构建 Model 下拉框"""
        layout.addWidget(QLabel("模型:"))
        self.model_combo = ComboBox()
        self.model_combo.setMinimumWidth(200)
        layout.addWidget(self.model_combo)

    def _build_config_buttons(self, layout):
        """构建配置区按钮"""
        refresh_btn = Button("刷新模型")
        refresh_btn.clicked.connect(self._refresh_models)
        layout.addWidget(refresh_btn)

        validate_btn = Button("验证配置")
        validate_btn.clicked.connect(self._validate_provider)
        layout.addWidget(validate_btn)

    def _create_config_area(self) -> QGroupBox:
        """创建顶部配置区域（Provider + Model 选择）"""
        group = QGroupBox("配置")
        layout = QHBoxLayout()

        self._build_provider_combo(layout)
        self._build_model_combo(layout)
        self._build_config_buttons(layout)

        group.setLayout(layout)
        return group

    def _create_temp_control(self, layout):
        """创建 Temperature 滑块控件"""
        layout.addWidget(QLabel("Temperature:"))
        self.temp_slider = Slider(minimum=0, maximum=_TEMP_SLIDER_SCALE, value=70)
        self.temp_slider.set_ticks(10)
        self.temp_slider.setToolTip("控制输出的随机性，值越低越确定")
        layout.addWidget(self.temp_slider)
        self.temp_label = QLabel("0.7")
        layout.addWidget(self.temp_label)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_label.setText(f"{v / _TEMP_SLIDER_SCALE:.1f}")
        )

    def _create_max_tokens_control(self, layout):
        """创建 Max Tokens 下拉框控件"""
        layout.addWidget(QLabel("Max Tokens:"))
        self.max_tokens_combo = ComboBox(_MAX_TOKENS_OPTIONS)
        self.max_tokens_combo.setCurrentIndex(1)
        layout.addWidget(self.max_tokens_combo)

    def _create_image_controls(self, layout):
        """创建图片相关控件"""
        self.image_btn = Button("添加图片")
        self.image_btn.clicked.connect(self._add_image)
        layout.addWidget(self.image_btn)

        self.images_list = ListWidget()
        self.images_list.setMaximumHeight(40)
        layout.addWidget(self.images_list)

        clear_img_btn = Button("清除图片")
        clear_img_btn.clicked.connect(self._clear_images)
        layout.addWidget(clear_img_btn)

    def _create_params_area(self) -> QGroupBox:
        """创建参数设置区域（Temperature、MaxTokens、图片）"""
        group = QGroupBox("参数")
        layout = QHBoxLayout()

        self._create_temp_control(layout)
        self._create_max_tokens_control(layout)
        self._create_image_controls(layout)

        group.setLayout(layout)
        return group

    def _create_history_area(self) -> QGroupBox:
        """创建对话历史区域"""
        group = QGroupBox("对话历史")
        layout = QVBoxLayout()

        self.history_list = ListWidget()
        self.history_list.setMaximumHeight(100)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self.history_list)

        clear_history_btn = Button("清除对话历史")
        clear_history_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_history_btn)

        group.setLayout(layout)
        return group

    def _create_output_area(self):
        """创建输出区域"""
        self.output_edit = TextArea(placeholder="AI 回复将显示在这里...")
        self.output_edit.setReadOnly(True)
        return self.output_edit

    def _create_input_controls(self):
        """创建输入控件"""
        self.input_edit = TextArea(
            placeholder="输入您的问题... (按 Enter 发送)"
        )
        self.input_edit.setMaximumHeight(80)
        self.input_edit.keyPressEvent = self._handle_input_keypress

        self.send_btn = Button("发送", variant="primary")
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setMinimumWidth(80)

        self.stop_btn = Button("停止", variant="danger")
        self.stop_btn.clicked.connect(self._stop_stream)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumWidth(80)

    def _create_chat_area(self) -> QGroupBox:
        """创建聊天区域（输入 + 输出）"""
        group = QGroupBox("对话")
        layout = QVBoxLayout()

        layout.addWidget(self._create_output_area())

        input_layout = QHBoxLayout()
        self._create_input_controls()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)
        input_layout.addWidget(self.stop_btn)

        layout.addLayout(input_layout)
        group.setLayout(layout)
        return group

    # ---- 主布局构建 ----

    def _setup_ui(self):
        """构建插件 UI 布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._create_scroll_area())

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(self._create_content_panel())
        return scroll_area

    def _create_conversation_section(self) -> QSplitter:
        """创建对话区域（历史 + 聊天）"""
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(self._create_history_area())
        splitter.addWidget(self._create_chat_area())
        return splitter

    def _create_content_panel(self) -> QWidget:
        """创建内容面板"""
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._create_config_area())
        layout.addWidget(self._create_params_area())
        layout.addWidget(self._create_conversation_section())

        self.status_label = QLabel("就绪")
        set_property(self.status_label, "role", "hint")
        layout.addWidget(self.status_label)

        return content

    # ---- Provider / Model ----

    def _init_providers(self):
        """填充 Provider 下拉框（创建控件时执行一次，后续用「刷新模型」手动刷新）"""
        self.provider_combo.clear()
        providers = self.service.get_providers()
        if not providers:
            all_providers = self.service.get_all_providers()
            providers = list(all_providers.keys())
        if not providers:
            self.provider_combo.addItem(_TEXT_NO_PROVIDER)
            Message.warning(
                self,
                "未找到可用的 LLM Provider。\n\n"
                "请在「编辑 > LLM设置」中配置并启用至少一个 Provider。"
            )
            return
        last_provider = self.service.load_preference("last_provider", "")
        self.provider_combo.addItems(providers)
        if last_provider and last_provider in providers:
            self.provider_combo.setCurrentText(last_provider)

    def _on_provider_changed(self, provider: str):
        """Provider 切换：刷新模型列表并记住选择"""
        if provider and provider != _TEXT_NO_PROVIDER:
            self._refresh_models()
            self.service.save_preference("last_provider", provider)

    def _refresh_models(self):
        """刷新当前 Provider 的模型下拉框"""
        provider = self.provider_combo.currentText()
        if not provider or provider == _TEXT_NO_PROVIDER:
            return

        self._logger.debug(get_name(), f"Refreshing: {provider}")
        self.model_combo.clear()
        models = self.service.get_models(provider)
        self._logger.debug(get_name(), f"Got {len(models)} models")

        if not models:
            self.model_combo.addItem(_TEXT_NO_MODEL)
            return

        chat_models = self._filter_chat_models(models)
        self._populate_model_combo(chat_models)
        self._restore_last_model(provider)

    def _filter_chat_models(self, models):
        """过滤出支持对话的模型"""
        chat_models = [m for m in models if m.support_chat]
        if not chat_models:
            chat_models = models
        self._logger.debug(
            get_name(),
            f"Chat models: {[m.id for m in chat_models[:5]]}"
        )
        return chat_models

    def _populate_model_combo(self, models):
        """填充模型下拉框"""
        for model in models:
            self.model_combo.addItem(model.id, model)

    def _restore_last_model(self, provider: str):
        """恢复该 Provider 上次使用的模型"""
        last_model = self.service.load_preference(
            f"last_model_{provider}", ""
        )
        if last_model:
            index = self.model_combo.findText(last_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

    def _validate_provider(self):
        """验证当前 Provider 配置并告知结果"""
        provider = self.provider_combo.currentText()
        if not provider or provider == _TEXT_NO_PROVIDER:
            return

        result = self.service.validate_provider(provider)
        if result["valid"]:
            vision = "支持" if result["supports_vision"] else "不支持"
            Message.info(
                self,
                f"Provider「{provider}」配置有效。\n"
                f"Vision 多模态: {vision}"
            )
            self.image_btn.setEnabled(result["supports_vision"])
        else:
            Message.error(
                self,
                f"Provider「{provider}」配置无效:\n\n"
                f"{result['message']}\n\n"
                "请在「编辑 > LLM设置」中配置。"
            )

    # ---- 图片 ----

    def _add_image(self):
        """选择图片并转为 base64 加入待发送列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if not files:
            return

        for file_path in files:
            base64_data = self.service.load_image_as_base64(file_path)
            if base64_data:
                self._images.append(base64_data)
                self.images_list.addItem(Path(file_path).name)
            else:
                Message.warning(self, f"无法读取图片: {file_path}")

    def _clear_images(self):
        """清空待发送图片"""
        self._images.clear()
        self.images_list.clear()

    # ---- 消息发送 ----

    def _check_send_prerequisites(self):
        """检查发送消息的前置条件，返回错误消息或 None"""
        if self._chat_worker and self._chat_worker.isRunning():
            return "正在生成中，请稍候..."
        message = self.input_edit.toPlainText().strip()
        if not message:
            return "请输入消息"
        provider = self.provider_combo.currentText()
        if not provider or provider == _TEXT_NO_PROVIDER:
            return "请选择有效的 Provider"
        return None

    def _send_message(self):
        """发送按钮/回车入口：前置检查 + 配置验证后发送"""
        err = self._check_send_prerequisites()
        if err:
            Message.info(self, err)
            return

        message = self.input_edit.toPlainText().strip()
        provider = self.provider_combo.currentText()

        self._logger.debug(get_name(), f"Provider: {provider}")
        self._logger.debug(
            get_name(),
            f"Model: {self.model_combo.currentText()}"
        )

        validation = self.service.validate_provider(provider)
        if not validation["valid"]:
            Message.error(
                self,
                f"Provider「{provider}」配置无效:\n\n"
                f"{validation['message']}\n\n"
                "请在「编辑 > LLM设置」中配置 API Key。"
            )
            return

        self._do_send_message(message, provider)

    def _extract_send_params(self):
        """提取发送参数"""
        model = self.model_combo.currentText()
        if not model or model == _TEXT_NO_MODEL:
            model = None
        temperature = self.temp_slider.value() / _TEMP_SLIDER_SCALE
        max_tokens_str = self.max_tokens_combo.currentText()
        max_tokens = (
            None if max_tokens_str == _TEXT_MAX_TOKENS_UNLIMITED
            else int(max_tokens_str)
        )
        return model, temperature, max_tokens

    def _build_user_message(self, message: str) -> dict:
        """构建用户消息"""
        user_msg = {"role": "user", "content": message}
        if self._images:
            user_msg["images"] = self._images
        return user_msg

    def _do_send_message(self, message: str, provider: str):
        """实际执行消息发送"""
        model, temperature, max_tokens = self._extract_send_params()
        history = self._collect_history()
        self._update_ui_before_send()

        user_msg = self._build_user_message(message)
        history.append(user_msg)

        self._chat_worker = ChatWorker(
            self.service, message, provider, model,
            temperature, max_tokens,
            self._images if self._images else None,
            history[:-1],
        )
        self._chat_worker.chunk_received.connect(self._on_chunk_received)
        self._chat_worker.finished.connect(self._on_finished)
        self._chat_worker.start()

    def _collect_history(self) -> list:
        """从历史列表收集消息"""
        history = []
        for i in range(self.history_list.count()):
            item = self.history_list.item(i)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    history.append(data)
        return history

    def _update_ui_before_send(self):
        """发送前更新 UI 状态"""
        self.send_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.input_edit.setEnabled(False)
        self.output_edit.clear()
        self.status_label.setText("正在生成...")

    def _on_chunk_received(self, chunk: str):
        """流式增量：追加到输出区域（经 Qt 信号已在 UI 线程执行）"""
        try:
            cursor = self.output_edit.textCursor()
            if cursor.position() >= 0:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(chunk)
                self.output_edit.setTextCursor(cursor)
                self.output_edit.ensureCursorVisible()
        except Exception as e:
            self._logger.warning(get_name(), f"追加流式内容失败: {e}")

    def _on_finished(self, result: dict):
        """流式结束：恢复输入状态并分发成功/失败处理"""
        self.send_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.input_edit.setEnabled(True)
        self.input_edit.setFocus()

        if result.get("success"):
            self._handle_success_result(result)
        else:
            self._handle_error_result(result)

    def _handle_success_result(self, result: dict):
        """处理成功结果"""
        history = self._collect_history()

        user_msg = {
            "role": "user",
            "content": self.input_edit.toPlainText().strip()
        }
        if self._images:
            user_msg["images"] = self._images.copy()
        history.append(user_msg)

        assistant_msg = {
            "role": "assistant",
            "content": result.get("full_response", ""),
        }
        history.append(assistant_msg)

        self.history_list.addItem(
            f"你: {user_msg['content'][:_HISTORY_PREVIEW_LEN]}..."
        )
        self.history_list.addItem(
            f"AI: {assistant_msg['content'][:_HISTORY_PREVIEW_LEN]}..."
        )
        self.service.save_chat_history(history)
        self._clear_images()
        self.input_edit.clear()
        self.status_label.setText(
            f"完成 (使用模型: {result.get('model', 'unknown')})"
        )

    def _handle_error_result(self, result: dict):
        """处理错误结果"""
        error = result.get("error", "未知错误")
        error_type = result.get("error_type", "unknown")
        self.output_edit.append("\n\n--- 错误 ---\n")
        self.output_edit.append(error)
        self.status_label.setText(f"错误: {error_type}")

        if error_type == "authentication":
            Message.error(
                self,
                f"API 认证失败。\n\n{error}\n\n"
                "请在「编辑 > LLM设置」中检查 API Key。"
            )
        elif error_type == "rate_limit":
            Message.warning(self, f"请求超限: {error}")
        elif error_type == "configuration":
            Message.error(self, f"配置错误: {error}")

    def _stop_stream(self):
        """停止当前流式生成"""
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.cancel()
            self.status_label.setText("已停止")
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.input_edit.setEnabled(True)

    # ---- 历史记录 ----

    def _on_history_item_clicked(self, item):
        """点击历史条目：弹出对话框查看完整内容（长文本需手动关闭，不用轻提示）"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        role = data.get("role", "")
        content = data.get("content", "")
        title_map = {"user": "用户消息", "assistant": "AI 回复"}
        title = title_map.get(role, "消息")
        Dialog.info(self, title, content)

    def _clear_history(self):
        """清除对话历史（确认后执行）"""
        Dialog.confirm(
            self, "确认", "确定要清除所有对话历史吗？",
            on_result=self._on_clear_history_confirmed,
        )

    def _on_clear_history_confirmed(self, ok: bool):
        """清除历史确认回调"""
        if not ok:
            return
        self.history_list.clear()
        self.service.save_chat_history([])

    # ---- 输入框按键 ----

    def _handle_input_keypress(self, event):
        """输入框按键处理：Enter 发送，Shift+Enter 换行"""
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            self._send_message()
        elif (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self.input_edit.insertPlainText("\n")
        else:
            QTextEdit.keyPressEvent(self.input_edit, event)
