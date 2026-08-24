# -*- coding: utf-8 -*-
"""MarkdownView 演示页：基础渲染 / LaTeX 公式 / Mermaid 图表 / 流式追加。

覆盖 alpha-v1.0.2 新增的 MarkdownView 全能力：

- 基础渲染：标题、行内样式、列表、引用、代码围栏、表格、链接；
- LaTeX 公式：行内 / 块级，matplotlib mathtext 后台异步渲染；
- Mermaid 围栏：渲染为可交互图表（MermaidView 查看器叠加在图位上）；
- MermaidView 独立使用：脱离 MarkdownView 的交互查看器小节；
- 流式 ``append_markdown``：模拟 AI 逐 token 输出（自动播放 + 重新播放）。

文案经 ``bind_tr`` 按 ``markdown_view`` 分组取词；Markdown 示例正文存于
语言包（CDATA 原样保留换行），语言切换重建页面即以新语言渲染。
"""

from typing import Optional

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QPushButton, QWidget

from InstructionX_UIKit.components.markdown_view import MarkdownView
from InstructionX_UIKit.mermaid import MermaidView
from InstructionX_UIKit.theme import set_property

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, hint_label, make_page, row

__all__ = ["create_markdown_view_page"]

#: 流式追加演示：每片长度（字符）与推送间隔（毫秒），模拟逐 token 到达
_STREAM_CHUNK_SIZE = 8
_STREAM_INTERVAL_MS = 40

#: 各分区视图最小高度（像素）
_BASIC_HEIGHT = 380
_MATH_HEIGHT = 300
_MERMAID_HEIGHT = 1150
_STREAM_HEIGHT = 480
_STANDALONE_HEIGHT = 320
_EMPTY_HEIGHT = 120


def _tr_of(i18n):
    """本页统一取词闭包（分组 ``markdown_view``）。"""
    return bind_tr(i18n, "markdown_view")


class _StreamPlayer(QObject):
    """流式追加播放器：QTimer 按小片段把示例正文推入 MarkdownView。

    以目标视图为父对象，视图销毁时定时器随之失效，无悬垂回调。
    """

    def __init__(self, view: MarkdownView, text: str):
        super().__init__(view)
        self._view = view
        self._text = text
        self._chunks = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def replay(self) -> None:
        """清空视图并从头按小片段流式推送（模拟逐 token 到达）。"""
        self._view.clear()
        size = _STREAM_CHUNK_SIZE
        self._chunks = [self._text[i:i + size]
                        for i in range(0, len(self._text), size)]
        self._timer.start(_STREAM_INTERVAL_MS)

    def _tick(self) -> None:
        """每拍推出一个片段；推完即停表。"""
        if not self._chunks:
            self._timer.stop()
            return
        self._view.append_markdown(self._chunks.pop(0))


def _basic_section(tr) -> Section:
    """基础渲染分区：标题 / 行内样式 / 列表 / 引用 / 代码围栏 / 表格 / 链接。"""
    sec = Section(tr("sec.basic"))
    view = MarkdownView(tr("sample.basic"))
    view.setMinimumHeight(_BASIC_HEIGHT)
    sec.layout().addWidget(view)
    return sec


def _math_section(tr) -> Section:
    """LaTeX 公式分区：行内 / 块级公式（后台异步渲染，渲染期以源码占位）。"""
    sec = Section(tr("sec.math"))
    view = MarkdownView(tr("sample.math"))
    view.setMinimumHeight(_MATH_HEIGHT)
    sec.layout().addWidget(view)
    return sec


def _mermaid_section(tr) -> Section:
    """Mermaid 围栏分区：图表渲染为可交互查看器（拖动平移 / 缩放 / 工具条）。"""
    sec = Section(tr("sec.mermaid"))
    view = MarkdownView(tr("sample.mermaid"))
    view.setMinimumHeight(_MERMAID_HEIGHT)
    sec.layout().addWidget(view)
    sec.layout().addWidget(hint_label(tr("hint.mermaid"), role="tertiary"))
    return sec


def _mermaid_view_section(tr) -> Section:
    """MermaidView 独立使用分区：脱离 MarkdownView 直接实例化交互查看器。"""
    sec = Section(tr("sec.mermaid_view"))
    view = MermaidView(tr("sample.standalone"))
    view.setMinimumHeight(_STANDALONE_HEIGHT)
    sec.layout().addWidget(view)
    sec.layout().addWidget(hint_label(tr("hint.mermaid_view"), role="tertiary"))
    return sec


def _stream_section(tr) -> Section:
    """流式追加演示分区：自动播放 + 重新播放按钮。"""
    sec = Section(tr("sec.stream"))
    view = MarkdownView()
    view.setMinimumHeight(_STREAM_HEIGHT)
    player = _StreamPlayer(view, tr("sample.stream"))
    sec.layout().addWidget(view)
    btn = QPushButton(tr("replay"))
    set_property(btn, "variant", "primary")
    set_property(btn, "size", "sm")
    btn.clicked.connect(player.replay)
    sec.layout().addWidget(row(btn))
    player.replay()
    return sec


def _empty_section(tr) -> Section:
    """空状态分区：无内容时显示空占位。"""
    sec = Section(tr("sec.empty"))
    view = MarkdownView()
    view.setFixedHeight(_EMPTY_HEIGHT)
    sec.layout().addWidget(view)
    return sec


def create_markdown_view_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """页面工厂：MarkdownView 全能力演示（分组 ``markdown_view`` 取词）。"""
    tr = _tr_of(i18n)
    return make_page(tr("title"), tr("desc"), [
        _basic_section(tr),
        _math_section(tr),
        _mermaid_section(tr),
        _mermaid_view_section(tr),
        _stream_section(tr),
        _empty_section(tr),
    ])
