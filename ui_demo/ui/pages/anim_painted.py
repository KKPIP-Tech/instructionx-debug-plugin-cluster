# -*- coding: utf-8 -*-
"""动画 · 自绘演示页：24 个自绘 / 定时器动画预设的参数化卡片网格。

每卡 = 演示元件 + 参数区 + 「播放」按钮。由于自绘组件的可调参数基本都是
构造参数（InstructionX_UIKit 未提供运行时 setter），本页统一采用「参数变化即按新参数
重建演示控件」的方式应用；连续型组件重建后立即重启，触发型组件点击
「播放」重放，滚动型组件点击「播放」驱动滚动条演示。
文案经 ``bind_tr`` 按 ``anim_painted`` 分组取词（卡片键 = 组件短名）。
"""

import weakref
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from InstructionX_UIKit.anim import painted as P
from InstructionX_UIKit.theme import T, ThemeManager

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, make_page
from .playground import ParamCard, add_specs

__all__ = ["create_page"]

# ---------------------------------------------------------------------------
# 参数规格表（第 3 元素为取词键，构建时经 _S() 译为当前语言标签）
# ---------------------------------------------------------------------------
_SPECS_SPINNER = [("int", "size", "spinner.p.size", 40, 16, 64),
                  ("int", "line_width", "spinner.p.line_width", 3, 1, 8),
                  ("float", "speed", "spinner.p.speed", 10.0, 1.0, 30.0,
                   {"step": 1.0})]
_SPECS_DOTS = [("int", "count", "dots.p.count", 3, 1, 6),
               ("int", "diameter", "dots.p.diameter", 9, 4, 16),
               ("int", "amplitude", "dots.p.amplitude", 6, 2, 14),
               ("int", "period", "dots.p.period", 600, 200, 2000)]
_SPECS_CHECK = [("int", "size", "check.p.size", 56, 24, 96),
                ("int", "duration", "check.p.duration", 320, 100, 2000)]
_SPECS_LIKE = [("int", "size", "like.p.size", 52, 32, 80),
               ("int", "particle_count", "like.p.particle_count", 10, 4, 30)]
_SPECS_SKELETON = [("int", "period", "skeleton.p.period", 1400, 400, 3000),
                   ("int", "interval", "skeleton.p.interval", 33, 10, 100)]
_SPECS_SHIMMER = [("int", "period", "shimmer.p.period", 1440, 400, 3000),
                  ("float", "band", "shimmer.p.band", 0.4, 0.1, 0.9)]
_SPECS_STRIPED = [("int", "height", "striped.p.height", 14, 6, 24),
                  ("int", "stripe", "striped.p.stripe", 12, 4, 24),
                  ("int", "target", "striped.p.target", 82, 0, 100)]
_SPECS_PARALLAX = [("int", "layers", "parallax.p.layers", 3, 2, 5),
                   ("int", "layer_height", "parallax.p.layer_height", 64, 40, 120)]
_SPECS_REVEAL = [("int", "blocks", "reveal.p.blocks", 12, 4, 20),
                 ("float", "threshold", "reveal.p.threshold", 0.85, 0.3, 1.0)]
_SPECS_STRIP = [("float", "step", "strip.p.step", 2.0, 0.5, 6.0),
                ("int", "interval", "strip.p.interval", 30, 10, 100),
                ("bool", "autoplay", "strip.p.autoplay", True)]
_SPECS_STICKY = [("int", "rows", "sticky.p.rows", 24, 8, 40),
                 ("int", "cover_height", "sticky.p.cover_height", 90, 0, 200)]
_SPECS_PROGRESS = [("int", "height", "progress.p.height", 8, 4, 16),
                   ("int", "rows", "progress.p.rows", 30, 10, 60)]
_SPECS_STORY = [("int", "steps", "story.p.steps", 5, 2, 8),
                ("int", "delta", "story.p.delta", 120, 60, 300)]
_SPECS_FLUID = [("int", "blobs", "fluid.p.blobs", 3, 1, 8),
                ("float", "speed", "fluid.p.speed", 1.0, 0.2, 3.0),
                ("int", "fps", "fluid.p.fps", 30, 10, 60)]
_SPECS_NUMBER = [("int", "decimals", "number.p.decimals", 2, 0, 4),
                 ("text", "prefix", "number.p.prefix", "¥"),
                 ("float", "target", "number.p.target", 1024.5, 0.0, 99999.0,
                  {"step": 100.0}),
                 ("int", "duration", "number.p.duration", 480, 200, 3000)]
_SPECS_TILT = [("float", "max_angle", "tilt.p.max_angle", 10.0, 2.0, 25.0,
                {"step": 1.0}),
               ("float", "persp", "tilt.p.persp", 700.0, 200.0, 1500.0,
                {"step": 20.0, "decimals": 0})]
_SPECS_CUBE = [("float", "persp", "cube.p.persp", 520.0, 200.0, 1200.0,
                {"step": 20.0, "decimals": 0}),
               ("bool", "auto", "cube.p.auto", False)]
_SPECS_COVER = [("int", "items", "cover.p.items", 5, 3, 7),
                ("float", "persp", "cover.p.persp", 460.0, 200.0, 1200.0,
                 {"step": 20.0, "decimals": 0})]

_COVER_ITEM_COUNT = 7   # 立体轮播演示封面项数（与语言文件 cover.1-7 对应）
_STRIP_ITEM_COUNT = 8   # 横向滚动条带演示项数（与语言文件 strip.1-8 对应）


def _lab(text, style=""):
    lab = QLabel(text)
    lab.setAlignment(Qt.AlignCenter)
    if style:
        lab.setStyleSheet(style)
    return lab


def _fill(text, bg_key="primary", fg_key="on.primary", extra=""):
    """主题感知填充标签：颜色取令牌（配合整页主题重建，切主题即刷新）。"""
    return _lab(text, f"background:{T('color.' + bg_key)};"
                      f"color:{T('color.' + fg_key)};border-radius:6px;{extra}")


def _S(tr, rows) -> list:
    """把规格行第 3 元素（取词键）译为当前语言标签。"""
    return [(kind, name, tr(label_key), *rest)
            for kind, name, label_key, *rest in rows]


def _make_play_fn(card, opts, play):
    """生成播放回调：优先自定义 ``play``，否则调用演示控件的 ``start()``。"""
    def _do_play():
        w = card.demo
        if w is None:
            return None
        if play is not None:
            return play(w, opts)
        if hasattr(w, "start"):
            w.start()
        return None
    return _do_play


def _make_rebuild_fn(card, opts, build, auto, do_play):
    """生成重建回调：按当前参数重建演示控件，连续型立即重放。"""
    def rebuild(*_):
        card.set_demo(build(opts))
        if auto:
            do_play()
    return rebuild


def _rcard(i18n, title, hint, build, specs, play=None, demo_height=130,
           auto=False):
    """构建一张参数化自绘动画卡片（重建式应用参数）。

    参数:
        build: ``build(opts) -> QWidget``，按当前参数构造演示控件。
        specs: 参数规格（见 ``playground.add_specs``）。
        play: 可选 ``play(widget, opts) -> 句柄``；缺省时调用 ``widget.start()``。
        auto: True 时每次重建后立即播放（连续型 / 自动演示组件）。
    """
    card = ParamCard(title, hint=hint, demo_height=demo_height, i18n=i18n)
    opts = {}
    add_specs(card.form, opts, specs)
    card.opts = opts  # 暴露参数快照，便于审计 / 测试断言接线
    do_play = _make_play_fn(card, opts, play)
    rebuild = _make_rebuild_fn(card, opts, build, auto, do_play)
    card.set_play(do_play)
    card.form.changed.connect(rebuild)
    card._rebuild = rebuild  # 供主题切换时整页重建（刷新令牌色）
    rebuild()
    return card


def _simple_card(i18n, tr, key, build, specs, **kw):
    """「标题 / 提示取词 + 规格表翻译」型卡片的通用构建。"""
    return _rcard(i18n, tr(f"{key}.title"), tr(f"{key}.hint"), build,
                  _S(tr, specs), **kw)


# ---------------------------------------------------------------------------
# 各卡片构建
# ---------------------------------------------------------------------------

def _check_card(i18n, tr):
    """对勾描绘卡：播放 = 复位后重新描绘。"""

    def _play(w, o):
        w.reset()
        w.start()
    return _simple_card(i18n, tr, "check",
                        lambda o: P.CheckDraw(size=o["size"],
                                              duration=o["duration"]),
                        _SPECS_CHECK, play=_play, auto=True)


def _magnet_specs(tr) -> list:
    """磁吸按钮卡参数规格（文本默认值需取词，故构建期生成）。"""
    return [("text", "text", tr("magnet.p.text"), tr("magnet.default")),
            ("float", "max_offset", tr("magnet.p.max_offset"), 8.0, 2.0, 24.0,
             {"step": 1.0}),
            ("float", "magnet_range", tr("magnet.p.magnet_range"), 96.0, 40.0,
             240.0, {"step": 4.0, "decimals": 0})]


def _magnet_card(i18n, tr):
    """磁吸按钮卡：按钮随鼠标位移。"""
    return _rcard(i18n, tr("magnet.title"), tr("magnet.hint"),
                  lambda o: P.MagneticButton(o["text"], max_offset=o["max_offset"],
                                             magnet_range=o["magnet_range"]),
                  _magnet_specs(tr), play=lambda w, o: w.click())


def _skeleton_card(i18n, tr):
    """骨架屏微光卡：连续扫过。"""

    def _build(o):
        w = P.SkeletonShimmer(period=o["period"], interval=o["interval"])
        w.setMinimumSize(240, 96)
        return w
    return _simple_card(i18n, tr, "skeleton", _build, _SPECS_SKELETON, auto=True)


def _shimmer_card(i18n, tr):
    """区域微光卡：任意区域微光扫过。"""

    def _build(o):
        w = P.Shimmer(period=o["period"], band=o["band"])
        w.setMinimumSize(230, 80)
        return w
    return _simple_card(i18n, tr, "shimmer", _build, _SPECS_SHIMMER, auto=True)


def _striped_card(i18n, tr):
    """条纹流动进度条卡：播放 = 动画到目标值。"""

    def _build(o):
        w = P.ProgressStriped(value=30, height=o["height"], stripe=o["stripe"])
        w.setMinimumWidth(250)
        return w
    return _simple_card(i18n, tr, "striped", _build, _SPECS_STRIPED,
                        play=lambda w, o: w.animateTo(o["target"]), auto=True)


def _parallax_build(o, tr):
    """视差滚动演示控件：逐层添加不同速度的填充标签。"""
    area = P.ParallaxArea()
    n = o["layers"]
    for i in range(n):
        f = 0.2 + (0.7 * i / max(n - 1, 1))
        area.addLayer(_fill(tr("parallax.layer", n=i + 1, f=f"{f:.2f}")),
                      factor=f, height=o["layer_height"])
    area.setMinimumSize(250, 180)
    return area


def _parallax_card(i18n, tr):
    """视差滚动容器卡：播放驱动滚动条演示视差。"""

    def _play(w, o):
        sb = w.verticalScrollBar()
        sb.setValue(0 if sb.value() > sb.maximum() // 2 else sb.maximum())
    return _rcard(i18n, tr("parallax.title"), tr("parallax.hint"),
                  lambda o: _parallax_build(o, tr), _S(tr, _SPECS_PARALLAX),
                  play=_play, demo_height=190)


def _reveal_build(o, tr):
    """滚动渐显演示控件：一列内容块 + ScrollReveal 包装。"""
    box = QWidget()
    lay = QVBoxLayout(box)
    lay.setContentsMargins(4, 4, 4, 4)
    for i in range(o["blocks"]):
        blk = _fill(tr("reveal.block", n=i + 1), "bg.muted", "text.primary")
        blk.setFixedHeight(56)
        lay.addWidget(blk)
    reveal = P.ScrollReveal(box, threshold=o["threshold"])
    reveal.setMinimumSize(250, 180)
    return reveal


def _reveal_card(i18n, tr):
    """滚动渐显卡：播放滚动渐显内容块。"""

    def _play(w, o):
        sb = w.verticalScrollBar()
        sb.setValue(sb.maximum() if sb.value() < sb.maximum() // 2 else 0)
    return _rcard(i18n, tr("reveal.title"), tr("reveal.hint"),
                  lambda o: _reveal_build(o, tr), _S(tr, _SPECS_REVEAL),
                  play=_play, demo_height=190)


def _strip_card(i18n, tr):
    """横向滚动条带卡：演示项文案取词。"""

    def _build(o):
        items = [tr(f"strip.{i}") for i in range(1, _STRIP_ITEM_COUNT + 1)]
        w = P.HorizontalScrollStrip(items, step=o["step"],
                                    interval=o["interval"],
                                    autoplay=o["autoplay"])
        w.setMinimumSize(250, 64)
        return w
    return _simple_card(i18n, tr, "strip", _build, _SPECS_STRIP, auto=True)


def _sticky_build(o, tr):
    """粘性固定头演示控件：章节头 + 若干正文行。"""
    sticky = P.StickyHeader()
    # 前导空格为版式缩进，语言文件不保存首尾空白，故在代码中拼接
    header = _fill("  " + tr("sticky.header"), extra="font-weight:bold;")
    sticky.setHeaderWidget(header)
    body = QWidget()
    blay = QVBoxLayout(body)
    for i in range(o["rows"]):
        blay.addWidget(QLabel(tr("sticky.row", n=i + 1)))
    sticky.setBody(body, cover_height=o["cover_height"])
    sticky.setMinimumSize(250, 180)
    return sticky


def _sticky_card(i18n, tr):
    """粘性固定头卡：播放滚动吸附 / 释放。"""

    def _play(w, o):
        sb = w.verticalScrollBar()
        sb.setValue(160 if sb.value() < 80 else 0)
    return _rcard(i18n, tr("sticky.title"), tr("sticky.hint"),
                  lambda o: _sticky_build(o, tr), _S(tr, _SPECS_STICKY),
                  play=_play, demo_height=190)


def _progress_build(o, tr):
    """滚动进度条演示控件：顶部进度条 + 内容滚动区。"""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    content = QWidget()
    clay = QVBoxLayout(content)
    for i in range(o["rows"]):
        clay.addWidget(QLabel(tr("progress.row", n=i + 1)))
    scroll.setWidget(content)
    bar = P.ScrollProgressBar(scroll, height=o["height"])
    holder = QWidget()
    hlay = QVBoxLayout(holder)
    hlay.setContentsMargins(0, 0, 0, 0)
    hlay.setSpacing(0)
    hlay.addWidget(bar)
    hlay.addWidget(scroll, 1)
    holder.setMinimumSize(250, 180)
    holder._uik_scroll = scroll  # 供 play 取滚动条
    return holder


def _progress_card(i18n, tr):
    """滚动进度条卡：播放滚动驱动顶部进度条。"""

    def _play(w, o):
        sb = w._uik_scroll.verticalScrollBar()
        sb.setValue(0 if sb.value() > sb.maximum() // 2 else sb.maximum())
    return _rcard(i18n, tr("progress.title"), tr("progress.hint"),
                  lambda o: _progress_build(o, tr), _S(tr, _SPECS_PROGRESS),
                  play=_play, demo_height=190)


def _story_build(o, tr):
    """滚动叙事演示控件：按步数生成步骤（说明文本重复 4 段凑足长度）。"""
    story = P.ScrollStoryArea()
    for i in range(o["steps"]):
        story.addStep(tr("story.step", n=i + 1), tr("story.body") * 4)
    story.setMinimumSize(250, 180)
    return story


def _story_card(i18n, tr):
    """滚动叙事卡：播放滚动推进叙事时间线。"""

    def _play(w, o):
        sb = w.verticalScrollBar()
        sb.setValue(sb.value() + o["delta"]
                    if sb.value() < sb.maximum() - 10 else 0)
    return _rcard(i18n, tr("story.title"), tr("story.hint"),
                  lambda o: _story_build(o, tr), _S(tr, _SPECS_STORY),
                  play=_play, demo_height=190)


def _marquee_specs(tr) -> list:
    """跑马灯卡参数规格（文本默认值需取词，故构建期生成）。"""
    return [("text", "text", tr("marquee.p.text"), tr("marquee.default")),
            ("float", "speed", tr("marquee.p.speed"), 1.6, 0.4, 6.0),
            ("int", "gap", tr("marquee.p.gap"), 56, 16, 120),
            ("int", "pause", tr("marquee.p.pause"), 900, 0, 3000)]


def _marquee_card(i18n, tr):
    """跑马灯卡：长文本循环滚动。"""

    def _build(o):
        w = P.MarqueeLabel(o["text"], speed=o["speed"], gap=o["gap"],
                           pause=o["pause"])
        w.setMinimumWidth(250)
        return w
    return _rcard(i18n, tr("marquee.title"), tr("marquee.hint"), _build,
                  _marquee_specs(tr), auto=True)


def _fluid_card(i18n, tr):
    """流体渐变背景卡：正弦叠加的流体渐变。"""

    def _build(o):
        w = P.FluidBackground(blobs=o["blobs"], fps=o["fps"], speed=o["speed"])
        w.setMinimumSize(250, 150)
        return w
    return _simple_card(i18n, tr, "fluid", _build, _SPECS_FLUID,
                        auto=True, demo_height=170)


def _typewriter_specs(tr) -> list:
    """打字机卡参数规格（文本默认值需取词，故构建期生成）。"""
    return [("text", "text", tr("typewriter.p.text"), tr("typewriter.default")),
            ("int", "interval", tr("typewriter.p.interval"), 50, 10, 300),
            ("bool", "cursor", tr("typewriter.p.cursor"), True)]


def _typewriter_card(i18n, tr):
    """打字机卡：逐字输出 + 光标。"""

    def _build(o):
        w = P.TypewriterLabel(interval=o["interval"], cursor=o["cursor"])
        w.setMinimumWidth(250)
        return w
    return _rcard(i18n, tr("typewriter.title"), tr("typewriter.hint"), _build,
                  _typewriter_specs(tr), play=lambda w, o: w.start(o["text"]),
                  auto=True)


def _decode_specs(tr) -> list:
    """文字解码卡参数规格（文本默认值需取词，故构建期生成）。"""
    return [("text", "text", tr("decode.p.text"), tr("decode.default")),
            ("int", "step", tr("decode.p.step"), 40, 10, 120),
            ("int", "span", tr("decode.p.span"), 4, 1, 10)]


def _decode_card(i18n, tr):
    """文字解码卡：乱码逐步解码为文本。"""

    def _build(o):
        w = P.TextDecodeLabel(o["text"], step=o["step"], span=o["span"])
        w.setMinimumWidth(250)
        return w
    return _rcard(i18n, tr("decode.title"), tr("decode.hint"), _build,
                  _decode_specs(tr), play=lambda w, o: w.start(), auto=True)


def _number_card(i18n, tr):
    """数字滚动卡：播放 = 先归零再滚到目标。

    rollTo 从当前值起滚，当前值已等于目标值时画面无变化，
    用户会以为「播放无反应」，故播放前先归零。
    """

    def _build(o):
        w = P.NumberRollLabel(0, decimals=o["decimals"], prefix=o["prefix"],
                              duration=o["duration"])
        w.setStyleSheet("font-size:22px;font-weight:bold;")
        return w

    def _play(w, o):
        w.reset(0)
        return w.rollTo(o["target"])
    return _rcard(i18n, tr("number.title"), tr("number.hint"), _build,
                  _S(tr, _SPECS_NUMBER), play=_play, auto=True)


def _letters_specs(tr) -> list:
    """逐字进场卡参数规格（文本默认值需取词，故构建期生成）。"""
    return [("text", "text", tr("letters.p.text"), tr("letters.default")),
            ("int", "stagger", tr("letters.p.stagger"), 50, 10, 200),
            ("int", "rise", tr("letters.p.rise"), 12, 4, 30)]


def _letters_card(i18n, tr):
    """逐字进场卡：逐字上浮进场。"""

    def _build(o):
        w = P.LetterStaggerLabel(o["text"], stagger=o["stagger"],
                                 rise=o["rise"])
        w.setMinimumSize(240, 48)
        return w
    return _rcard(i18n, tr("letters.title"), tr("letters.hint"), _build,
                  _letters_specs(tr), play=lambda w, o: w.start(), auto=True)


def _tilt_card(i18n, tr):
    """卡片倾斜卡：鼠标移动查看 3D 倾斜。"""

    def _build(o):
        content = _lab(tr("tilt.content"),
                       f"background:{T('color.bg.elevated')};"
                       f"color:{T('color.text.primary')};"
                       f"border:1px solid {T('color.primary')};"
                       "border-radius:8px;")
        tilt = P.CardTilt(content, max_angle=o["max_angle"], persp=o["persp"])
        tilt.setMinimumSize(240, 150)
        return tilt
    return _rcard(i18n, tr("tilt.title"), tr("tilt.hint"), _build,
                  _S(tr, _SPECS_TILT), play=lambda w, o: None,
                  demo_height=170)


def _cube_card(i18n, tr):
    """立方体旋转卡：两面 3D 立方体翻转。"""

    def _build(o):
        w = P.CubeRotator(tr("cube.face_a"), tr("cube.face_b"),
                          persp=o["persp"])
        w.setMinimumSize(230, 150)
        if o["auto"]:
            w.startAuto()
        return w
    return _rcard(i18n, tr("cube.title"), tr("cube.hint"), _build,
                  _S(tr, _SPECS_CUBE), play=lambda w, o: w.rotate(),
                  demo_height=170)


def _flip_specs(tr) -> list:
    """翻转卡片参数规格（正反面文本默认值需取词，故构建期生成）。"""
    return [("text", "front", tr("flip.p.front"), tr("flip.default.front")),
            ("text", "back", tr("flip.p.back"), tr("flip.default.back")),
            ("float", "persp", tr("flip.p.persp"), 640.0, 200.0, 1200.0,
             {"step": 20.0, "decimals": 0})]


def _flip_card(i18n, tr):
    """翻转卡片：点击卡片或「播放」正反面翻转。"""

    def _build(o):
        w = P.FlipCard(o["front"], o["back"], persp=o["persp"])
        w.setMinimumSize(220, 140)
        return w
    return _rcard(i18n, tr("flip.title"), tr("flip.hint"), _build,
                  _flip_specs(tr), play=lambda w, o: w.flip(),
                  demo_height=160)


def _cover_card(i18n, tr):
    """立体轮播卡：3-7 项透视堆叠轮播。"""

    def _build(o):
        items = [tr(f"cover.{i}") for i in range(1, _COVER_ITEM_COUNT + 1)]
        w = P.CoverFlow(items[:o["items"]], persp=o["persp"])
        # 类默认最小 520x280 远超演示卡宽度，会撑破卡片网格；卡面尺寸随
        # 控件宽高自适应，故此处收敛到卡片可容纳的最小尺寸
        w.setMinimumSize(240, 190)
        return w
    return _rcard(i18n, tr("cover.title"), tr("cover.hint"), _build,
                  _S(tr, _SPECS_COVER), play=lambda w, o: w.next(),
                  demo_height=230)


# ---------------------------------------------------------------------------
# 卡片编排
# ---------------------------------------------------------------------------

def _loader_cards(i18n, tr) -> list:
    """加载指示类卡片（spinner / dots / check）。"""
    return [
        _simple_card(i18n, tr, "spinner",
                     lambda o: P.SpinnerArc(size=o["size"],
                                            line_width=o["line_width"],
                                            speed=o["speed"]),
                     _SPECS_SPINNER, auto=True),
        _simple_card(i18n, tr, "dots",
                     lambda o: P.BouncingDots(count=o["count"],
                                              diameter=o["diameter"],
                                              amplitude=o["amplitude"],
                                              period=o["period"]),
                     _SPECS_DOTS, auto=True),
        _check_card(i18n, tr),
    ]


def _button_anim_cards(i18n, tr) -> list:
    """按钮反馈类卡片（like / magnet）。"""
    return [
        _simple_card(i18n, tr, "like",
                     lambda o: P.LikeBurstButton(
                         size=o["size"], particle_count=o["particle_count"]),
                     _SPECS_LIKE, play=lambda w, o: w.click()),
        _magnet_card(i18n, tr),
    ]


def _shimmer_cards(i18n, tr) -> list:
    """微光 / 进度类卡片（6-8）。"""
    return [_skeleton_card(i18n, tr), _shimmer_card(i18n, tr),
            _striped_card(i18n, tr)]


def _scroll_cards(i18n, tr) -> list:
    """滚动型卡片（9-14）：点击「播放」驱动滚动条演示。"""
    return [_parallax_card(i18n, tr), _reveal_card(i18n, tr),
            _strip_card(i18n, tr), _sticky_card(i18n, tr),
            _progress_card(i18n, tr), _story_card(i18n, tr)]


def _text_cards(i18n, tr) -> list:
    """文本与背景类卡片（15-20）。"""
    return [_marquee_card(i18n, tr), _fluid_card(i18n, tr),
            _typewriter_card(i18n, tr), _decode_card(i18n, tr),
            _number_card(i18n, tr), _letters_card(i18n, tr)]


def _stereo_cards(i18n, tr) -> list:
    """3D 变换类卡片（21-24）。"""
    return [_tilt_card(i18n, tr), _cube_card(i18n, tr), _flip_card(i18n, tr),
            _cover_card(i18n, tr)]


def _cards(i18n) -> list:
    """按演示顺序构建全部 24 张参数化卡片。"""
    tr = bind_tr(i18n, "anim_painted")
    return (_loader_cards(i18n, tr) + _button_anim_cards(i18n, tr)
            + _shimmer_cards(i18n, tr) + _scroll_cards(i18n, tr)
            + _text_cards(i18n, tr) + _stereo_cards(i18n, tr))


def _rebuild_card(card) -> None:
    """重建单张卡片的演示控件；卡片 C++ 侧已销毁时静默跳过。"""
    rebuild = getattr(card, "_rebuild", None)
    if rebuild is None:
        return
    try:
        rebuild()
    except RuntimeError:
        pass  # 页面重建竞态导致卡片已销毁，忽略


def _rebuild_cards_on_theme(page, tm) -> None:
    """主题切换时整页重建各卡演示控件（覆盖 _fill 等 QSS 标签的令牌色）。"""
    root_ref = weakref.ref(page.widget())

    def _on_theme(*_):
        root = root_ref()
        if root is None:
            tm.theme_changed.disconnect(_on_theme)
            return
        try:
            cards = root.findChildren(ParamCard)
        except RuntimeError:
            tm.theme_changed.disconnect(_on_theme)
            return
        for card in cards:
            _rebuild_card(card)

    tm.theme_changed.connect(_on_theme)


def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """构建「动画 · 自绘」演示页（3 列卡片网格）。"""
    tr = bind_tr(i18n, "anim_painted")
    box = Section(tr("sec"))
    grid_host = QWidget()
    grid = QGridLayout(grid_host)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(12)
    for i, card in enumerate(_cards(i18n)):
        grid.addWidget(card, i // 3, i % 3)
    box.layout().addWidget(grid_host)
    page = make_page(tr("title"), tr("desc"), [box])
    _rebuild_cards_on_theme(page, ThemeManager.instance())
    return page
