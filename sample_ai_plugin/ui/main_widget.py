# -*- coding: utf-8 -*-
"""示例 AI 插件主控件。

演示 LLMPluginService 的完整集成方式，支持对话、流式输出、工具调用。
样式全面使用 InstructionX_UIKit 组件（Button/ComboBox/TextArea）与 T()
令牌，随全局主题自动换肤；后台线程的 UI 更新统一经 run_in_ui_thread
封送到 UI 线程。
"""

import json
import threading
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit import MONO_FAMILY, T
from InstructionX_UIKit.components import Button, ComboBox, TextArea

from utils.thread_utils import run_in_ui_thread

_CONFIG_PATH = Path(__file__).parent.parent / "config" / "default.json"
_DEFAULT_MARGINS = [16, 16, 16, 16]
_DEFAULT_SPACING = 16
_OUTPUT_MIN_HEIGHT = 160
#: provider/model 参数取该值表示「默认实例 / 默认模型」（与框架 DEFAULT_PROVIDER 语义一致）
_DEFAULT_REFERENCE = "default"


class StreamWorker(QThread):
    """流式响应工作线程（QThread + Signal，天然线程安全，无需封送）"""

    chunk_received = Signal(str)
    finished = Signal(dict)

    def __init__(self, service, conv_id, message, parent=None):
        super().__init__(parent)
        self._service = service
        self._conv_id = conv_id
        self._message = message

    def run(self):
        try:
            def callback(chunk):
                self.chunk_received.emit(chunk.content)

            content = self._service.stream_send_message(
                self._conv_id,
                self._message,
                callback=callback,
            )
            self.finished.emit({"success": True, "content": content})
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})


class MainWidget(QWidget):
    """示例 AI 插件主控件"""

    def __init__(self, service, parent=None):
        super().__init__(parent)
        self._service = service
        self._providers = []
        self._conv_id = None
        self._worker = None
        cfg = self._load_config().get("ui", {})
        self._margins = cfg.get("margins", _DEFAULT_MARGINS)
        self._spacing = cfg.get("spacing", _DEFAULT_SPACING)
        self._setup_ui()
        self._populate_providers()

    def _load_config(self) -> dict:
        """读取插件默认配置（UI 间距与边距参数）"""
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _setup_ui(self):
        """构建 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        scroll_area = self._create_scroll_area()
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(*self._margins)
        layout.setSpacing(self._spacing)

        self._add_title(layout)
        layout.addLayout(self._create_selectors())
        self._output = self._create_output_area()
        layout.addWidget(self._output)
        self._add_buttons(layout)
        layout.addStretch()

        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _create_scroll_area(self) -> QScrollArea:
        """创建滚动区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        return scroll_area

    def _add_title(self, layout: QVBoxLayout):
        """添加标题（字号取 UIKit 令牌，颜色随全局主题）"""
        title = QLabel("示例 AI 插件 — LLMPluginService 演示")
        font = QFont()
        font.setPixelSize(T("font.lg"))
        font.setWeight(QFont.Weight(QFont.Bold))
        title.setFont(font)
        layout.addWidget(title)

    def _create_selectors(self) -> QHBoxLayout:
        """创建 Provider / Model 选择器行"""
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Provider:"))
        self._provider_combo = ComboBox()
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        selector_layout.addWidget(self._provider_combo)
        selector_layout.addWidget(QLabel("Model:"))
        self._model_combo = ComboBox()
        selector_layout.addWidget(self._model_combo)
        return selector_layout

    def _create_output_area(self) -> TextArea:
        """创建输出区域（等宽字体便于查看流式输出）"""
        output = TextArea()
        output.setReadOnly(True)
        output.setMinimumHeight(_OUTPUT_MIN_HEIGHT)
        output.setFont(QFont(MONO_FAMILY))
        return output

    def _add_buttons(self, layout: QVBoxLayout):
        """创建操作按钮（同步/流式/工具调用，均为主操作 primary 变体）"""
        for text, handler in (
            ("发送测试消息（同步）", self._on_sync_chat),
            ("流式发送消息", self._on_stream_chat),
            ("使用工具调用", self._on_tools),
        ):
            btn = Button(text, variant="primary")
            btn.clicked.connect(handler)
            layout.addWidget(btn)

    def _populate_providers(self):
        """填充 Provider 列表（itemData 存实例 id，语义同框架 provider 参数）"""
        self._providers = self._service.get_available_providers()
        self._provider_combo.blockSignals(True)
        self._provider_combo.clear()
        if self._providers:
            for p in self._providers:
                self._provider_combo.addItem(p.name, p.instance_id)
            self._on_provider_changed()
        else:
            self._model_combo.clear()
            self._model_combo.addItem("无可用 Provider", _DEFAULT_REFERENCE)
        self._provider_combo.blockSignals(False)

    def _on_provider_changed(self):
        """Provider 选择变更，刷新模型下拉（ModelInfo 字段：name/id）"""
        idx = self._provider_combo.currentIndex()
        if idx < 0 or idx >= len(self._providers):
            return
        provider = self._providers[idx]
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for m in provider.models:
            self._model_combo.addItem(m.name or m.id, m.id)
        if not provider.models:
            self._model_combo.addItem(
                provider.current_chat_model or _DEFAULT_REFERENCE,
                _DEFAULT_REFERENCE,
            )
        self._model_combo.blockSignals(False)

    def _get_selected(self) -> tuple:
        """获取当前选中的 Provider 实例 id 和 Model id"""
        provider = self._provider_combo.currentData() or _DEFAULT_REFERENCE
        model = self._model_combo.currentData() or _DEFAULT_REFERENCE
        return provider, model

    def _ensure_conversation(self, provider, model):
        """确保对话存在"""
        if not self._conv_id:
            self._append(f"[系统] 创建对话 ({provider}/{model})...")
        self._conv_id = self._service.create_conversation(
            "你是一个友好的助手，用简洁的语言回答。",
            provider,
            model,
        )
        self._append(f"[系统] 对话已创建: {self._conv_id[:8]}...")

    def _append(self, text: str):
        """追加文本到输出区（仅允许在 UI 线程调用）"""
        self._output.append(text)

    def _append_safe(self, text: str):
        """从任意线程追加文本（经 run_in_ui_thread 封送到 UI 线程）"""
        run_in_ui_thread(self._append, text)

    def _on_sync_chat(self):
        """同步聊天按钮处理"""
        provider, model = self._get_selected()
        self._ensure_conversation(provider, model)
        self._append(f"[用户] 请用三句话解释量子计算 ({provider}/{model})")

        def send():
            try:
                content = self._service.send_message(self._conv_id, "请用三句话解释量子计算")
                self._append_safe(f"[助手] {content}")
            except Exception as e:
                self._append_safe(f"[错误] {e}")

        t = threading.Thread(target=send)
        t.start()

    def _on_stream_chat(self):
        """流式聊天按钮处理"""
        provider, model = self._get_selected()
        self._ensure_conversation(provider, model)
        self._append(f"[用户] 解释什么是深度学习 ({provider}/{model})")

        self._worker = StreamWorker(
            self._service,
            self._conv_id,
            "解释什么是深度学习",
        )
        self._worker.chunk_received.connect(self._on_chunk)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_chunk(self, text: str):
        """处理流式 chunk（经 Signal 到达，已在 UI 线程）"""
        if text:
            self._append(text)

    def _on_finished(self, result: dict):
        """流式响应完成（经 Signal 到达，已在 UI 线程）"""
        if not result.get("success"):
            self._append(f"[错误] {result.get('error')}")

    def _on_tools(self):
        """工具调用按钮处理"""
        provider, model = self._get_selected()
        self._ensure_conversation(provider, model)
        self._service.register_tools()
        self._append("[系统] 工具已注册，开始工具调用...")
        self._send_tools_request(provider, model)

    def _send_tools_request(self, provider, model):
        """在后台线程发送工具调用请求"""
        def send():
            try:
                executor = self._service.get_tool_executor()
                messages = [{"role": "user", "content": "计算 (2+3)*4 的结果"}]
                chat_result = executor.chat_with_tools(
                    messages, provider=provider, model=model,
                )
                for r in chat_result.tool_results:
                    self._append_safe(f"[工具 {r.tool_name}] {r.result}")
                self._append_safe(f"[助手] {chat_result.final_text}")
            except Exception as e:
                self._append_safe(f"[错误] {e}")

        t = threading.Thread(target=send)
        t.start()
