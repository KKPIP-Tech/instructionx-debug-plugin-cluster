# -*- coding: utf-8 -*-
"""ui_demo 测试共享辅助：NAV 键 → 中文标题映射。

NAV 注册表为 ``[(分类键, [(页面键, 工厂), ...]), ...]``，分类/页面标题
不落字面量，由取词门面按派生键（``cat.<分类键>`` / ``page.<页面键>``）
翻译。测试侧需要中文标题时直接解析 text/zh.xml 的 nav 分组，
与运行路径同一数据源，避免双份硬编码漂移。
"""

import xml.etree.ElementTree as ET
from pathlib import Path

#: ui_demo 默认语言文件（nav 分组承载全部分类/页面标题）
_ZH_XML = (
    Path(__file__).resolve().parents[2] / "ui_demo" / "text" / "zh.xml"
)


def nav_title_map() -> dict:
    """读取 zh.xml nav 分组，返回 {键: 中文标题}（如 'cat.tokens' / 'page.charts'）。"""
    root = ET.parse(_ZH_XML).getroot()
    for group in root.findall("group"):
        if group.get("name") == "nav":
            return {text.get("key"): text.text for text in group.findall("text")}
    raise AssertionError("zh.xml 缺少 nav 分组")
