# -*- coding: utf-8 -*-
"""预览面板（ui 层）。

预览区 = ImageView（圆角图片视图）+ 结果信息标签。
``preview_ready`` 信号携带的 PNG 字节在 **UI 线程** 的槽函数中经
``QPixmap.loadFromData`` 解码后 ``ImageView.set_source`` 显示
（QPixmap 只允许在 UI 线程创建，SPEC §1.3 线程边界）；
显示前按预览上限等比缩放（仅影响显示，不影响管线数据）。
"""

from typing import Any, Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from InstructionX_UIKit.components import Dialog, ImageView
from InstructionX_UIKit.theme import set_property

from utils.logging_tools import LoggerManager, get_name

__all__ = ["PreviewPanel"]

#: 预览显示等比缩放上限（SPEC §8 preview.max_width / max_height；
#: 配置接管前由本常量承载，缩放仅影响显示不影响数据）
_PREVIEW_MAX_WIDTH = 960
_PREVIEW_MAX_HEIGHT = 720
#: 空态提示与解码失败提示
_HINT_EMPTY = "运行管线后，preview 节点的结果将显示在这里。"
_HINT_DECODE_FAILED = "预览图解码失败（非有效 PNG 数据）。"
#: 空态占位透明像素尺寸（ImageView 对 null pixmap 会显示「加载失败」
#: 占位插画，空态改用 1×1 透明像素保持干净的空白区域）
_EMPTY_PIXMAP_SIZE = 1
#: 点击放大预览对话框的显示上限（超出等比缩小，仅影响显示）
_PREVIEW_DIALOG_MAX_WIDTH = 1024
_PREVIEW_DIALOG_MAX_HEIGHT = 768
#: 预览对话框标题与按钮文案
_PREVIEW_DIALOG_TITLE = "预览"
_PREVIEW_DIALOG_OK = "关闭"

_logger = LoggerManager()
_MODULE = get_name()


class _PlainImageView(ImageView):
    """去除悬停「预览」蒙层与手型光标的 ImageView。

    预览对话框内的图片本身已是预览结果，再叠加悬停蒙层（暗色遮罩 +
    「预览」字样）属于冗余引导；进入/离开事件跳过蒙层标记即可。
    """

    def __init__(self, source=None, parent: QWidget = None) -> None:
        super().__init__(source, parent=parent)
        self.setCursor(Qt.ArrowCursor)

    def enterEvent(self, event) -> None:
        QWidget.enterEvent(self, event)  # 不置 _hovered，蒙层不触发

    def leaveEvent(self, event) -> None:
        QWidget.leaveEvent(self, event)


class PreviewPanel(QWidget):
    """预览区控件：ImageView + 结果信息（尺寸 / 通道 / 耗时）。

    公开方法:
        ``show_result(png_bytes, info)``：显示一轮 preview 结果；
        ``show_empty()``：回空态提示（图加载 / 重置时调用）。
    """

    def __init__(self, parent: QWidget = None) -> None:
        """构建 ImageView 与信息标签，初始为空态。

        参数:
            parent: 父控件。
        """
        super().__init__(parent)
        self._image_view = ImageView()
        self._info_label = QLabel()
        #: 当前结果的原始分辨率 pixmap（点击放大预览用；空态为 None）
        self._current_pixmap: Optional[QPixmap] = None
        self._build_layout()
        self._image_view.clicked.connect(self._open_preview_dialog)
        self.show_empty()

    def show_result(self, png_bytes: bytes, info: Dict[str, Any]) -> None:
        """显示 preview 结果（仅可在 UI 线程调用）。

        参数:
            png_bytes: 引擎 imencode 产出的 PNG 字节。
            info: 结果元数据 ``{"width","height","channels","elapsed_ms"}``。
        """
        pixmap = QPixmap()
        if not pixmap.loadFromData(png_bytes):
            _logger.error(_MODULE, "预览 PNG 解码失败")
            self._info_label.setText(_HINT_DECODE_FAILED)
            return
        self._current_pixmap = pixmap
        self._image_view.set_source(self._scaled(pixmap))
        self._info_label.setText(self._format_info(info))

    def show_empty(self) -> None:
        """回空态：清空图片并显示引导提示。"""
        self._current_pixmap = None
        self._image_view.set_source(self._transparent_pixmap())
        self._info_label.setText(_HINT_EMPTY)

    def _open_preview_dialog(self) -> None:
        """点击图片 → 放大预览对话框（原始分辨率，超限等比缩小）。"""
        if self._current_pixmap is None or self._current_pixmap.isNull():
            return  # 空态 / 解码失败无图可预览
        dialog = Dialog(self, title=_PREVIEW_DIALOG_TITLE,
                        ok_text=_PREVIEW_DIALOG_OK, show_cancel=False)
        pixmap = self._scaled_for_dialog()
        view = _PlainImageView(pixmap)
        view.setFixedSize(pixmap.size())  # 对话框内容区贴合图片实际尺寸
        dialog.set_content(view)
        dialog.exec()

    def _scaled_for_dialog(self) -> QPixmap:
        """对话框显示用 pixmap：超出上限等比缩小（仅显示层）。"""
        pixmap = self._current_pixmap
        if pixmap.width() <= _PREVIEW_DIALOG_MAX_WIDTH and \
                pixmap.height() <= _PREVIEW_DIALOG_MAX_HEIGHT:
            return pixmap
        return pixmap.scaled(
            _PREVIEW_DIALOG_MAX_WIDTH, _PREVIEW_DIALOG_MAX_HEIGHT,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)

    @staticmethod
    def _transparent_pixmap() -> QPixmap:
        """构造 1×1 透明像素（空态占位，规避「加载失败」占位插画）。"""
        pixmap = QPixmap(_EMPTY_PIXMAP_SIZE, _EMPTY_PIXMAP_SIZE)
        pixmap.fill(Qt.transparent)
        return pixmap

    # ------------------------------------------------------------------ 内部
    def _build_layout(self) -> None:
        """纵向装配：图片视图拉伸占满，信息标签居底。"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._image_view, 1)
        set_property(self._info_label, "role", "secondary")
        self._info_label.setWordWrap(True)
        layout.addWidget(self._info_label)

    def _scaled(self, pixmap: QPixmap) -> QPixmap:
        """超出预览上限时等比缩小（仅显示层缩放）。"""
        if pixmap.width() <= _PREVIEW_MAX_WIDTH and pixmap.height() <= _PREVIEW_MAX_HEIGHT:
            return pixmap
        return pixmap.scaled(
            _PREVIEW_MAX_WIDTH, _PREVIEW_MAX_HEIGHT,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def _format_info(self, info: Dict[str, Any]) -> str:
        """把 info 元数据格式化为单行结果文案。"""
        return (
            f"结果：{info.get('width', '?')}×{info.get('height', '?')}"
            f" · {info.get('channels', '?')} 通道"
            f" · 耗时 {float(info.get('elapsed_ms', 0.0)):.0f} ms"
        )
