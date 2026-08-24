# -*- coding: utf-8 -*-
"""基础控件全家福：经全局 QSS 美化后的 Qt 原生控件总览。

覆盖按钮 / 输入 / 数字日期 / 下拉 / 滑块表盘 / 进度数码 / 文本显示 /
容器 / 数据视图 / 窗口部件，以及标准对话框（QMessageBox / QFileDialog /
QColorDialog / QFontDialog / QInputDialog）的触发按钮。亮 / 暗主题自动换肤。
文案经 ``bind_tr`` 按 ``basic_widgets`` 分组取词。
"""

from typing import Optional

from PySide6.QtCore import Qt, QDate, QTime, QDateTime
from PySide6.QtGui import QAction, QColor
from PySide6.QtWidgets import (
    QCalendarWidget,
    QColorDialog,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFileDialog,
    QFontComboBox,
    QFontDialog,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QKeySequenceEdit,
    QLCDNumber,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSlider,
    QSpinBox,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QTextEdit,
    QTimeEdit,
    QToolBar,
    QToolBox,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QFont

from InstructionX_UIKit.theme import set_property

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, col, hint_label, make_page, row

__all__ = ["create_page"]


def _buttons_section(tr):
    box = Section(tr("sec.buttons"))
    box.layout().addWidget(row(
        QPushButton(tr("btn.default")),
        _v(tr("btn.primary"), "primary"),
        _v(tr("btn.danger"), "danger"),
        _v(tr("btn.disabled"), None, False)))
    tb1 = QToolButton(); tb1.setText(tr("tb.tool"))
    tb2 = QToolButton(); tb2.setText(tr("tb.menu"))
    tb2.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    box.layout().addWidget(row(tb1, tb2))
    return box


def _v(text, variant, enabled=True):
    b = QPushButton(text)
    if variant:
        set_property(b, "variant", variant)
    b.setEnabled(enabled)
    return b


def _text_inputs_section(tr):
    box = Section(tr("sec.text_inputs"))
    le = QLineEdit(tr("le.text"))
    le.setMinimumWidth(200)
    box.layout().addWidget(row(le, QLineEdit(tr("le.placeholder"))))
    te = QTextEdit(tr("te.text"))
    te.setFixedHeight(90)
    pe = QPlainTextEdit(tr("pe.text"))
    pe.setFixedHeight(90)
    box.layout().addWidget(row(te, pe))
    return box


def _number_date_section(tr):
    box = Section(tr("sec.number_date"))
    box.layout().addWidget(row(
        QSpinBox(value=42), QDoubleSpinBox(value=3.14),
        QKeySequenceEdit()))
    box.layout().addWidget(row(
        QDateEdit(QDate.currentDate()),
        QTimeEdit(QTime.currentTime()),
        QDateTimeEdit(QDateTime.currentDateTime())))
    return box


def _combo_section(tr):
    box = Section(tr("sec.combo"))
    cb = QComboBox()
    cb.addItems([tr(f"cb.item.{i}") for i in range(1, 4)])
    fcb = QFontComboBox()
    fcb.setMinimumWidth(200)
    box.layout().addWidget(row(cb, fcb))
    return box


def _slider_dial_section(tr):
    box = Section(tr("sec.slider_dial"))
    sl = QSlider(Qt.Horizontal, value=55)
    sl.setMinimumWidth(240)
    dial = QDial(value=40)
    box.layout().addWidget(row(sl, dial))
    pb = QProgressBar(value=65)
    pb.setMinimumWidth(240)
    pb.setFormat("%p%")
    lcd = QLCDNumber()
    lcd.display("1234")
    lcd.setFixedHeight(60)
    box.layout().addWidget(row(pb, lcd))
    return box


def _display_section(tr):
    box = Section(tr("sec.display"))
    tb = QTextBrowser()
    tb.setHtml(tr("tb.html"))
    tb.setFixedHeight(180)
    tb.setMinimumWidth(300)
    cal = QCalendarWidget()
    cal.setFixedSize(360, 260)
    box.layout().addWidget(row(tb, cal))
    return box


def _container_section(tr):
    box = Section(tr("sec.container"))
    gb = QGroupBox(tr("gb.title"))
    gl = QVBoxLayout(gb)
    gl.addWidget(QLabel(tr("gb.content")))
    gl.addWidget(QPushButton(tr("gb.button")))
    tabs = QTabWidget()
    for i in range(1, 4):
        name = tr(f"tab.{i}")
        tabs.addTab(QLabel(tr("tab.content", name=name), alignment=Qt.AlignCenter), name)
    tabs.setFixedHeight(150)
    toolbox = QToolBox()
    toolbox.addItem(QLabel(tr("drawer.1.content"), alignment=Qt.AlignCenter),
                    tr("drawer.1"))
    toolbox.addItem(QLabel(tr("drawer.2.content"), alignment=Qt.AlignCenter),
                    tr("drawer.2"))
    toolbox.setFixedHeight(150)
    box.layout().addWidget(row(gb, tabs, toolbox))
    return box


def _views_section(tr):
    box = Section(tr("sec.views"))
    lw = QListWidget()
    lw.addItems([tr(f"lw.item.{i}") for i in range(1, 5)])
    lw.setCurrentRow(1)
    tree = QTreeWidget()
    tree.setHeaderLabels([tr("tree.header.name"), tr("tree.header.value")])
    for i in range(3):
        it = QTreeWidgetItem([tr("tree.node", n=i + 1), str(i)])
        it.addChild(QTreeWidgetItem([tr("tree.child", n=i + 1), "x"]))
        tree.addTopLevelItem(it)
    tree.expandAll()
    table = QTableWidget(3, 3)
    table.setHorizontalHeaderLabels([tr(f"table.col.{i}") for i in range(1, 4)])
    for r in range(3):
        for c in range(3):
            table.setItem(r, c, QTableWidgetItem(f"{r + 1},{c + 1}"))
    for w in (lw, tree, table):
        w.setFixedSize(240, 190)
    box.layout().addWidget(row(lw, tree, table))
    return box


def _window_menus(win, tr) -> None:
    """填充演示主窗口的菜单栏（文件 / 编辑）。"""
    mb = win.menuBar()
    m_file = mb.addMenu(tr("menu.file"))
    m_file.addAction(tr("menu.file.new"))
    m_file.addAction(tr("menu.file.open"))
    m_edit = mb.addMenu(tr("menu.edit"))
    m_edit.addAction(tr("menu.edit.undo"))


def _window_toolbar(win, tr) -> None:
    """填充演示主窗口的工具栏（新建 / 保存 / 帮助）。"""
    tb = QToolBar(tr("toolbar.title"))
    tb.addAction(QAction(tr("toolbar.new"), win))
    tb.addAction(QAction(tr("toolbar.save"), win))
    tb.addSeparator()
    tb.addAction(QAction(tr("toolbar.help"), win))
    win.addToolBar(tb)


def _window_parts_section(tr):
    box = Section(tr("sec.window_parts"))
    win = QMainWindow()
    _window_menus(win, tr)
    _window_toolbar(win, tr)
    win.setCentralWidget(QLabel(tr("central"), alignment=Qt.AlignCenter))
    sb = QStatusBar()
    sb.showMessage(tr("status.ready"))
    win.setStatusBar(sb)
    win.setFixedHeight(240)
    box.layout().addWidget(win)
    return box


def _dialog_handlers(page, tr) -> list:
    """系统对话框演示的 (按钮文案, 触发函数) 表。"""
    return [
        ("QMessageBox", lambda: QMessageBox.information(
            page, "QMessageBox", tr("dlg.msg.text"))),
        ("QFileDialog", lambda: QFileDialog.getOpenFileName(
            page, tr("dlg.file.title"))),
        ("QColorDialog", lambda: QColorDialog.getColor(
            QColor("#3F5E8C"), page, tr("dlg.color.title"))),
        ("QFontDialog", lambda: QFontDialog.getFont(
            page, tr("dlg.font.title"))),
        ("QInputDialog", lambda: QInputDialog.getText(
            page, "QInputDialog", tr("dlg.input.label"))),
    ]


def _dialogs_section(page, tr):
    box = Section(tr("sec.dialogs"))
    btns = []
    for text, fn in _dialog_handlers(page, tr):
        b = QPushButton(text)
        b.clicked.connect(fn)
        btns.append(b)
    box.layout().addWidget(row(*btns))
    box.layout().addWidget(hint_label(tr("dlg.hint"), role="tertiary"))
    return box


def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    tr = bind_tr(i18n, "basic_widgets")
    sections = [
        _buttons_section(tr),
        _text_inputs_section(tr),
        _number_date_section(tr),
        _combo_section(tr),
        _slider_dial_section(tr),
        _display_section(tr),
        _container_section(tr),
        _views_section(tr),
        _window_parts_section(tr),
    ]
    page = make_page(tr("title"), tr("desc"), sections)
    # 对话框 section 需要页面作为 parent，最后追加
    content = page.widget()
    content.layout().insertWidget(
        content.layout().count() - 1, _dialogs_section(content, tr))
    return page
