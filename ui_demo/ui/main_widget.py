"""UI Demo Main Widget"""

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QPlainTextEdit,
    QComboBox, QCheckBox, QRadioButton, QSlider, QProgressBar,
    QSpinBox, QDoubleSpinBox, QGroupBox, QTabWidget, QListWidget,
    QTableWidget, QTreeWidget, QMenuBar, QMenu, QToolBar,
    QScrollArea, QFrame, QSplitter, QButtonGroup, QTreeWidgetItem,
    QTableWidgetItem, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, QTimer
from utils.style_qss.registry import QssRegistry


def _load_config() -> dict:
    """Load plugin configuration from config/default.json"""
    config_path = Path(__file__).parent.parent / "config" / "default.json"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


class MainWidget(QWidget):
    """UI Demo Main Widget"""

    def __init__(self, parent=None, service=None, plugin=None):
        super().__init__(parent)
        self.setObjectName("UIDemoWidget")
        self._service = service
        self._plugin = plugin
        self.progress_bar: QProgressBar | None = None
        self._timer: QTimer | None = None
        self._progress_step: int = 0
        self._radio_group: QButtonGroup | None = None
        self._config: dict = _load_config()
        self._parent_widget: QWidget | None = parent
        self._setup_ui()
        self._load_plugin_style()

    def _load_plugin_style(self):
        """加载插件 QSS 样式文件"""
        style_dir = Path(__file__).parent.parent / "style"
        if not style_dir.exists():
            return
        qss_parts = []
        for qss_file in sorted(style_dir.glob("*.qss")):
            raw = qss_file.read_text(encoding="utf-8")
            qss_parts.append(QssRegistry.apply_variables(raw))
        if qss_parts:
            self._qss_content = "\n".join(qss_parts)
            self.setStyleSheet(self._qss_content)
            self.destroyed.connect(self._unload_plugin_style)

    def _unload_plugin_style(self):
        """卸载插件 QSS 样式（widget 销毁时调用）"""
        self.setStyleSheet("")

    def _setup_ui(self):
        """Set up the main UI layout"""
        main_layout = QVBoxLayout(self)
        self._apply_main_layout_style(main_layout)
        scroll_area = self._build_scroll_area()
        main_layout.addWidget(scroll_area)

    def _apply_main_layout_style(self, layout: QVBoxLayout):
        """Apply style to main layout"""
        layout_cfg = self._config.get("layout", {})
        margin = layout_cfg.get("content_margin", 10)
        spacing = layout_cfg.get("spacing", 10)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)

    def _build_scroll_area(self) -> QScrollArea:
        """Build the main scroll area"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setWidget(self._build_scroll_content())
        return scroll_area

    def _build_scroll_content(self) -> QWidget:
        """Build the scrollable content widget"""
        layout_cfg = self._config.get("layout", {})
        margin = layout_cfg.get("content_margin", 10)
        spacing = layout_cfg.get("spacing", 10)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(spacing)
        layout.addWidget(self._build_main_tabs())
        layout.addWidget(self._build_status_bar())
        return content

    def _build_main_tabs(self) -> QTabWidget:
        """Build the main tab widget"""
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._create_basic_tab(), "Basic")
        tabs.addTab(self._create_input_tab(), "Input")
        tabs.addTab(self._create_container_tab(), "Container")
        tabs.addTab(self._create_list_tab(), "List")
        tabs.addTab(self._create_menu_toolbar_tab(), "Menu/Toolbar")
        return tabs

    def _build_status_bar(self) -> QStatusBar:
        """Build the status bar"""
        bar = QStatusBar()
        bar.showMessage("Ready - Controls Demo")
        return bar

    def _add_title(self, layout, text: str):
        """Add title label to a layout"""
        title = QLabel(text)
        title.setProperty("class", "panel-title")
        layout.addWidget(title)

    def _create_basic_tab(self) -> QWidget:
        """Create basic controls tab"""
        layout_cfg = self._config.get("layout", {})
        progress_cfg = self._config.get("progress", {})
        tabs_cfg = self._config.get("tabs", {})
        margin = tabs_cfg.get("basic_margin", 5)
        group_spacing = layout_cfg.get("group_spacing", 15)
        row_height = layout_cfg.get("slider_row_height", 40)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(group_spacing)

        self._add_title(layout, "Basic Controls Demo")
        layout.addWidget(self._create_button_group())
        layout.addWidget(self._create_checkbox_group())
        layout.addWidget(self._create_slider_progress_group(row_height, progress_cfg))
        layout.addStretch()
        return widget

    def _create_button_group(self) -> QGroupBox:
        """Create button group"""
        group = QGroupBox("Buttons (QPushButton)")
        group_layout = QVBoxLayout()
        group_layout.addLayout(self._make_button_row_1())
        group_layout.addLayout(self._make_button_row_2())
        group.setLayout(group_layout)
        return group

    def _make_button_row_1(self) -> QHBoxLayout:
        """Create first row of buttons"""
        row = QHBoxLayout()
        row.addWidget(self._make_button("Normal", self._on_normal_clicked))
        row.addWidget(self._make_button("Primary", self._on_primary_clicked, "primary"))
        row.addWidget(self._make_button("Danger", self._on_danger_clicked, "danger"))
        row.addWidget(self._make_button("Success", self._on_success_clicked, "success"))
        return row

    def _make_button_row_2(self) -> QHBoxLayout:
        """Create second row of buttons"""
        row = QHBoxLayout()
        row.addWidget(self._make_button("Outline", self._on_outline_clicked, "outline"))
        row.addWidget(self._make_button("Subtle", self._on_subtle_clicked, "subtle"))
        disabled = QPushButton("Disabled")
        disabled.setEnabled(False)
        row.addWidget(disabled)
        row.addStretch()
        return row

    def _make_button(self, text: str, handler, cls: str = None) -> QPushButton:
        """Create styled button"""
        btn = QPushButton(text)
        btn.clicked.connect(handler)
        if cls:
            btn.setProperty("class", cls)
        return btn

    def _create_checkbox_group(self) -> QGroupBox:
        """Create checkbox and radio button group"""
        group = QGroupBox("CheckBox (QCheckBox) and RadioButton (QRadioButton)")
        layout = QHBoxLayout()
        layout.addLayout(self._build_checkboxes())
        layout.addSpacing(30)
        layout.addLayout(self._build_radios())
        layout.addStretch()
        group.setLayout(layout)
        return group

    def _build_checkboxes(self) -> QHBoxLayout:
        """Build checkbox row"""
        row = QHBoxLayout()
        check1 = QCheckBox("Check 1")
        check1.setChecked(True)
        check2 = QCheckBox("Check 2")
        check3 = QCheckBox("Tri-state")
        check3.setTristate(True)
        check3.setCheckState(Qt.CheckState.PartiallyChecked)
        row.addWidget(check1)
        row.addWidget(check2)
        row.addWidget(check3)
        return row

    def _build_radios(self) -> QHBoxLayout:
        """Build radio button row"""
        row = QHBoxLayout()
        self._radio_group = QButtonGroup()
        radio1 = QRadioButton("Option A")
        radio1.setChecked(True)
        radio2 = QRadioButton("Option B")
        radio3 = QRadioButton("Option C")
        self._radio_group.addButton(radio1)
        self._radio_group.addButton(radio2)
        self._radio_group.addButton(radio3)
        row.addWidget(radio1)
        row.addWidget(radio2)
        row.addWidget(radio3)
        return row

    def _create_slider_progress_group(self, row_height: int, progress_cfg: dict) -> QGroupBox:
        """Create slider and progress bar group"""
        default_val = progress_cfg.get("slider_default", 50)
        group = QGroupBox("Slider (QSlider) and ProgressBar (QProgressBar)")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)
        layout.setRowMinimumHeight(0, row_height)
        layout.setRowMinimumHeight(1, row_height)

        layout.addWidget(QLabel("Horizontal:"), 0, 0)
        layout.addWidget(self._build_h_slider(default_val), 0, 1)
        layout.addWidget(QLabel("Vertical:"), 0, 2)
        layout.addWidget(self._build_v_slider(default_val), 0, 3, 3, 1)
        layout.addWidget(QLabel("Progress:"), 1, 0)
        layout.addWidget(self._build_progress_bar(progress_cfg), 1, 1)
        layout.addLayout(self._build_progress_buttons(progress_cfg), 2, 1)

        group.setLayout(layout)
        return group

    def _build_h_slider(self, default_val: int) -> QSlider:
        """Build horizontal slider"""
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(default_val)
        return slider

    def _build_v_slider(self, default_val: int) -> QSlider:
        """Build vertical slider"""
        slider = QSlider(Qt.Orientation.Vertical)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.setValue(default_val)
        slider.setMinimumWidth(32)
        return slider

    def _build_progress_bar(self, progress_cfg: dict) -> QProgressBar:
        """Build progress bar"""
        bar = QProgressBar()
        bar.setValue(progress_cfg.get("default_value", 60))
        self.progress_bar = bar
        return bar

    def _build_progress_buttons(self, progress_cfg: dict) -> QHBoxLayout:
        """Build progress control buttons"""
        layout = QHBoxLayout()
        step = progress_cfg.get("step", 10)
        layout.addWidget(self._make_button("-10", lambda: self._adjust_progress(-step)))
        layout.addWidget(self._make_button("+10", lambda: self._adjust_progress(step)))
        layout.addWidget(self._make_button("Animate", self._start_progress_animation))
        return layout

    def _create_input_tab(self) -> QWidget:
        """Create input controls tab"""
        layout_cfg = self._config.get("layout", {})
        tabs_cfg = self._config.get("tabs", {})
        margin = tabs_cfg.get("basic_margin", 5)
        group_spacing = layout_cfg.get("group_spacing", 15)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(group_spacing)

        self._add_title(layout, "Input Controls Demo")
        layout.addWidget(self._build_lineedit_group())
        layout.addWidget(self._build_textedit_group())
        layout.addWidget(self._build_spinbox_group())
        layout.addWidget(self._build_combobox_group())
        layout.addStretch()
        return widget

    def _build_lineedit_group(self) -> QGroupBox:
        """Build line edit group"""
        group = QGroupBox("LineEdit (QLineEdit)")
        line_layout = QVBoxLayout()
        normal = QLineEdit()
        normal.setPlaceholderText("Normal input...")
        line_layout.addWidget(normal)
        pwd = QLineEdit()
        pwd.setPlaceholderText("Password input...")
        pwd.setEchoMode(QLineEdit.EchoMode.Password)
        line_layout.addWidget(pwd)
        readonly = QLineEdit()
        readonly.setText("Read-only")
        readonly.setReadOnly(True)
        line_layout.addWidget(readonly)
        group.setLayout(line_layout)
        return group

    def _build_textedit_group(self) -> QGroupBox:
        """Build text edit group"""
        group = QGroupBox("TextEdit (QTextEdit / QPlainTextEdit)")
        text_layout = QVBoxLayout()
        text_layout.addWidget(QTextEdit())
        text_layout.addWidget(QPlainTextEdit())
        group.setLayout(text_layout)
        return group

    def _build_spinbox_group(self) -> QGroupBox:
        """Build spinbox group"""
        group = QGroupBox("SpinBox (QSpinBox / QDoubleSpinBox)")
        spin_layout = QHBoxLayout()
        spin = QSpinBox()
        spin.setRange(0, 100)
        spin.setValue(50)
        spin_layout.addWidget(QLabel("Int:"))
        spin_layout.addWidget(spin)
        dspin = QDoubleSpinBox()
        dspin.setRange(0.0, 100.0)
        dspin.setValue(50.0)
        dspin.setDecimals(2)
        spin_layout.addWidget(QLabel("Float:"))
        spin_layout.addWidget(dspin)
        spin_layout.addStretch()
        group.setLayout(spin_layout)
        return group

    def _build_combobox_group(self) -> QGroupBox:
        """Build combo box group"""
        group = QGroupBox("ComboBox (QComboBox)")
        combo_layout = QVBoxLayout()
        combo = QComboBox()
        combo.addItems(["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"])
        combo_layout.addWidget(combo)
        editable = QComboBox()
        editable.setEditable(True)
        editable.addItems(["Editable 1", "Editable 2", "Editable 3"])
        combo_layout.addWidget(editable)
        group.setLayout(combo_layout)
        return group

    def _create_container_tab(self) -> QWidget:
        """Create container controls tab"""
        layout_cfg = self._config.get("layout", {})
        tabs_cfg = self._config.get("tabs", {})
        margin = tabs_cfg.get("basic_margin", 5)
        group_spacing = layout_cfg.get("group_spacing", 15)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(group_spacing)

        self._add_title(layout, "Container Controls Demo")
        layout.addWidget(self._build_tabwidget_group())
        layout.addLayout(self._build_groupbox_row())
        layout.addWidget(self._build_scrollarea_group())
        layout.addStretch()
        return widget

    def _build_tabwidget_group(self) -> QGroupBox:
        """Build tab widget group"""
        group = QGroupBox("TabWidget (QTabWidget)")
        tab_layout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self._build_tab_page_1(), "Page 1")
        tabs.addTab(self._build_tab_page_2(), "Page 2")
        tabs.addTab(self._build_tab_page_3(), "Page 3")
        tab_layout.addWidget(tabs)
        group.setLayout(tab_layout)
        return group

    def _build_tab_page_1(self) -> QWidget:
        """Build tab page 1"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Tab 1 content"))
        layout.addWidget(QPushButton("Tab button"))
        layout.addStretch()
        return page

    def _build_tab_page_2(self) -> QWidget:
        """Build tab page 2"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Tab 2 content"))
        layout.addWidget(QComboBox())
        layout.addStretch()
        return page

    def _build_tab_page_3(self) -> QWidget:
        """Build tab page 3"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Tab 3 content"))
        layout.addWidget(QSlider(Qt.Orientation.Horizontal))
        layout.addStretch()
        return page

    def _build_groupbox_row(self) -> QHBoxLayout:
        """Build horizontal row of group boxes"""
        row = QHBoxLayout()
        row.addWidget(self._build_checkable_groupbox())
        row.addWidget(self._build_normal_groupbox())
        return row

    def _build_checkable_groupbox(self) -> QGroupBox:
        """Build checkable group box"""
        group = QGroupBox("Checkable GroupBox")
        layout = QVBoxLayout()
        layout.addWidget(QCheckBox("Option A"))
        layout.addWidget(QCheckBox("Option B"))
        layout.addWidget(QCheckBox("Option C"))
        group.setLayout(layout)
        group.setCheckable(True)
        group.setChecked(True)
        return group

    def _build_normal_groupbox(self) -> QGroupBox:
        """Build normal group box"""
        group = QGroupBox("Normal GroupBox")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("GroupBox content"))
        layout.addWidget(QPushButton("GroupBox button"))
        group.setLayout(layout)
        return group

    def _build_scrollarea_group(self) -> QGroupBox:
        """Build scroll area group"""
        group = QGroupBox("ScrollArea (QScrollArea)")
        scroll_layout = QVBoxLayout()
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_inner = QVBoxLayout()
        for i in range(10):
            scroll_inner.addWidget(QPushButton(f"Scroll button {i+1}"))
        scroll_inner.addStretch()
        scroll_widget.setLayout(scroll_inner)
        scroll_area.setWidget(scroll_widget)
        scroll_layout.addWidget(scroll_area)
        group.setLayout(scroll_layout)
        return group

    def _create_list_tab(self) -> QWidget:
        """Create list controls tab"""
        layout_cfg = self._config.get("layout", {})
        tabs_cfg = self._config.get("tabs", {})
        margin = tabs_cfg.get("basic_margin", 5)
        group_spacing = layout_cfg.get("group_spacing", 15)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(group_spacing)

        self._add_title(layout, "List Controls Demo")
        layout.addWidget(self._build_listwidget_group())
        layout.addLayout(self._build_tree_table_row())
        layout.addStretch()
        return widget

    def _build_listwidget_group(self) -> QGroupBox:
        """Build list widget group"""
        group = QGroupBox("ListWidget (QListWidget)")
        list_layout = QVBoxLayout()
        list_widget = QListWidget()
        list_widget.addItems([f"Item {i}" for i in range(1, 7)])
        list_widget.setCurrentRow(0)
        list_layout.addWidget(list_widget)
        group.setLayout(list_layout)
        return group

    def _build_treewidget_group(self) -> QGroupBox:
        """Build tree widget group"""
        group = QGroupBox("TreeWidget (QTreeWidget)")
        tree_layout = QVBoxLayout()
        tree = QTreeWidget()
        tree.setHeaderLabels(["Name", "Description"])
        root1 = QTreeWidgetItem(["Root 1", "Root node 1"])
        root1.addChild(QTreeWidgetItem(["Child 1.1", "Child"]))
        root1.addChild(QTreeWidgetItem(["Child 1.2", "Child"]))
        root2 = QTreeWidgetItem(["Root 2", "Root node 2"])
        root2.addChild(QTreeWidgetItem(["Child 2.1", "Child"]))
        tree.addTopLevelItem(root1)
        tree.addTopLevelItem(root2)
        tree.expandAll()
        tree_layout.addWidget(tree)
        group.setLayout(tree_layout)
        return group

    def _build_tablewidget_group(self) -> QGroupBox:
        """Build table widget group"""
        group = QGroupBox("TableWidget (QTableWidget)")
        table_layout = QVBoxLayout()
        table = QTableWidget(5, 3)
        table.setHorizontalHeaderLabels(["Col 1", "Col 2", "Col 3"])
        for i in range(5):
            for j in range(3):
                table.setItem(i, j, QTableWidgetItem(f"Cell {i+1},{j+1}"))
        table_layout.addWidget(table)
        group.setLayout(table_layout)
        return group

    def _build_tree_table_row(self) -> QHBoxLayout:
        """Build horizontal row with tree and table widgets"""
        row = QHBoxLayout()
        row.addWidget(self._build_treewidget_group())
        row.addWidget(self._build_tablewidget_group())
        return row

    def _create_menu_toolbar_tab(self) -> QWidget:
        """Create menu and toolbar tab"""
        layout_cfg = self._config.get("layout", {})
        tabs_cfg = self._config.get("tabs", {})
        margin = tabs_cfg.get("basic_margin", 5)
        group_spacing = layout_cfg.get("group_spacing", 15)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(group_spacing)

        self._add_title(layout, "Menu and Toolbar Demo")
        layout.addWidget(self._build_menubar_group())
        layout.addWidget(self._build_toolbar_group())
        layout.addWidget(self._build_splitter_group())
        layout.addStretch()
        return widget

    def _build_menubar_group(self) -> QGroupBox:
        """Build menu bar group"""
        group = QGroupBox("MenuBar (QMenuBar)")
        menu_layout = QVBoxLayout()
        menu_bar = QMenuBar()
        menu_bar.addMenu(self._build_file_menu())
        menu_bar.addMenu(self._build_edit_menu())
        menu_bar.addMenu(self._build_view_menu())
        menu_bar.addMenu(self._build_help_menu())
        menu_layout.addWidget(menu_bar)
        group.setLayout(menu_layout)
        return group

    def _build_file_menu(self) -> QMenu:
        """Build file menu"""
        menu = QMenu("File (&F)")
        menu.addAction("New", lambda: self._show_msg("New file"))
        menu.addAction("Open", lambda: self._show_msg("Open file"))
        menu.addSeparator()
        menu.addAction("Save", lambda: self._show_msg("Save file"))
        menu.addAction("Save As", lambda: self._show_msg("Save file as"))
        menu.addSeparator()
        menu.addAction("Exit", lambda: self._show_msg("Exit"))
        return menu

    def _build_edit_menu(self) -> QMenu:
        """Build edit menu"""
        menu = QMenu("Edit (&E)")
        menu.addAction("Undo", lambda: self._show_msg("Undo"))
        menu.addAction("Redo", lambda: self._show_msg("Redo"))
        menu.addSeparator()
        menu.addAction("Cut", lambda: self._show_msg("Cut"))
        menu.addAction("Copy", lambda: self._show_msg("Copy"))
        menu.addAction("Paste", lambda: self._show_msg("Paste"))
        return menu

    def _build_view_menu(self) -> QMenu:
        """Build view menu"""
        menu = QMenu("View (&V)")
        menu.addAction("Fullscreen", lambda: self._show_msg("Fullscreen"))
        menu.addAction("Zoom In", lambda: self._show_msg("Zoom in"))
        menu.addAction("Zoom Out", lambda: self._show_msg("Zoom out"))
        return menu

    def _build_help_menu(self) -> QMenu:
        """Build help menu"""
        menu = QMenu("Help (&H)")
        menu.addAction("About", lambda: self._show_msg("About"))
        menu.addAction("Documentation", lambda: self._show_msg("Documentation"))
        return menu

    def _build_toolbar_group(self) -> QGroupBox:
        """Build toolbar group"""
        group = QGroupBox("ToolBar (QToolBar)")
        toolbar_layout = QVBoxLayout()
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.addAction("New", lambda: self._show_msg("New"))
        toolbar.addAction("Open", lambda: self._show_msg("Open"))
        toolbar.addAction("Save", lambda: self._show_msg("Save"))
        toolbar.addSeparator()
        toolbar.addAction("Settings", lambda: self._show_msg("Settings"))
        toolbar.addAction("Help", lambda: self._show_msg("Help"))
        toolbar_layout.addWidget(toolbar)
        group.setLayout(toolbar_layout)
        return group

    def _build_splitter_group(self) -> QGroupBox:
        """Build splitter group"""
        group = QGroupBox("Splitter (QSplitter)")
        splitter_layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(QPushButton("Panel 1"))
        splitter.addWidget(QPushButton("Panel 2"))
        splitter.addWidget(QPushButton("Panel 3"))
        splitter_layout.addWidget(splitter)
        group.setLayout(splitter_layout)
        return group

    def _show_msg(self, message: str):
        """Show information message"""
        QMessageBox.information(self._parent_widget, "Info", message)

    def _adjust_progress(self, delta: int):
        """Adjust progress bar value"""
        if self.progress_bar is None:
            return
        new_val = self.progress_bar.value() + delta
        new_val = max(0, min(100, new_val))
        self.progress_bar.setValue(new_val)

    def _start_progress_animation(self):
        """Start progress bar animation"""
        progress_cfg = self._config.get("progress", {})
        interval = progress_cfg.get("animation_interval", 50)

        if self._timer is not None:
            self._timer.stop()
        self._progress_step = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_progress)
        self._timer.start(interval)

    def _update_progress(self):
        """Update progress bar during animation"""
        if self.progress_bar is None:
            return
        self._progress_step += 1
        max_val = self._config.get("progress", {}).get("max_value", 100)
        if self._progress_step > max_val:
            if self._timer is not None:
                self._timer.stop()
            self._progress_step = 0
        else:
            self.progress_bar.setValue(self._progress_step)

    def _on_normal_clicked(self):
        self._show_msg("Normal clicked")

    def _on_primary_clicked(self):
        self._show_msg("Primary clicked")

    def _on_danger_clicked(self):
        self._show_msg("Danger clicked")

    def _on_success_clicked(self):
        self._show_msg("Success clicked")

    def _on_outline_clicked(self):
        self._show_msg("Outline clicked")

    def _on_subtle_clicked(self):
        self._show_msg("Subtle clicked")
