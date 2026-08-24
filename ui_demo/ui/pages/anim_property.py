# -*- coding: utf-8 -*-
"""动画 · 属性演示页：28 个属性动画预设的参数化卡片网格。

每卡 = 演示元件 + 参数区（2-4 个有意义参数）+「播放」按钮：调整参数后
点击「播放」即按新参数重放；循环型动画（漂浮 / 辉光 / 呼吸 / 渐变流动等）
参数变化即时重启。参数全部对应 ``InstructionX_UIKit.anim.property`` 各预设的真实
``**opts``，不存在的参数不虚构。
文案经 ``bind_tr`` 按 ``anim_property`` 分组取词（卡片键 = 动画短名）。
"""

from typing import Optional

from PySide6.QtCore import QPoint, QRect, QTimer, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QStackedWidget, QWidget

from InstructionX_UIKit.anim import property as A
from InstructionX_UIKit.components.button import Button
from InstructionX_UIKit.components.switch import Switch
from InstructionX_UIKit.theme import T

from core.interfaces import ILocalizationFacade

from .common import ColorBlock, Section, bind_tr, connect_theme_refresh, make_page
from .playground import ParamCard, add_specs

__all__ = ["create_page"]

_DIRECTIONS = ["left", "right", "up", "down"]

# ---------------------------------------------------------------------------
# 参数规格表（第 3 元素为取词键，构建时经 _S() 译为当前语言标签）
# ---------------------------------------------------------------------------
_SPECS_FADE_IN = [("int", "duration", "fade_in.p.duration", 200, 50, 2000),
                  ("easing", "easing", "fade_in.p.easing", "standard"),
                  ("float", "from_opacity", "fade_in.p.opacity", 0.0, 0.0, 1.0)]
_SPECS_FADE_OUT = [("int", "duration", "fade_out.p.duration", 200, 50, 2000),
                   ("easing", "easing", "fade_out.p.easing", "standard")]
_SPECS_SLIDE_IN = [("choice", "direction", "slide_in.p.direction", "left",
                    list(_DIRECTIONS)),
                   ("int", "distance", "slide_in.p.distance", 70, 16, 200),
                   ("bool", "fade", "slide_in.p.fade", True),
                   ("int", "duration", "slide_in.p.duration", 200, 50, 2000)]
_SPECS_ZOOM_IN = [("float", "from_scale", "zoom_in.p.scale", 0.6, 0.05, 1.0),
                  ("bool", "fade", "zoom_in.p.fade", True),
                  ("int", "duration", "zoom_in.p.duration", 200, 50, 2000)]
_SPECS_SPRING_POP = [("float", "from_scale", "spring_pop.p.scale", 0.55, 0.05, 1.0),
                     ("int", "duration", "spring_pop.p.duration", 320, 100, 1000)]
_SPECS_BADGE_POP = [("int", "duration", "badge_pop.p.duration", 320, 100, 1000),
                    ("easing", "easing", "badge_pop.p.easing", "spring")]
_SPECS_STAGGER_IN = [("int", "interval", "stagger_in.p.interval", 90, 0, 300),
                     ("int", "distance", "stagger_in.p.offset", 24, 0, 80),
                     ("int", "duration", "stagger_in.p.duration", 200, 50, 2000)]
_SPECS_BLUR_IN = [("int", "radius", "blur_in.p.radius", 16, 0, 40),
                  ("int", "duration", "blur_in.p.duration", 320, 100, 2000)]
_SPECS_MASK_REVEAL = [("choice", "direction", "mask_reveal.p.direction", "circle",
                       ["right", "left", "down", "up", "circle"]),
                      ("int", "duration", "mask_reveal.p.duration", 320, 100, 2000)]
_SPECS_HOVER_LIFT = [("int", "dy", "hover_lift.p.dy", 6, 0, 20),
                     ("bool", "use_shadow", "hover_lift.p.shadow", True),
                     ("int", "duration", "hover_lift.p.duration", 120, 50, 600)]
_SPECS_MORPH = [("int", "duration", "morph.p.duration", 200, 50, 2000),
                ("int", "pulse_duration", "morph.p.pulse", 900, 200, 2000)]
_SPECS_RIPPLE = [("float", "max_opacity", "ripple.p.opacity", 0.35, 0.05, 0.8),
                 ("int", "duration", "ripple.p.duration", 320, 100, 1000)]
_SPECS_SWITCH = [("int", "duration", "switch.p.duration", 120, 50, 600),
                 ("easing", "easing", "switch.p.easing", "standard")]
_SPECS_PULSE = [("float", "peak", "pulse.p.peak", 1.06, 1.0, 1.5),
                ("int", "loops", "pulse.p.loops", 1, 1, 5),
                ("int", "duration", "pulse.p.duration", 320, 100, 2000)]
_SPECS_BOUNCE = [("int", "height", "bounce.p.height", 12, 4, 40),
                 ("int", "loops", "bounce.p.loops", 1, 1, 5),
                 ("int", "duration", "bounce.p.duration", 480, 200, 2000)]
_SPECS_SWING = [("int", "angle", "swing.p.angle", 8, 2, 30),
                ("int", "loops", "swing.p.loops", 1, 1, 5),
                ("int", "duration", "swing.p.duration", 480, 200, 2000)]
_SPECS_SHAKE = [("int", "distance", "shake.p.amplitude", 6, 2, 20),
                ("int", "loops", "shake.p.loops", 1, 1, 5),
                ("int", "duration", "shake.p.duration", 320, 100, 1000)]
_SPECS_FLASH = [("int", "times", "flash.p.times", 2, 1, 6),
                ("float", "max_opacity", "flash.p.opacity", 0.45, 0.1, 0.9),
                ("choice", "color", "flash.p.color", "warning",
                 ["primary", "success", "warning", "danger"]),
                ("int", "duration", "flash.p.duration", 480, 200, 2000)]
_SPECS_FLOAT_LOOP = [("int", "dy", "float_loop.p.dy", 6, 2, 24),
                     ("int", "duration", "float_loop.p.duration", 1600, 400, 4000)]
_SPECS_PULSE_GLOW = [("int", "min_blur", "pulse_glow.p.min_blur", 8, 0, 20),
                     ("int", "max_blur", "pulse_glow.p.max_blur", 28, 10, 60),
                     ("int", "duration", "pulse_glow.p.duration", 1600, 400, 4000)]
_SPECS_BREATHING = [("float", "min_opacity", "breathing.p.opacity", 0.5, 0.05, 0.9),
                    ("int", "duration", "breathing.p.duration", 1600, 400, 4000)]
_SPECS_CROSS_FADE = [("int", "duration", "cross_fade.p.duration", 200, 50, 2000),
                     ("easing", "easing", "cross_fade.p.easing", "standard")]
_SPECS_PAGE_TRANS = [("choice", "kind", "page_trans.p.kind", "slide",
                      ["fade", "slide"]),
                     ("choice", "direction", "page_trans.p.direction", "left",
                      list(_DIRECTIONS)),
                     ("int", "duration", "page_trans.p.duration", 320, 100, 2000)]
_SPECS_SLIDE_TRANS = [("choice", "direction", "slide_trans.p.direction", "left",
                       list(_DIRECTIONS)),
                      ("int", "duration", "slide_trans.p.duration", 320, 100, 2000),
                      ("bool", "hide_source", "slide_trans.p.hide_source", True)]
_SPECS_CONTAINER_MORPH = [("int", "radius", "container_morph.p.radius", 28, 0, 40),
                          ("int", "duration", "container_morph.p.duration",
                           320, 100, 2000)]
_SPECS_SHARED = [("int", "duration", "shared_element.p.duration", 320, 100, 2000),
                 ("easing", "easing", "shared_element.p.easing", "emphasis"),
                 ("bool", "fade", "shared_element.p.fade", False)]


class _Stage(QWidget):
    """绝对定位演示舞台：避免布局刷新覆盖 pos / geometry 动画。"""

    def __init__(self, w=250, h=112, parent=None):
        super().__init__(parent)
        self.setFixedSize(w, h)
        self._w, self._h = w, h

    def place(self, child, cw, ch, x=None, y=None):
        """把控件以固定尺寸放入舞台（默认居中）。"""
        child.setParent(self)
        child.setFixedSize(cw, ch)
        if x is None:
            x = (self._w - cw) // 2
        if y is None:
            y = (self._h - ch) // 2
        child.move(x, y)
        child.show()
        return child


def _pcard(i18n, title, hint, stage, play, specs, demo_height=130,
           continuous=False, on_stop=None):
    """构建一张参数化属性动画卡片。

    play(opts) -> 可选句柄；重放 / 参数变化（continuous）前自动停止旧句柄。
    """
    card = ParamCard(title, stage, hint=hint, demo_height=demo_height,
                     continuous=continuous, on_stop=on_stop, i18n=i18n)
    opts = {}
    add_specs(card.form, opts, specs)
    card.opts = opts  # 暴露参数快照，便于审计 / 测试断言接线
    card.set_play(lambda: play(opts))
    return card


def _block(text="", key="primary", size=(120, 66)):
    return ColorBlock(text, color_key=key, size=size)


def _restore_handle(h):
    """「应用 ↔ 还原」类句柄的清理：优先 restore()。"""
    if h is not None and hasattr(h, "restore"):
        h.restore()


def _safe_show(widget) -> None:
    """延时复原可见性；触发时目标可能已随演示卡重建销毁（Qt 对象已删）。"""
    try:
        widget.setVisible(True)
    except RuntimeError:
        pass


def _S(tr, rows) -> list:
    """把规格行第 3 元素（取词键）译为当前语言标签。"""
    return [(kind, name, tr(label_key), *rest)
            for kind, name, label_key, *rest in rows]


# ---------------------------------------------------------------------------
# 卡片构建：通用模式
# ---------------------------------------------------------------------------

def _block_card(i18n, tr, anim, fn, specs, color="primary", continuous=False):
    """「色块 + 单动画调用」型卡片的通用构建。"""
    st = _Stage()
    t = st.place(_block(tr(f"{anim}.block"), key=color), 120, 66)
    return _pcard(i18n, tr(f"{anim}.title"), tr(f"{anim}.hint"), st,
                  lambda o, t=t: fn(t, **o), _S(tr, specs),
                  continuous=continuous)


def _stacked_card(i18n, tr, anim, play_fn, specs, colors):
    """两页 QStackedWidget 往返切换类卡片的通用构建。"""
    st = _Stage()
    stack = QStackedWidget(st)
    st.place(stack, 150, 70)
    stack.addWidget(_block(tr(f"{anim}.block_a"), key=colors[0], size=(150, 70)))
    stack.addWidget(_block(tr(f"{anim}.block_b"), key=colors[1], size=(150, 70)))
    state = {"i": 0}

    def _play(o, stack=stack, state=state):
        state["i"] = 1 - state["i"]
        return play_fn(stack, state["i"], o)
    return _pcard(i18n, tr(f"{anim}.title"), tr(f"{anim}.hint"), st, _play,
                  _S(tr, specs))


# ---------------------------------------------------------------------------
# 卡片构建：定制卡片
# ---------------------------------------------------------------------------

def _fade_out_card(i18n, tr):
    """淡出卡：快照叠加层路径结束保持隐藏；延时自动复原，避免卡片停留隐藏态。"""
    st = _Stage()
    t = st.place(_block(tr("fade_out.block")), 120, 66)

    def _play(o, t=t):
        t.setVisible(True)  # 重放前先复原（上次结束保持隐藏）
        anim = A.fade_out(t, **o)
        # 仅当动画自然结束（隐藏）时延时复原；中途被 replay stop 已还原可见
        anim.finished.connect(lambda: QTimer.singleShot(700, lambda: _safe_show(t)))
        return anim
    return _pcard(i18n, tr("fade_out.title"), tr("fade_out.hint"), st, _play,
                  _S(tr, _SPECS_FADE_OUT))


def _badge_card(i18n, tr):
    """角标弹入卡：角标文本固定为 ``99+``，不翻译。"""
    st = _Stage()
    t = st.place(_block("99+", key="danger", size=(48, 40)), 48, 40)
    return _pcard(i18n, tr("badge_pop.title"), tr("badge_pop.hint"), st,
                  lambda o, t=t: A.badge_pop(t, **o), _S(tr, _SPECS_BADGE_POP))


def _stagger_card(i18n, tr):
    """交错入场卡：4 个绝对定位小块依次淡入上移。"""
    st = _Stage()
    cont = QWidget(st)
    cont.setGeometry(15, 30, 220, 50)
    cont.show()
    kids = []
    for i in range(4):
        k = ColorBlock("", color_key="primary", size=(44, 44), parent=cont)
        k.setFixedSize(44, 44)
        k.move(8 + i * 54, 3)
        k.show()
        kids.append(k)
    return _pcard(i18n, tr("stagger_in.title"), tr("stagger_in.hint"), st,
                  lambda o: A.stagger_in(cont, children=kids, **o),
                  _S(tr, _SPECS_STAGGER_IN))


def _hover_card(i18n, tr):
    """悬停上浮卡：事件过滤器；重放 = 按新参数重装过滤器。"""
    st = _Stage()
    t = st.place(_block(tr("hover_lift.block"), key="success"), 120, 66)
    return _pcard(i18n, tr("hover_lift.title"), tr("hover_lift.hint"), st,
                  lambda o, t=t: A.hover_lift(t, **o), _S(tr, _SPECS_HOVER_LIFT),
                  on_stop=lambda h: h.uninstall() if h is not None else None)


def _morph_card(i18n, tr):
    """按钮变形加载卡：「应用 ↔ 还原」切换，还原由 on_stop 的 restore() 完成。"""
    st = _Stage()
    btn = st.place(Button(tr("morph.block"), variant="primary"), 120, 36)
    state = {"on": False}

    def _play(o, btn=btn, state=state):
        if state["on"]:
            state["on"] = False
            return None
        state["on"] = True
        return A.button_morph_loading(btn, **o)
    return _pcard(i18n, tr("morph.title"), tr("morph.hint"), st, _play,
                  _S(tr, _SPECS_MORPH), on_stop=_restore_handle)


def _ripple_card(i18n, tr):
    """涟漪卡：重放 = 按新参数重装过滤器并触发一次。"""
    st = _Stage()
    rbtn = st.place(Button(tr("ripple.block"), variant="primary"), 120, 36)
    state = {"filt": None}

    def _play(o, rbtn=rbtn, state=state):
        old = state["filt"]
        if old is not None:
            rbtn.removeEventFilter(old)
            old.overlay.deleteLater()  # 清掉旧叠加层，避免残留
            old.deleteLater()
        # 必须清掉库函数的安装标记，否则 ripple() 会返回带旧参数的存量过滤器
        rbtn._uik_ripple = None
        state["filt"] = A.ripple(rbtn, **o)
        state["filt"].start(rbtn.rect().center())
        return None
    return _pcard(i18n, tr("ripple.title"), tr("ripple.hint"), st, _play,
                  _S(tr, _SPECS_RIPPLE))


def _switch_card(i18n, tr):
    """开关切换卡：按压回弹 + 换态。"""
    st = _Stage()
    sw = st.place(Switch(checked=False), 44, 22)
    return _pcard(i18n, tr("switch.title"), tr("switch.hint"), st,
                  lambda o: A.switch_toggle(sw, **o), _S(tr, _SPECS_SWITCH))


def _flash_card(i18n, tr):
    """高亮闪烁卡：高亮色取主题令牌。"""
    st = _Stage()
    t = st.place(_block(tr("flash.block")), 120, 66)

    def _play(o, t=t):
        opts = dict(o)
        opts["color"] = QColor(T(f"color.{opts['color']}"))
        return A.flash_highlight(t, **opts)
    return _pcard(i18n, tr("flash.title"), tr("flash.hint"), st, _play,
                  _S(tr, _SPECS_FLASH))


def _float_card(i18n, tr):
    """漂浮循环卡：重放前还原初始位置，避免以中途位置为新基准逐次漂移。"""
    st = _Stage()
    t = st.place(_block(tr("float_loop.block"), key="success"), 120, 66)
    home = t.pos()

    def _stop(h, t=t, home=home):
        if h is not None:
            h.stop()
        t.move(home)
    specs = _S(tr, _SPECS_FLOAT_LOOP) + [
        ("int", "loops", tr("float_loop.p.loops"), -1, -1, 5,
         {"special": tr("float_loop.p.unlimited")})]
    return _pcard(i18n, tr("float_loop.title"), tr("float_loop.hint"), st,
                  lambda o, t=t: A.float_loop(t, **o), specs,
                  continuous=True, on_stop=_stop)


def _gflow_colors(palette) -> list:
    """渐变流动色带：``theme`` 取主题令牌，其余为固定演示色。"""
    if palette == "theme":
        return [T("color.primary"), T("color.success")]
    if palette == "warm":
        return ["#C08A3E", "#D6473C"]
    return ["#7C5CFC", "#E05C8A"]


def _gflow_static(gf) -> None:
    """未播放时的静态渐变底（否则演示区是一块空白 QFrame）。"""
    ca, cb = _gflow_colors("theme")
    gf.setStyleSheet(
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, "
        f"stop:0 {ca}, stop:1 {cb}); border-radius: {T('radius.md')}px;")


def _gflow_specs(tr) -> list:
    """背景渐变流动卡参数规格（色带选项标签需取词，故构建期生成）。"""
    return [
        ("choice", "palette", tr("gflow.p.palette"), "theme",
         [(tr("gflow.palette.theme"), "theme"),
          (tr("gflow.palette.warm"), "warm"),
          (tr("gflow.palette.violet"), "violet")]),
        ("choice", "direction", tr("gflow.p.direction"), "horizontal",
         ["horizontal", "vertical"]),
        ("int", "duration", tr("gflow.p.duration"), 2400, 500, 6000)]


def _gflow_card(i18n, tr):
    """背景渐变流动卡：初始静态渐变，主题切换时刷新。"""
    st = _Stage()
    gf = QFrame(st)
    st.place(gf, 150, 66)
    gf.setAttribute(Qt.WA_StyledBackground, True)
    _gflow_static(gf)
    connect_theme_refresh(gf, _gflow_static)

    def _play(o, gf=gf):
        opts = dict(o)
        opts["colors"] = _gflow_colors(opts.pop("palette"))
        return A.gradient_flow(gf, **opts)
    return _pcard(i18n, tr("gflow.title"), tr("gflow.hint"), st, _play,
                  _gflow_specs(tr), continuous=True)


def _gtext_card(i18n, tr):
    """文字渐变流动卡：演示文本与默认值同源取词。"""
    st = _Stage()
    lab = QLabel(tr("gtext.block"), st)
    st.place(lab, 170, 40)
    specs = [("text", "text", tr("gtext.p.text"), tr("gtext.block")),
             ("int", "duration", tr("gtext.p.duration"), 2000, 500, 6000)]
    return _pcard(i18n, tr("gtext.title"), tr("gtext.hint"), st,
                  lambda o: A.gradient_text_flow(lab, **o), specs,
                  continuous=True)


def _cross_fade_card(i18n, tr):
    """交叉淡化卡：两页 A/B 交叉淡化。"""
    return _stacked_card(i18n, tr, "cross_fade",
                         lambda s, i, o: A.cross_fade(s, index=i, **o),
                         _SPECS_CROSS_FADE, ("primary", "success"))


def _page_trans_card(i18n, tr):
    """页面切换卡：QStackedWidget 切页（fade / slide）。"""
    return _stacked_card(i18n, tr, "page_trans",
                         lambda s, i, o: A.page_transition(s, i, **o),
                         _SPECS_PAGE_TRANS, ("primary", "warning"))


def _slide_trans_card(i18n, tr):
    """滑动过渡卡：源滑出 / 目标滑入。"""
    return _stacked_card(i18n, tr, "slide_trans",
                         lambda s, i, o: A.slide_transition(s, index=i, **o),
                         _SPECS_SLIDE_TRANS, ("success", "danger"))


def _morph_style(widget, radius=0) -> None:
    """容器变形目标方块的静态底色（主题令牌）；变形中由动画逐帧重写。"""
    widget.setStyleSheet(
        f"background:{T('color.primary')};border-radius:{radius}px;")


def _morph_stage():
    """创建容器变形演示的舞台与目标方块，返回 (stage, box, state)。

    方块底色取主题令牌；变形进行中由动画逐帧重写样式，主题刷新不干预。
    """
    st = _Stage()
    box = QFrame(st)
    state = {"on": False}
    _morph_style(box)
    st.place(box, 120, 66)
    connect_theme_refresh(
        box, lambda w: None if state["on"] else _morph_style(w))
    return st, box, state


def _container_morph_card(i18n, tr):
    """容器变形卡：应用 ↔ 还原；底色取主题令牌，空闲时随主题刷新。"""
    st, box, state = _morph_stage()

    def _play(o):
        if state["on"]:
            state["on"] = False
            return None
        state["on"] = True
        opts = dict(o)
        radius = opts.pop("radius")
        return A.container_morph(box, size=(170, 90), radius=radius,
                                 from_radius=0, **opts)
    return _pcard(i18n, tr("container_morph.title"),
                  tr("container_morph.hint"), st, _play,
                  _S(tr, _SPECS_CONTAINER_MORPH), on_stop=_restore_handle)


def _shared_card(i18n, tr):
    """共享元素卡：绝对定位，两位置往返。"""
    st = _Stage(250, 112)
    mover = ColorBlock("", color_key="primary", size=(56, 44))
    st.place(mover, 56, 44, x=14, y=(112 - 44) // 2)
    state = {"left": True}

    def _play(o, mover=mover, state=state):
        state["left"] = not state["left"]
        target = QRect(14, (112 - 44) // 2, 56, 44) if state["left"] \
            else QRect(250 - 14 - 56, (112 - 44) // 2, 56, 44)
        return A.shared_element(mover, to=target, **o)
    return _pcard(i18n, tr("shared_element.title"), tr("shared_element.hint"),
                  st, _play, _S(tr, _SPECS_SHARED))


# ---------------------------------------------------------------------------
# 卡片编排
# ---------------------------------------------------------------------------

def _entrance_cards(i18n, tr) -> list:
    """入场类卡片（1-9）。"""
    return [
        _block_card(i18n, tr, "fade_in", A.fade_in, _SPECS_FADE_IN),
        _fade_out_card(i18n, tr),
        _block_card(i18n, tr, "slide_in", A.slide_in, _SPECS_SLIDE_IN),
        _block_card(i18n, tr, "zoom_in", A.zoom_in, _SPECS_ZOOM_IN),
        _block_card(i18n, tr, "spring_pop", A.spring_pop, _SPECS_SPRING_POP),
        _badge_card(i18n, tr),
        _stagger_card(i18n, tr),
        _block_card(i18n, tr, "blur_in", A.blur_in, _SPECS_BLUR_IN),
        _block_card(i18n, tr, "mask_reveal", A.mask_reveal, _SPECS_MASK_REVEAL),
    ]


def _interaction_cards(i18n, tr) -> list:
    """交互类卡片（10-13）。"""
    return [_hover_card(i18n, tr), _morph_card(i18n, tr), _ripple_card(i18n, tr),
            _switch_card(i18n, tr)]


def _emphasis_cards(i18n, tr) -> list:
    """强调类卡片（14-18）。"""
    return [
        _block_card(i18n, tr, "pulse", A.pulse, _SPECS_PULSE),
        _block_card(i18n, tr, "bounce", A.bounce, _SPECS_BOUNCE, color="success"),
        _block_card(i18n, tr, "swing", A.swing, _SPECS_SWING, color="warning"),
        _block_card(i18n, tr, "shake", A.shake, _SPECS_SHAKE, color="danger"),
        _flash_card(i18n, tr),
    ]


def _loop_cards(i18n, tr) -> list:
    """循环类卡片（19-23）：参数变化即时重启。"""
    return [
        _float_card(i18n, tr),
        _block_card(i18n, tr, "pulse_glow", A.pulse_glow, _SPECS_PULSE_GLOW,
                    continuous=True),
        _block_card(i18n, tr, "breathing", A.breathing, _SPECS_BREATHING,
                    continuous=True),
        _gflow_card(i18n, tr),
        _gtext_card(i18n, tr),
    ]


def _transition_cards(i18n, tr) -> list:
    """过渡 / 变形类卡片（24-28）。"""
    return [_cross_fade_card(i18n, tr), _page_trans_card(i18n, tr),
            _slide_trans_card(i18n, tr), _container_morph_card(i18n, tr),
            _shared_card(i18n, tr)]


def _cards(i18n) -> list:
    """按演示顺序构建全部 28 张参数化卡片。"""
    tr = bind_tr(i18n, "anim_property")
    return (_entrance_cards(i18n, tr) + _interaction_cards(i18n, tr)
            + _emphasis_cards(i18n, tr) + _loop_cards(i18n, tr)
            + _transition_cards(i18n, tr))


def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """构建「动画 · 属性」演示页（3 列卡片网格）。"""
    tr = bind_tr(i18n, "anim_property")
    box = Section(tr("sec"))
    grid_host = QWidget()
    grid = QGridLayout(grid_host)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(12)
    for i, card in enumerate(_cards(i18n)):
        grid.addWidget(card, i // 3, i % 3)
    box.layout().addWidget(grid_host)
    return make_page(tr("title"), tr("desc"), [box])
