"""
示例 AI 插件主控件

演示 LLMPluginService 的完整集成方式，支持对话、流式输出、工具调用。
"""

import json
import threading
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QLabel, QComboBox, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QThread, Signal
from utils.style_qss.registry import QssRegistry


class StreamWorker(QThread):
    """流式响应工作线程"""

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
        self.setObjectName("MainWidget")
        self._service = service
        self._providers = []
        self._conv_id = None
        self._worker = None
        self._load_plugin_style()
        self._setup_ui()
        self._populate_providers()

    def _load_plugin_style(self):
        """加载插件 QSS 样式文件"""
        style_dir = Path(__file__).parent.parent / "style"
        config_dir = Path(__file__).parent.parent / "config"
        if not style_dir.exists():
            return
        ui_cfg = {}
        if config_dir.exists():
            cfg_file = config_dir / "default.json"
            if cfg_file.exists():
                cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
                ui_cfg = cfg.get("ui", {})
        self._ui_config = ui_cfg
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            raw = QssRegistry.apply_variables(raw)
            for key, val in ui_cfg.items():
                raw = raw.replace(f"{{{key}}}", str(val))
            qss_parts.append(raw)
        if qss_parts:
            self._plugin_qss = "\n".join(qss_parts)
            self.setStyleSheet(self._plugin_qss)
            self.destroyed.connect(self._unload_plugin_style)

    def _unload_plugin_style(self):
        """卸载插件 QSS 样式（widget 销毁时调用）"""
        if hasattr(self, "_plugin_qss"):
            self.setStyleSheet("")
            del self._plugin_qss

    def _setup_ui(self):
        """初始化 UI 布局"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self._create_scroll_area(main_layout)
        self._create_title_and_selectors()
        self._create_output_area()
        self._create_buttons()

    def _create_scroll_area(self, main_layout):
        """创建滚动区域"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self._content_layout = QVBoxLayout(content)
        ui_cfg = getattr(self, "_ui_config", {})
        m_top = ui_cfg.get("content_margins_top", 16)
        m_bottom = ui_cfg.get("content_margins_bottom", 16)
        m_left = ui_cfg.get("content_margins_left", 16)
        m_right = ui_cfg.get("content_margins_right", 16)
        spacing = ui_cfg.get("content_spacing", 16)
        self._content_layout.setContentsMargins(m_top, m_bottom, m_left, m_right)
        self._content_layout.setSpacing(spacing)
        self._content_layout.addStretch()
        scroll_area.setWidget(content)
        main_layout.addWidget(scroll_area)

    def _create_title_and_selectors(self):
        """创建标题和选择器"""
        title = QLabel("示例 AI 插件 — LLMPluginService 演示")
        title.setProperty("heading", "true")
        self._content_layout.insertWidget(self._content_layout.count() - 1, title)

        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Provider:"))
        self._provider_combo = QComboBox()
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        selector_layout.addWidget(self._provider_combo)
        selector_layout.addWidget(QLabel("Model:"))
        self._model_combo = QComboBox()
        selector_layout.addWidget(self._model_combo)
        self._content_layout.insertLayout(self._content_layout.count() - 1, selector_layout)

    def _create_output_area(self):
        """创建输出区域"""
        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._content_layout.insertWidget(self._content_layout.count() - 1, self._output)

    def _create_buttons(self):
        """创建按钮"""
        btn_chat = QPushButton("发送测试消息（同步）")
        btn_chat.setProperty("class", "btn-ai")
        btn_chat.clicked.connect(self._on_sync_chat)
        self._content_layout.insertWidget(self._content_layout.count() - 1, btn_chat)

        btn_stream = QPushButton("流式发送消息")
        btn_stream.setProperty("class", "btn-ai")
        btn_stream.clicked.connect(self._on_stream_chat)
        self._content_layout.insertWidget(self._content_layout.count() - 1, btn_stream)

        btn_tools = QPushButton("使用工具调用")
        btn_tools.setProperty("class", "btn-ai")
        btn_tools.clicked.connect(self._on_tools)
        self._content_layout.insertWidget(self._content_layout.count() - 1, btn_tools)

    def _populate_providers(self):
        """填充 Provider 列表"""
        self._providers = self._service.get_available_providers()
        self._provider_combo.blockSignals(True)
        self._provider_combo.clear()
        if self._providers:
            for p in self._providers:
                self._provider_combo.addItem(p.name, p.name)
            self._on_provider_changed()
        else:
            self._model_combo.clear()
            self._model_combo.addItem("无可用 Provider", "")
        self._provider_combo.blockSignals(False)

    def _on_provider_changed(self):
        """Provider 选择变更"""
        idx = self._provider_combo.currentIndex()
        if idx < 0 or idx >= len(self._providers):
            return
        provider = self._providers[idx]
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for m in provider.models:
            self._model_combo.addItem(m.name or m.id, m.id)
        if not provider.models:
            self._model_combo.addItem(provider.current_chat_model or "default", "default")
        self._model_combo.blockSignals(False)

    def _get_selected(self) -> tuple:
        """获取当前选中的 Provider 和 Model"""
        provider = self._provider_combo.currentData() or "default"
        model = self._model_combo.currentData() or "default"
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
        """追加文本到输出区"""
        self._output.append(text)

    def _on_sync_chat(self):
        """同步聊天按钮处理"""
        provider, model = self._get_selected()
        self._ensure_conversation(provider, model)
        self._append(f"[用户] 请用三句话解释量子计算 ({provider}/{model})")

        def send():
            try:
                content = self._service.send_message(self._conv_id, "请用三句话解释量子计算")
                self._append(f"[助手] {content}")
            except Exception as e:
                self._append(f"[错误] {e}")

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
        """处理流式 chunk"""
        if text:
            self._append(text)

    def _on_finished(self, result: dict):
        """流式响应完成"""
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
                msgs, results, final = executor.chat_with_tools(
                    messages, provider=provider, model=model,
                )
                for r in results:
                    self._append(f"[工具 {r.tool_name}] {r.result}")
                self._append(f"[助手] {final}")
            except Exception as e:
                self._append(f"[错误] {e}")

        t = threading.Thread(target=send)
        t.start()
