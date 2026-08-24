# -*- coding: utf-8 -*-
"""模态对话框统一封装（ui 层）。

把插件内所有原生 ``QInputDialog`` / ``QMessageBox`` 弹窗统一为 UIKit
``Dialog``（主题感知、按钮中文文案），调用方保持阻塞式 ``exec()``
语义。文件选择对话框（``QFileDialog``）是系统级对话框，UIKit 无对应
组件，保留在 property_panel 并注释说明。
"""

from typing import Optional

from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QWidget

from InstructionX_UIKit.components import Dialog, LineEdit

__all__ = ["confirm", "prompt_text", "warn"]


def prompt_text(parent: QWidget, title: str, label: str,
                initial: str = "") -> Optional[str]:
    """单行文本输入对话框（替代 QInputDialog.getText，阻塞式）。

    参数:
        parent: 父控件（窗口模态）。
        title: 对话框标题。
        label: 输入框上方的提示文案。
        initial: 输入框初始文本（重命名场景预填旧名）。

    返回:
        去除首尾空白后的输入文本；取消或空输入返回 ``None``。
    """
    dialog = Dialog(parent, title=title)
    edit = LineEdit(initial)
    box = QWidget(dialog)
    layout = QVBoxLayout(box)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel(label, box))
    layout.addWidget(edit)
    dialog.set_content(box)
    edit.selectAll()
    edit.setFocus()
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    return edit.text().strip() or None


def confirm(parent: QWidget, title: str, text: str) -> bool:
    """确认对话框（替代 QMessageBox.question，阻塞式）；确认返回 True。"""
    dialog = Dialog(parent, title=title)
    dialog.set_text(text)
    return dialog.exec() == QDialog.DialogCode.Accepted


def warn(parent: QWidget, title: str, text: str) -> None:
    """警示对话框（替代 QMessageBox.warning，阻塞式，仅确认按钮）。"""
    dialog = Dialog(parent, title=title, show_cancel=False)
    dialog.set_text(text)
    dialog.exec()
