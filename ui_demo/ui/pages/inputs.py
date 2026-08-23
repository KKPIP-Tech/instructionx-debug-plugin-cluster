# -*- coding: utf-8 -*-
"""组件 · 输入演示页：20 个输入与按钮组件，每组件一页，覆盖主要变体。

页面 = 标题 + 说明 + 分区演示（变体 / 尺寸 / 状态），紧凑排布。
所有组件基于全局 QSS 与令牌，亮 / 暗主题切换自动换肤。
文案经 ``bind_tr`` 按 ``inputs`` 分组取词（键前缀 = 组件导航键）。
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from InstructionX_UIKit.components.auto_complete import AutoComplete
from InstructionX_UIKit.components.button import Button
from InstructionX_UIKit.components.cascader import Cascader
from InstructionX_UIKit.components.checkbox import CheckBox
from InstructionX_UIKit.components.color_picker import ColorPicker
from InstructionX_UIKit.components.combo_box import ComboBox
from InstructionX_UIKit.components.date_picker import DatePicker
from InstructionX_UIKit.components.form import FormLayout
from InstructionX_UIKit.components.icon_button import IconButton
from InstructionX_UIKit.components.line_edit import LineEdit
from InstructionX_UIKit.components.radio import RadioButton, RadioGroup
from InstructionX_UIKit.components.rating import Rating
from InstructionX_UIKit.components.segmented import SegmentedControl
from InstructionX_UIKit.components.slider import Slider
from InstructionX_UIKit.components.spin_box import DoubleSpinBox, SpinBox
from InstructionX_UIKit.components.switch import Switch
from InstructionX_UIKit.components.text_area import TextArea
from InstructionX_UIKit.components.time_picker import TimePicker
from InstructionX_UIKit.components.transfer import Transfer
from InstructionX_UIKit.components.upload import UploadWidget

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, hint_label, make_page, row

#: 圆形按钮三档边长（sm/md/lg，见 create_button_page 注释）
_CIRCLE_SIZES = (24, 32, 40)


def _disabled(widget) -> QWidget:
    widget.setEnabled(False)
    return widget


def _tr_of(i18n):
    """本页统一取词闭包（分组 ``inputs``）。"""
    return bind_tr(i18n, "inputs")


# ---------------------------------------------------------------------------
# 各组件页面
# ---------------------------------------------------------------------------

def create_button_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    variants = Section(tr("button.sec.variant"))
    variants.layout().addWidget(row(*[
        Button(tr(f"button.variant.{v}"), variant=v) for v in
        ("primary", "default", "dashed", "text", "link", "danger")]))
    sizes = Section(tr("button.sec.size"))
    sizes.layout().addWidget(row(
        Button(tr("button.size.sm"), size="sm"),
        Button(tr("button.size.md"), size="md"),
        Button(tr("button.size.lg"), size="lg"),
        Button(tr("button.size.loading"), variant="primary", loading=True),
        _disabled(Button(tr("button.size.disabled"), variant="primary"))))
    sizes.layout().addWidget(Button(tr("button.size.block"), variant="primary", block=True))
    shapes = Section(tr("button.sec.shape"))
    # 圆形按钮：QSS 约定「配合组件固定宽=高」，此处按 sm/md/lg 边长
    # 24/32/40 固定为正方形，否则 "+" 单字按钮宽度由字宽决定，会渲染成
    # 细长条。短文本（≤2 字符）圆形按钮由组件按墨迹盒自绘，"+" 在三档
    # 尺寸下均水平 + 垂直精确居中。
    circles = []
    for edge, size in zip(_CIRCLE_SIZES, ("sm", "md", "lg")):
        btn = Button("+", shape="circle", variant="primary", size=size)
        btn.setFixedSize(edge, edge)
        circles.append(btn)
    shapes.layout().addWidget(row(
        Button(tr("button.shape.round"), shape="round"), *circles,
        Button(tr("button.shape.pill"), shape="round", variant="primary")))
    return make_page(tr("button.title"), tr("button.desc"),
                     [variants, sizes, shapes])


def create_icon_button_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s1 = Section(tr("icon_button.sec.icons"))
    s1.layout().addWidget(row(
        IconButton(text="+", variant="primary", shape="circle"),
        IconButton(text="×", variant="danger", shape="circle"),
        IconButton(text="?", shape="circle"),
        IconButton(text="★", variant="default"),
        IconButton(text="⚙", shape="round", variant="primary")))
    s2 = Section(tr("icon_button.sec.size"))
    s2.layout().addWidget(row(
        IconButton(text="+", size="sm"), IconButton(text="+", size="md"),
        IconButton(text="+", size="lg"),
        _disabled(IconButton(text="+", variant="primary", shape="circle"))))
    return make_page(tr("icon_button.title"), tr("icon_button.desc"), [s1, s2])


def create_checkbox_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("checkbox.sec.state"))
    tri = CheckBox(tr("checkbox.state.partial"), tristate=True)
    tri.set_check_state(Qt.PartiallyChecked)
    s.layout().addWidget(row(
        CheckBox(tr("checkbox.state.unchecked")),
        CheckBox(tr("checkbox.state.checked"), checked=True), tri,
        _disabled(CheckBox(tr("checkbox.state.disabled"), checked=True))))
    return make_page(tr("checkbox.title"), tr("checkbox.desc"), [s])


def create_radio_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("radio.sec.group"))
    group = RadioGroup()
    radios = [group.add_button(tr(f"radio.opt.{i}"), id=i) for i in range(1, 4)]
    group.set_checked_id(2)
    s.layout().addWidget(row(*(radios + [_disabled(RadioButton(tr("radio.disabled")))])))
    return make_page(tr("radio.title"), tr("radio.desc"), [s])


def create_switch_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("switch.sec"))
    s.layout().addWidget(row(
        Switch(checked=True), Switch(checked=False),
        Switch(checked=True, size="sm"),
        _disabled(Switch(checked=True))))
    return make_page(tr("switch.title"), tr("switch.desc"), [s])


def create_line_edit_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s1 = Section(tr("line_edit.sec.basic"))
    le1 = LineEdit(placeholder=tr("line_edit.ph.username"), clearable=True)
    le2 = LineEdit("user", clearable=True)
    le2.set_prefix_icon("@")
    le2.set_suffix_icon(".com")
    for w in (le1, le2):
        w.setMinimumWidth(200)
    s1.layout().addWidget(row(le1, le2))
    s2 = Section(tr("line_edit.sec.state"))
    pwd = LineEdit("secret")
    pwd.set_password_mode(True)
    err = LineEdit(tr("line_edit.err.content"))
    err.set_error(True)
    pwd.setMinimumWidth(180)
    err.setMinimumWidth(180)
    s2.layout().addWidget(row(pwd, err, _disabled(LineEdit(tr("line_edit.disabled")))))
    s2.layout().addWidget(row(LineEdit(placeholder=tr("line_edit.ph.sm"), size="sm"),
                              LineEdit(placeholder=tr("line_edit.ph.lg"), size="lg")))
    return make_page(tr("line_edit.title"), tr("line_edit.desc"), [s1, s2])


def create_text_area_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("text_area.sec"))
    ta = TextArea(placeholder=tr("text_area.ph.intro"),
                  auto_height=True, min_rows=2, max_rows=5,
                  max_length=120, show_count=True)
    ta.setPlainText(tr("text_area.sample"))
    ta.setMinimumWidth(360)
    s.layout().addWidget(row(ta, _disabled(TextArea(placeholder=tr("text_area.ph.disabled")))))
    return make_page(tr("text_area.title"), tr("text_area.desc"), [s])


def create_spin_box_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("spin_box.sec"))
    s.layout().addWidget(row(
        SpinBox(minimum=0, maximum=99, value=5, size="sm"),
        SpinBox(minimum=0, maximum=99, value=42),
        SpinBox(minimum=0, maximum=99, value=8, size="lg"),
        DoubleSpinBox(minimum=0, maximum=99, value=19.9,
                      suffix=" " + tr("spin_box.suffix")),
        _disabled(SpinBox(value=7))))
    return make_page(tr("spin_box.title"), tr("spin_box.desc"), [s])


def create_combo_box_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("combo_box.sec"))
    cities = [tr("combo_box.city.beijing"), tr("combo_box.city.shanghai"),
              tr("combo_box.city.guangzhou")]
    fruits = [tr("combo_box.fruit.apple"), tr("combo_box.fruit.banana"),
              tr("combo_box.fruit.orange")]
    s.layout().addWidget(row(
        ComboBox(cities, size="sm"),
        ComboBox(cities),
        ComboBox(fruits, searchable=True,
                 placeholder=tr("combo_box.ph.fruit"), size="lg"),
        _disabled(ComboBox([tr("combo_box.item.disabled")]))))
    return make_page(tr("combo_box.title"), tr("combo_box.desc"), [s])


def create_slider_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("slider.sec"))
    sl = Slider(minimum=0, maximum=100, value=45)
    sl.set_ticks(10)
    sl.setMinimumWidth(320)
    dis = Slider(value=30)
    dis.setMinimumWidth(220)
    dis.setEnabled(False)
    s.layout().addWidget(row(sl, dis))
    return make_page(tr("slider.title"), tr("slider.desc"), [s])


def create_date_picker_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("date_picker.sec"))
    dp = DatePicker()
    dp.set_date_str("2025-06-15")
    s.layout().addWidget(row(dp, DatePicker(size="sm"), _disabled(DatePicker())))
    return make_page(tr("date_picker.title"), tr("date_picker.desc"), [s])


def create_time_picker_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("time_picker.sec"))
    tp = TimePicker()
    tp.set_time_str("09:30:00")
    s.layout().addWidget(row(tp, TimePicker(size="sm"), _disabled(TimePicker())))
    return make_page(tr("time_picker.title"), tr("time_picker.desc"), [s])


def create_rating_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("rating.sec"))
    s.layout().addWidget(row(
        Rating(value=3.5, allow_half=True),
        Rating(value=4, read_only=True),
        _disabled(Rating(value=3, read_only=True))))
    return make_page(tr("rating.title"), tr("rating.desc"), [s])


def create_color_picker_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("color_picker.sec"))
    s.layout().addWidget(row(
        ColorPicker("#3F5E8C"), ColorPicker("#3E7E5F", size="sm"),
        _disabled(ColorPicker("#98A0AC"))))
    return make_page(tr("color_picker.title"), tr("color_picker.desc"), [s])


def create_auto_complete_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("auto_complete.sec"))
    fruits = [tr(f"auto_complete.fruit.{k}") for k in
              ("apple", "banana", "orange", "apple_pie", "grape")]
    ac = AutoComplete(fruits, placeholder=tr("auto_complete.ph"))
    ac.setMinimumWidth(240)
    s.layout().addWidget(row(
        ac, _disabled(AutoComplete(["x"], placeholder=tr("auto_complete.ph.disabled")))))
    s.layout().addWidget(hint_label(tr("auto_complete.hint"), role="tertiary"))
    return make_page(tr("auto_complete.title"), tr("auto_complete.desc"), [s])


def create_cascader_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("cascader.sec"))
    cas = Cascader([
        {"value": "zj", "label": tr("cascader.region.zj"), "children": [
            {"value": "hz", "label": tr("cascader.region.hz")},
            {"value": "nb", "label": tr("cascader.region.nb")}]},
        {"value": "gd", "label": tr("cascader.region.gd"), "children": [
            {"value": "gz", "label": tr("cascader.region.gz")},
            {"value": "sz", "label": tr("cascader.region.sz")}]},
    ])
    cas.set_path(["zj", "hz"])
    s.layout().addWidget(row(cas, _disabled(Cascader(
        [{"value": "x", "label": tr("cascader.none")}]))))
    return make_page(tr("cascader.title"), tr("cascader.desc"), [s])


def create_transfer_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("transfer.sec"))
    fruits = [tr(f"transfer.fruit.{k}") for k in
              ("apple", "banana", "orange", "grape", "watermelon")]
    widget = Transfer(fruits)
    widget.set_target_items([tr("transfer.fruit.banana"), tr("transfer.fruit.grape")])
    s.layout().addWidget(widget)
    return make_page(tr("transfer.title"), tr("transfer.desc"), [s])


def create_upload_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("upload.sec"))
    up = UploadWidget()
    up.add_files([tr(f"upload.file.{k}") for k in ("report", "data", "design")])
    up.setMinimumWidth(400)
    s.layout().addWidget(row(up))
    s.layout().addWidget(hint_label(tr("upload.hint"), role="tertiary"))
    return make_page(tr("upload.title"), tr("upload.desc"), [s])


def create_segmented_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("segmented.sec"))
    seg2 = SegmentedControl([tr("segmented.mode.list"), tr("segmented.mode.card"),
                             tr("segmented.mode.disabled")], current=0, size="sm")
    seg2.set_item_enabled(2, False)
    s.layout().addWidget(row(
        SegmentedControl([tr(f"segmented.period.{k}") for k in
                          ("day", "week", "month", "year")], current=1),
        seg2,
        _disabled(SegmentedControl([tr("segmented.ab.a"), tr("segmented.ab.b")],
                                   current=0))))
    return make_page(tr("segmented.title"), tr("segmented.desc"), [s])


def create_form_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = _tr_of(i18n)
    s = Section(tr("form.sec"))
    holder = QWidget()
    form = FormLayout(holder)
    user = LineEdit("abc")
    form.add_row(tr("form.label.user"), user, required=True,
                 validator=lambda v: len(v) >= 3 or tr("form.err.min_len"))
    mail = LineEdit("bad")
    form.add_row(tr("form.label.mail"), mail, required=True,
                 validator=lambda v: "@" in v or tr("form.err.mail"))
    form.add_row(tr("form.label.note"), TextArea(auto_height=True, min_rows=2, max_rows=3))
    form.validate_all()  # 触发错误提示行
    holder.setMinimumWidth(420)
    s.layout().addWidget(holder)
    s.layout().addWidget(hint_label(tr("form.hint"), role="tertiary"))
    return make_page(tr("form.title"), tr("form.desc"), [s])


#: 输入组件页注册表：(导航键, 页面工厂)；标题由 MainWidget 经 ``nav:page.<键>`` 取词
INPUT_PAGES = [
    ("button", create_button_page),
    ("icon_button", create_icon_button_page),
    ("checkbox", create_checkbox_page),
    ("radio", create_radio_page),
    ("switch", create_switch_page),
    ("line_edit", create_line_edit_page),
    ("text_area", create_text_area_page),
    ("spin_box", create_spin_box_page),
    ("combo_box", create_combo_box_page),
    ("slider", create_slider_page),
    ("date_picker", create_date_picker_page),
    ("time_picker", create_time_picker_page),
    ("rating", create_rating_page),
    ("color_picker", create_color_picker_page),
    ("auto_complete", create_auto_complete_page),
    ("cascader", create_cascader_page),
    ("transfer", create_transfer_page),
    ("upload", create_upload_page),
    ("segmented", create_segmented_page),
    ("form", create_form_page),
]
