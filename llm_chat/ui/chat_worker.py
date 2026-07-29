# -*- coding: utf-8 -*-
"""聊天工作线程。

在工作线程中消费 Service 的流式生成器，通过 Qt 信号把增量内容与
最终结果回投到 UI 线程（跨线程信号自动排队，线程安全）。
"""

from PySide6.QtCore import QThread, Signal


class ChatWorker(QThread):
    """聊天工作线程

    消费 ``service.stream_send_message`` 生成器：
    - 中间块经 ``chunk_received`` 信号逐块发出；
    - 结束/错误经 ``finished`` 信号发出结果字典。
    """

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
        """请求取消：在下一次迭代时停止消费（不强制杀线程）。"""
        self._is_cancelled = True

    def _do_stream(self):
        """消费流式生成器并分发信号"""
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
        """线程入口：异常统一经 finished 信号上报，不跨线程抛出"""
        if self._is_cancelled:
            return
        try:
            self._do_stream()
        except Exception as e:
            self.finished.emit({"success": False, "error": str(e)})
