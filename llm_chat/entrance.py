"""
LLM Chat 插件入口 - UI 界面
"""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit,
    QComboBox, QGroupBox, QFileDialog,
    QMessageBox, QScrollArea, QFrame,
    QSplitter, QListWidget,
    QSlider
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QTextCursor

from core.plugin.plugin_interface import IPlugin
from core.data.data_provider import DataProvider, DataProviderError
from utils.style_qss.registry import QssRegistry
from utils.logging_tools import LoggerManager, get_name


def _get_service(plugin_id, data_provider):
    from .service import Service
    return Service(plugin_id, data_provider)


class ChatWorker(QThread):
    """聊天工作线程"""
    finished = Signal(dict)
    chunk_received = Signal(str)

    def __init__(self, service, message, provider, model,
                 temperature, max_tokens, images, history):
        super().__init__()
        self.service = service
        self.message = message
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.images = images
        self.history = history
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def _do_stream(self):
        for result in self.service.stream_send_message(
            self.message, self.provider, self.model, self.temperature,
            self.max_tokens, self.images, self.history,
        ):
            if self._is_cancelled:
                break
            if "error" in result and result.get("done"):
                self.finished.emit(result)
                break
            if not result.get("done"):
                self.chunk_received.emit(result.get("chunk", ""))
            else:
                self.finished.emit({
                    "success": True,
                    "full_response": result.get("full_response", ""),
                    "model": result.get("model", ""),
                })

    def run(self):
        if self._is_cancelled:
            return
        try:
            self._do_stream()
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})


class LLMChatPlugin(IPlugin):
    """LLM Chat 插件"""

    _logger = LoggerManager()

    @property
    def plugin_name(self) -> str:
        return "LLM\nChat"

    def get_widget(self, parent=None, data_provider=None):
        from utils.style_qss import get_style_qss
        current_theme = get_style_qss().theme()
        if getattr(self, '_cached_theme', None) != current_theme:
            self._cached_theme = current_theme
            self._cached_widget = None
            self._cached_parent = None
        return super().get_widget(parent, data_provider)

    def on_plugin_loaded(self):
        self._logger.info(get_name(), f"插件已加载: {self.plugin_name}")

    # ---- QSS 样式加载与卸载 ----

    def _load_plugin_style(self, widget: QWidget):
        """加载插件目录下的 style/*.qss，支持 {variable} 变量替换"""
        style_dir = Path(__file__).parent / "style"
        if not style_dir.exists():
            return

        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))

        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            widget.setStyleSheet(self._qss_content)

    # ---- 样式状态类 ----

    def _set_status_class(self, status_class: str):
        """设置状态标签的语义化样式类并刷新"""
        self.status_label.setProperty("class", status_class)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    # ---- UI 子控件创建方法 ----

    def _build_provider_combo(self, layout):
        """构建 Provider 下拉框"""
        layout.addWidget(QLabel("供应商:"))
        self.provider_combo = QComboBox()
        self.provider_combo.currentTextChanged.connect(
            self._on_provider_changed
        )
        layout.addWidget(self.provider_combo)

    def _build_model_combo(self, layout):
        """构建 Model 下拉框"""
        layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(200)
        layout.addWidget(self.model_combo)

    def _build_config_buttons(self, layout):
        """构建配置区按钮"""
        refresh_btn = QPushButton("刷新模型")
        refresh_btn.clicked.connect(self._refresh_models)
        layout.addWidget(refresh_btn)

        validate_btn = QPushButton("验证配置")
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
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(0, 100)
        self.temp_slider.setValue(70)
        self.temp_slider.setTickPosition(
            QSlider.TickPosition.TicksBelow
        )
        self.temp_slider.setTickInterval(10)
        self.temp_slider.setToolTip("控制输出的随机性，值越低越确定")
        layout.addWidget(self.temp_slider)
        self.temp_label = QLabel("0.7")
        layout.addWidget(self.temp_label)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_label.setText(f"{v / 100:.1f}")
        )

    def _create_max_tokens_control(self, layout):
        """创建 Max Tokens 下拉框控件"""
        layout.addWidget(QLabel("Max Tokens:"))
        self.max_tokens_combo = QComboBox()
        self.max_tokens_combo.addItems(
            ["256", "512", "1024", "2048", "4096", "无限制"]
        )
        self.max_tokens_combo.setCurrentIndex(1)
        layout.addWidget(self.max_tokens_combo)

    def _create_image_controls(self, layout):
        """创建图片相关控件"""
        self.image_btn = QPushButton("添加图片")
        self.image_btn.clicked.connect(self._add_image)
        layout.addWidget(self.image_btn)

        self.images_list = QListWidget()
        self.images_list.setMaximumHeight(40)
        layout.addWidget(self.images_list)

        clear_img_btn = QPushButton("清除图片")
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

        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(100)
        self.history_list.itemClicked.connect(self._on_history_item_clicked)
        layout.addWidget(self.history_list)

        clear_history_btn = QPushButton("清除对话历史")
        clear_history_btn.clicked.connect(self._clear_history)
        layout.addWidget(clear_history_btn)

        group.setLayout(layout)
        return group

    def _create_output_area(self):
        """创建输出区域"""
        self.output_edit = QTextEdit()
        self.output_edit.setReadOnly(True)
        self.output_edit.setPlaceholderText("AI 回复将显示在这里...")
        return self.output_edit

    def _create_input_controls(self):
        """创建输入控件"""
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText(
            "输入您的问题... (按 Enter 发送)"
        )
        self.input_edit.setMaximumHeight(80)
        self.input_edit.keyPressEvent = self._handle_input_keypress

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setMinimumWidth(80)

        self.stop_btn = QPushButton("停止")
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

    # ---- 主控件创建 ----

    def _setup_plugin(self, dp, data_provider, plugin_id):
        """初始化插件：注册、创建服务实例"""
        try:
            dp.register_plugin(plugin_id, "LLMChat")
            dp.set_active_instance(plugin_id)
        except DataProviderError:
            pass

        self.service = _get_service(plugin_id, dp)

        if data_provider:
            try:
                data_provider.register_plugin(plugin_id, "LLMChat")
                data_provider.set_active_instance(plugin_id)
            except DataProviderError:
                pass

    def _create_root_widget(self, parent) -> QWidget:
        """创建根控件并加载样式"""
        widget = QWidget(parent)
        widget.setObjectName("LLMChatWidget")
        self._load_plugin_style(widget)
        def _on_destroyed(w=widget):
            try:
                w.setStyleSheet("")
            except RuntimeError:
                pass
        widget.destroyed.connect(_on_destroyed)
        return widget

    def _build_layout(self, widget) -> QWidget:
        """构建插件 UI 布局"""
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(self._create_scroll_area())
        return widget

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
        self.status_label.setProperty("class", "status-info")
        layout.addWidget(self.status_label)

        return content

    def _create_widget(self, parent=None, data_provider=None) -> QWidget:
        dp = DataProvider()

        if not self.plugin_id:
            self._plugin_id = "llm-chat-default"
        actual_plugin_id = self.plugin_id or "llm-chat-default"

        self._setup_plugin(dp, data_provider, actual_plugin_id)
        widget = self._build_layout(
            self._create_root_widget(parent)
        )
        self.widget = widget
        self._connect_global_signals()
        self._load_preferences()
        self._init_providers()
        self._chat_worker = None
        self._images = []

        return widget

    def _connect_global_signals(self):
        """连接主窗口全局信号"""
        main_window = self._find_main_window()
        if main_window and hasattr(main_window, 'llm_provider_changed'):
            main_window.llm_provider_changed.connect(
                self._on_global_llm_changed
            )

    def _find_main_window(self):
        """向上查找 MainWindow"""
        parent = self.widget.parent()
        while parent:
            try:
                from ui.main_window import InstructionXMainWindow
                if isinstance(parent, InstructionXMainWindow):
                    return parent
            except ImportError:
                pass
            parent = parent.parent()
        return None

    def _on_global_llm_changed(self, provider: str, model: str):
        idx = self.provider_combo.findText(provider)
        if idx >= 0 and idx != self.provider_combo.currentIndex():
            self.provider_combo.setCurrentIndex(idx)
        if model:
            idx = self.model_combo.findText(model)
            if idx >= 0 and idx != self.model_combo.currentIndex():
                self.model_combo.setCurrentIndex(idx)
        self.service.save_preference("last_provider", provider)

    def _init_providers(self):
        self.provider_combo.clear()
        providers = self.service.get_providers()
        if not providers:
            all_providers = self.service.get_all_providers()
            providers = list(all_providers.keys())
        if not providers:
            self.provider_combo.addItem("无可用 Provider")
            QMessageBox.warning(
                None, "警告",
                "未找到可用的 LLM Provider。\n\n"
                "请在「编辑 > LLM设置」中配置并启用至少一个 Provider。"
            )
            return
        last_provider = self.service.load_preference("last_provider", "")
        if last_provider and last_provider in providers:
            self.provider_combo.addItems(providers)
            self.provider_combo.setCurrentText(last_provider)
        else:
            self.provider_combo.addItems(providers)

    def _on_provider_changed(self, provider: str):
        if provider and provider != "无可用 Provider":
            self._refresh_models()
            self.service.save_preference("last_provider", provider)

    def _refresh_models(self):
        provider = self.provider_combo.currentText()
        if not provider or provider == "无可用 Provider":
            return

        self._logger.debug(get_name(), f"Refreshing: {provider}")
        self.model_combo.clear()
        models = self.service.get_models(provider)
        self._logger.debug(get_name(), f"Got {len(models)} models")

        if not models:
            self.model_combo.addItem("无可用模型")
            return

        chat_models = self._filter_chat_models(models)
        self._populate_model_combo(chat_models)
        self._restore_last_model(provider)

    def _filter_chat_models(self, models):
        chat_models = [m for m in models if m.support_chat]
        if not chat_models:
            chat_models = models
        self._logger.debug(
            get_name(),
            f"Chat models: {[m.id for m in chat_models[:5]]}"
        )
        return chat_models

    def _populate_model_combo(self, models):
        for model in models:
            self.model_combo.addItem(model.id, model)

    def _restore_last_model(self, provider: str):
        last_model = self.service.load_preference(
            f"last_model_{provider}", ""
        )
        if last_model:
            index = self.model_combo.findText(last_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)

    def _validate_provider(self):
        provider = self.provider_combo.currentText()
        if not provider or provider == "无可用 Provider":
            return

        result = self.service.validate_provider(provider)
        if result["valid"]:
            vision = "支持" if result["supports_vision"] else "不支持"
            QMessageBox.information(
                None, "验证成功",
                f"Provider「{provider}」配置有效。\n"
                f"Vision 多模态: {vision}"
            )
            self.image_btn.setEnabled(result["supports_vision"])
        else:
            QMessageBox.critical(
                None, "验证失败",
                f"Provider「{provider}」配置无效:\n\n"
                f"{result['message']}\n\n"
                "请在「编辑 > LLM设置」中配置。"
            )

    def _add_image(self):
        files, _ = QFileDialog.getOpenFileNames(
            None, "选择图片", "",
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
                QMessageBox.warning(
                    None, "警告",
                    f"无法读取图片: {file_path}"
                )

    def _clear_images(self):
        self._images.clear()
        self.images_list.clear()

    def _check_send_prerequisites(self):
        """检查发送消息的前置条件，返回错误消息或 None"""
        if self._chat_worker and self._chat_worker.isRunning():
            return "正在生成中，请稍候..."
        message = self.input_edit.toPlainText().strip()
        if not message:
            return "请输入消息"
        provider = self.provider_combo.currentText()
        if not provider or provider == "无可用 Provider":
            return "请选择有效的 Provider"
        return None

    def _send_message(self):
        err = self._check_send_prerequisites()
        if err:
            QMessageBox.information(None, "提示", err)
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
            QMessageBox.critical(
                None, "配置无效",
                f"Provider「{provider}」配置无效:\n\n"
                f"{validation['message']}\n\n"
                "请在「编辑 > LLM设置」中配置 API Key。"
            )
            return

        self._do_send_message(message, provider)

    def _extract_send_params(self):
        """提取发送参数"""
        model = self.model_combo.currentText()
        if not model or model == "无可用模型":
            model = None
        temperature = self.temp_slider.value() / 100
        max_tokens_str = self.max_tokens_combo.currentText()
        max_tokens = (
            None if max_tokens_str == "无限制"
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
        self._set_status_class("status-info")

    def _on_chunk_received(self, chunk: str):
        try:
            cursor = self.output_edit.textCursor()
            if cursor.position() >= 0:
                cursor.movePosition(QTextCursor.MoveOperation.End)
                cursor.insertText(chunk)
                self.output_edit.setTextCursor(cursor)
                self.output_edit.ensureCursorVisible()
        except Exception:
            pass

    def _on_finished(self, result: dict):
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
            f"你: {user_msg['content'][:50]}..."
        )
        self.history_list.addItem(
            f"AI: {assistant_msg['content'][:50]}..."
        )
        self.service.save_chat_history(history)
        self._clear_images()
        self.input_edit.clear()
        self.status_label.setText(
            f"完成 (使用模型: {result.get('model', 'unknown')})"
        )
        self._set_status_class("status-success")

    def _handle_error_result(self, result: dict):
        """处理错误结果"""
        error = result.get("error", "未知错误")
        error_type = result.get("error_type", "unknown")
        self.output_edit.append("\n\n--- 错误 ---\n")
        self.output_edit.append(error)
        self.status_label.setText(f"错误: {error_type}")
        self._set_status_class("status-error")

        if error_type == "authentication":
            QMessageBox.critical(
                None, "认证失败",
                f"API 认证失败。\n\n{error}\n\n"
                "请在「编辑 > LLM设置」中检查 API Key。"
            )
        elif error_type == "rate_limit":
            QMessageBox.warning(None, "请求超限", error)
        elif error_type == "configuration":
            QMessageBox.critical(None, "配置错误", error)

    def _stop_stream(self):
        if self._chat_worker and self._chat_worker.isRunning():
            self._chat_worker.cancel()
            self.status_label.setText("已停止")
            self._set_status_class("status-warning")
            self.send_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.input_edit.setEnabled(True)

    def _on_history_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        role = data.get("role", "")
        content = data.get("content", "")
        title_map = {"user": "用户消息", "assistant": "AI 回复"}
        title = title_map.get(role, "消息")
        QMessageBox.information(None, title, content)

    def _clear_history(self):
        reply = QMessageBox.question(
            None, "确认", "确定要清除所有对话历史吗？",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.history_list.clear()
            self.service.save_chat_history([])

    def _handle_input_keypress(self, event):
        if event.key() == Qt.Key.Key_Return and not event.modifiers():
            self._send_message()
        elif (
            event.key() == Qt.Key.Key_Return
            and event.modifiers() == Qt.KeyboardModifier.ShiftModifier
        ):
            self.input_edit.insertPlainText("\n")
        else:
            QTextEdit.keyPressEvent(self.input_edit, event)

    def _load_preferences(self):
        pass
