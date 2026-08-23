# -*- coding: utf-8 -*-
"""图表演示页：InstructionX_UIKit.charts 原生图表引擎全系列演示（ECharts 风格 set_option）。

纯 QPainter 自绘（无 WebView / 无 QtCharts 依赖），覆盖：

- 直角坐标系列：bar / pictorialBar / line / scatter / effectScatter /
  candlestick / boxplot / heatmap（grid 与日历两式）/ parallel / themeRiver；
- 层级占比系列：pie / radar / gauge / funnel / sunburst / treemap；
- 关系流向系列：tree / sankey / graph / lines；
- 坐标系与地图：grid 多系列混合 / polar 折线 / singleAxis 散点 /
  calendar 热力 / map（内置示意地图）；
- 组件综合：markPoint + markLine + markArea + visualMap +
  dataZoom（slider + inside）+ brush + toolbox + timeline 三帧切换。

每个系列一张演示卡（``ChartDemoCard``：ChartWidget 最小约 384x264、宽度随
卡片伸缩 + 下方 ``ParamForm`` 精简参数行，每图 2-4 个有意义参数），参数
变化即按新参数 ``set_option`` 重建图表。卡片由 ``ResponsiveCardGrid``
按页面宽度以 1~3 列断点自适应排布（同排等宽、整排撑满），组件综合演示
大图整行撑满。ChartWidget 自身监听 ``theme_changed`` 实时换肤，
亮 / 暗主题切换无需重建页面。示例数据均为语义化数据（月度销量 /
城市天气 / 转化漏斗 / 组织架构等）。
文案经 ``bind_tr`` 按 ``charts`` 分组取词（示例数据键前缀 ``data.``）。
"""

import datetime as _dt
import random
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QSizePolicy,
    QVBoxLayout,
    QLabel,
    QWidget,
)

from InstructionX_UIKit.charts import ChartWidget
from InstructionX_UIKit.theme import T

from core.interfaces import ILocalizationFacade

from .common import Section, bind_tr, hint_label, make_page
from .playground import ParamForm, PlaygroundPanel, add_specs

__all__ = ["create_page", "ChartDemoCard", "ResponsiveCardGrid"]


# ---------------------------------------------------------------------------
# 语义化示例数据（确定性；文本经取词，数据本身不变）
# ---------------------------------------------------------------------------

def _months(tr) -> list:
    """12 个月份标签。"""
    return [tr(f"data.month.{i}") for i in range(1, 13)]


def _cities(tr) -> list:
    """6 个示例城市标签（象形柱图等用）。"""
    keys = ("beijing", "shanghai", "guangzhou", "shenzhen", "hangzhou", "chengdu")
    return [tr(f"data.city.{k}") for k in keys]


def _weekdays(tr) -> list:
    """周一 ~ 周日标签。"""
    return [tr(f"data.weekday.{i}") for i in range(1, 8)]


def _walk(n, seed, lo=2.0, hi=10.0, step=1.6):
    """确定性随机游走序列（n 点，[lo, hi]）。"""
    rnd = random.Random(seed)
    v = rnd.uniform(lo, hi * 0.6)
    out = []
    for _ in range(n):
        v = max(lo, min(hi, v + rnd.uniform(-step, step)))
        out.append(round(v, 1))
    return out


# ---------------------------------------------------------------------------
# 演示卡
# ---------------------------------------------------------------------------

class ChartDemoCard(QFrame):
    """图表演示卡：标题 + ChartWidget + 下方精简参数行。

    参数变化即 ``chart.set_option(build(opts))`` 重建图表；主题切换由
    ChartWidget 自行换肤。``build`` 签名为 ``build(opts: dict) -> dict``
    （返回完整 option）。``specs`` 复用 :func:`add_specs` 规格元组。
    """

    def __init__(self, title, build, specs, hint="", size=(384, 264),
                 auto_apply=True, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)  # 命中 QSS 卡片边框
        self.title_text = str(title)
        self._build = build
        self.opts = {}
        # 卡片水平随网格伸缩（同排等宽、整排撑满）
        self.setSizePolicy(QSizePolicy.Policy.Expanding,
                           QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 10)
        lay.setSpacing(6)

        head = QLabel(self.title_text)
        font = QFont()
        font.setWeight(QFont.Weight(T("font.weight.semibold")))
        head.setFont(font)
        lay.addWidget(head)
        if hint:
            lay.addWidget(hint_label(hint, role="tertiary"))

        self.chart = ChartWidget(self)
        # size 为最小尺寸：宽度随卡片伸缩（resize 自动重排），高度固定
        self.chart.setMinimumWidth(int(size[0]))
        self.chart.setFixedHeight(int(size[1]))
        self.chart.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Fixed)
        lay.addWidget(self.chart)

        self.form = ParamForm(self)
        add_specs(self.form, self.opts, specs)
        lay.addWidget(self.form)
        self.controls = self.form.controls
        lay.addStretch(1)  # 行高不一致时内容顶对齐

        self.form.changed.connect(lambda *_: self.apply())
        if auto_apply:
            self.apply()

    def apply(self):
        """按当前参数重建 option 并 set_option（播放入场动画）。"""
        self.chart.set_option(self._build(dict(self.opts)))

    def finish_animation(self):
        """直接跳到动画末帧（测试 / 截图用）。"""
        self.chart.anim.set_progress(1.0)


class ResponsiveCardGrid(QWidget):
    """演示卡自适应网格：按可用宽度以 1~max_cols 列断点重排。

    卡片水平 Expanding，同排等宽、整排撑满（各列等拉伸，无排内空洞）；
    宽度变化触发 resizeEvent 时仅在实际列数变化时重排，避免布局抖动。
    """

    def __init__(self, cards, min_card_width=420, max_cols=3, spacing=10,
                 parent=None):
        super().__init__(parent)
        self._cards = list(cards)
        self._min_card_width = max(1, int(min_card_width))
        self._max_cols = max(1, int(max_cols))
        self._cols = -1
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(int(spacing))
        self._grid = grid
        self._reflow()

    @property
    def cards(self) -> list:
        """网格内全部演示卡（按加入顺序）。"""
        return list(self._cards)

    @property
    def cols(self) -> int:
        """当前列数（1~max_cols，随宽度断点变化）。"""
        return self._cols

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reflow()

    def _reflow(self) -> None:
        spacing = self._grid.spacing()
        avail = max(1, self.width())
        cols = int((avail + spacing) // (self._min_card_width + spacing))
        cols = max(1, min(self._max_cols, len(self._cards) or 1, cols))
        if cols == self._cols:
            return
        # 清空旧列拉伸（防止残留空列占位）
        for c in range(max(self._grid.columnCount(), self._cols, 0)):
            self._grid.setColumnStretch(c, 0)
        while self._grid.count():
            self._grid.takeAt(0)
        for i, card in enumerate(self._cards):
            self._grid.addWidget(card, i // cols, i % cols)
        for c in range(cols):
            self._grid.setColumnStretch(c, 1)  # 同排等宽、整排撑满
        self._cols = cols


# ---------------------------------------------------------------------------
# 直角坐标系列构建函数
# ---------------------------------------------------------------------------

def _build_bar(o, tr):
    cat = {"type": "category", "data": _months(tr)[:6]}
    val = {"type": "value", "name": tr("data.unit.piece")}
    s1 = {"type": "bar", "name": tr("data.series.offline"),
          "data": [120, 132, 101, 134, 156, 230]}
    s2 = {"type": "bar", "name": tr("data.series.online"),
          "data": [220, 182, 191, 234, 290, 330]}
    for s in (s1, s2):
        s["barWidth"] = o["barWidth"]
        s["barBorderRadius"] = o["radius"]
        if o["stack"]:
            s["stack"] = tr("data.series.total")
    if o["horizontal"]:
        x_axis, y_axis = val, cat
    else:
        x_axis, y_axis = cat, val
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"show": True},
        "grid": {"left": 48, "right": 16, "top": 30, "bottom": 46},
        "xAxis": x_axis, "yAxis": y_axis,
        "series": [s1, s2],
    }


def _build_pictorial(o, tr):
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 16, "top": 30, "bottom": 30},
        "xAxis": {"type": "category", "data": _cities(tr)},
        "yAxis": {"type": "value", "name": "mm"},
        "series": [{
            "type": "pictorialBar", "name": tr("data.series.rainfall"),
            "symbol": o["symbol"], "symbolRepeat": o["repeat"],
            "symbolSize": o["size"],
            "data": [580, 1200, 1800, 1950, 1450, 950],
        }],
    }


def _build_line(o, tr):
    beijing = [2, 5, 11, 19, 25, 29, 31, 30, 26, 19, 10, 4]
    shanghai = [5, 8, 12, 18, 23, 27, 31, 31, 27, 22, 15, 8]
    series = []
    cities = ((tr("data.city.beijing"), beijing),
              (tr("data.city.shanghai"), shanghai))
    for name, data in cities:
        s = {"type": "line", "name": name, "data": data,
             "showSymbol": o["symbol"]}
        if o["step"] != "none":
            s["step"] = o["step"]
        else:
            s["smooth"] = o["smooth"]
        if o["area"]:
            s["areaStyle"] = {"opacity": 0.18}
        series.append(s)
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"show": True},
        "grid": {"left": 44, "right": 16, "top": 30, "bottom": 46},
        "xAxis": {"type": "category", "data": _months(tr)},
        "yAxis": {"type": "value", "name": "℃"},
        "series": series,
    }


def _build_scatter(o, tr):
    rnd = random.Random(20260701)
    data = []
    for _ in range(o["n"]):
        temp = round(rnd.uniform(2, 34), 1)          # 气温
        hum = round(rnd.uniform(25, 95), 1)          # 湿度
        aqi = rnd.randint(20, 180)                   # 第三维：AQI
        data.append([temp, hum, aqi] if o["zmap"] else [temp, hum])
    series = {"type": "scatter", "name": tr("data.series.weather"),
              "data": data}
    if not o["zmap"]:
        series["symbolSize"] = o["size"]
    return {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 44, "right": 16, "top": 30, "bottom": 34},
        "xAxis": {"type": "value", "name": tr("data.axis.temp")},
        "yAxis": {"type": "value", "name": tr("data.axis.humidity")},
        "series": [series],
    }


def _build_effect_scatter(o, tr):
    pts = [[116, 40], [121, 31], [113, 23], [120, 30], [104, 31], [109, 34]]
    return {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 44, "right": 16, "top": 30, "bottom": 34},
        "xAxis": {"type": "value", "name": tr("data.axis.longitude"),
                  "min": 98, "max": 126},
        "yAxis": {"type": "value", "name": tr("data.axis.latitude"),
                  "min": 18, "max": 44},
        "series": [{
            "type": "effectScatter", "name": tr("data.series.checkin"),
            "symbolSize": o["size"],
            "rippleEffect": {"period": o["period"], "scale": o["scale"]},
            "data": pts,
        }],
    }


def _build_candlestick(o, tr):
    rnd = random.Random(955)
    price, data = 12.0, []
    for _ in range(o["n"]):
        open_ = price
        close = max(2.0, open_ + rnd.uniform(-1.6, 1.6))
        high = max(open_, close) + rnd.uniform(0.1, 1.0)
        low = max(0.5, min(open_, close) - rnd.uniform(0.1, 1.0))
        data.append([round(open_, 2), round(close, 2),
                     round(low, 2), round(high, 2)])
        price = close
    series = {"type": "candlestick", "name": tr("data.series.stock"),
              "data": data}
    if o["width"] > 0:
        series["barWidth"] = o["width"]
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 48, "right": 16, "top": 30, "bottom": 30},
        "xAxis": {"type": "category",
                  "data": [tr("data.day", n=i + 1) for i in range(o["n"])]},
        "yAxis": {"type": "value", "name": tr("data.unit.yuan")},
        "series": [series],
    }


def _build_boxplot(o, tr):
    rnd = random.Random(451)
    groups = [tr("data.group", c=c) for c in "ABCDEF"[: o["groups"]]]
    data = []
    for gi in range(o["groups"]):
        vals = sorted(round(rnd.uniform(4, 36), 1) for _ in range(12))
        data.append([vals[0], vals[3], vals[5], vals[8], vals[-1]])
    series = {"type": "boxplot", "name": tr("data.series.overtime"),
              "data": data}
    if o["width"] > 0:
        series["barWidth"] = o["width"]
    return {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 44, "right": 16, "top": 30, "bottom": 30},
        "xAxis": {"type": "category", "data": groups},
        "yAxis": {"type": "value", "name": tr("data.unit.hour")},
        "series": [series],
    }


_HEAT_RAMP = {
    "blue": ["#EBEFF5", "#3F5E8C"],
    "warm": ["#FDF3E3", "#D6473C"],
}


def _build_heatmap_grid(o, tr):
    hours = [tr("data.hour", h=h) for h in range(8, 20, 2)]
    rnd = random.Random(77)
    data = []
    for xi in range(len(hours)):
        for yi in range(len(_weekdays(tr))):
            base = 30 if yi < 5 else 8
            peak = 70 if xi in (2, 3) else 0
            data.append([xi, yi, rnd.randint(0, 20) + base + peak])
    opt = {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 52, "right": 16, "top": 30, "bottom": 30},
        "xAxis": {"type": "category", "data": hours},
        "yAxis": {"type": "category", "data": _weekdays(tr)},
        "series": [{"type": "heatmap", "name": tr("data.series.traffic"),
                    "data": data}],
    }
    if o["visualMap"]:
        opt["visualMap"] = {"min": 0, "max": 120,
                            "inRange": {"colors": _HEAT_RAMP[o["ramp"]]},
                            "orient": "vertical"}
    return opt


def _year_data(year, seed=9):
    """生成某年约 200 天的随机活跃度（日历热力数据）。"""
    rnd = random.Random(seed + year)
    data = []
    day = _dt.date(year, 1, 1)
    while day.year == year:
        if rnd.random() < 0.55:
            data.append([day.isoformat(), rnd.randint(1, 12)])
        day += _dt.timedelta(days=1)
    return data


def _build_heatmap_calendar(o, tr):
    opt = {
        "tooltip": {"trigger": "item"},
        "calendar": {"year": int(o["year"]), "cellSize": o["cell"]},
        "series": [{"type": "heatmap", "name": tr("data.series.commits"),
                    "coordinateSystem": "calendar",
                    "data": _year_data(int(o["year"]))}],
    }
    if o["visualMap"]:
        opt["visualMap"] = {"min": 0, "max": 12, "orient": "vertical"}
    return opt


def _build_parallel(o, tr):
    subjects = [tr(f"data.subject.{i}") for i in range(1, 6)][: o["dims"]]
    rnd = random.Random(33)
    rows = [[rnd.randint(55, 99) for _ in subjects]
            for _ in range(o["n"])]
    return {
        "tooltip": {"trigger": "item"},
        "parallelAxis": [{"name": s, "min": 40, "max": 100}
                         for s in subjects],
        "series": [{"type": "parallel", "name": tr("data.series.scores"),
                    "data": rows}],
    }


def _build_themeriver(o, tr):
    topics = [tr(f"data.topic.{i}") for i in range(1, 6)][: o["series"]]
    rnd = random.Random(2026)
    data = []
    for mi in range(o["months"]):
        for ti, t in enumerate(topics):
            v = 6 + int(10 * (1 + mi % 3) / (ti + 1)) + rnd.randint(0, 8)
            data.append([f"2026-{mi + 1:02d}", v, t])
    return {
        "tooltip": {"trigger": "item"},
        "legend": {"show": True},
        "series": [{"type": "themeRiver", "name": tr("data.series.topic_heat"),
                    "data": data}],
    }


# ---------------------------------------------------------------------------
# 层级占比系列构建函数
# ---------------------------------------------------------------------------

def _pie_data(tr) -> list:
    """饼图示例数据：部门预算。"""
    keys = ("rd", "marketing", "ops", "design", "admin")
    values = (420, 260, 180, 120, 80)
    return [{"name": tr(f"data.dept.{k}"), "value": v}
            for k, v in zip(keys, values)]


def _build_pie(o, tr):
    series = {
        "type": "pie", "name": tr("data.series.budget"),
        "data": _pie_data(tr),
        "label": {"show": True, "position": o["labelPos"]},
    }
    if o["donut"]:
        series["radius"] = ["42%", "72%"]
    else:
        series["radius"] = "72%"
    if o["rose"] != "none":
        series["roseType"] = o["rose"]
    return {
        "tooltip": {"trigger": "item"},
        "legend": {"show": True, "orient": "vertical", "right": 4},
        "series": [series],
    }


def _build_radar(o, tr):
    dims = [(tr(f"data.dim.{i}"), 100) for i in range(1, 7)]
    series = {
        "type": "radar", "name": tr("data.series.eval"),
        "indicator": [{"name": n, "max": m} for n, m in dims],
        "shape": o["shape"],
        "splitNumber": o["split"],
        "data": [
            {"name": tr("data.series.quarter_cur"),
             "value": [82, 90, 70, 88, 60, 76]},
            {"name": tr("data.series.quarter_prev"),
             "value": [70, 78, 66, 80, 55, 70]},
        ],
    }
    if o["area"]:
        series["areaStyle"] = {"opacity": 0.22}
    return {
        "tooltip": {"trigger": "item"},
        "legend": {"show": True},
        "series": [series],
    }


def _build_gauge(o, tr):
    series = {
        "type": "gauge", "name": tr("data.series.goal"),
        "min": 0, "max": 100,
        "data": [{"name": tr("data.series.rate"), "value": o["value"]}],
        "pointer": {"show": True, "length": "62%"},
        "anchor": {"show": True},
        "detail": {"show": True},
        "title": {"show": True},
    }
    if o["progress"]:
        series["progress"] = {"show": True, "width": 10}
    if o["segments"]:
        series["axisLine"] = {"lineStyle": {"width": 10, "color": [
            [0.6, "#3FA46A"], [0.85, "#C78A2B"], [1.0, "#E64545"]]}}
    return {"tooltip": {"show": False}, "series": [series]}


def _build_funnel(o, tr):
    values = (100, 64, 42, 26, 12)
    data = [{"name": tr(f"data.funnel.{i}"), "value": v}
            for i, v in enumerate(values, start=1)]
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "funnel", "name": tr("data.series.conversion"),
            "sort": o["sort"], "gap": o["gap"],
            "label": {"show": True, "position": o["labelPos"]},
            "data": data,
        }],
    }


def _sunburst_data(tr) -> list:
    """旭日图示例数据：营收构成（两级层级）。"""
    g = lambda k: tr(f"data.sun.{k}")  # noqa: E731 简短别名便于排版
    return [
        {"name": g("hardware"), "children": [
            {"name": g("phone"), "value": 46},
            {"name": g("tablet"), "value": 22},
            {"name": g("wearable"), "value": 14}]},
        {"name": g("software"), "children": [
            {"name": g("cloud"), "value": 30},
            {"name": g("appstore"), "value": 18}]},
        {"name": g("content"), "children": [
            {"name": g("video"), "value": 12},
            {"name": g("music"), "value": 8},
            {"name": g("reading"), "value": 5}]},
    ]


def _build_sunburst(o, tr):
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "sunburst", "name": tr("data.series.revenue"),
            "radius": ["18%", "92%"],
            "label": {"show": o["labels"], "minAngle": o["minAngle"]},
            "data": _sunburst_data(tr),
        }],
    }


def _treemap_data(tr) -> list:
    """矩形树图示例数据：存储占用。"""
    g = lambda k: tr(f"data.tm.{k}")  # noqa: E731 简短别名便于排版
    return [
        {"name": g("video"), "children": [
            {"name": g("movie"), "value": 46},
            {"name": g("series"), "value": 30}]},
        {"name": g("photo"), "children": [
            {"name": g("camera"), "value": 28},
            {"name": g("screenshot"), "value": 6}]},
        {"name": g("app"), "value": 24},
        {"name": g("doc"), "value": 10},
        {"name": g("system"), "value": 16},
    ]


def _build_treemap(o, tr):
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "treemap", "name": tr("data.series.storage"),
            "gapWidth": o["gap"], "label": {"show": o["labels"]},
            "breadcrumb": {"show": o["crumb"]},
            "data": _treemap_data(tr),
        }],
    }


# ---------------------------------------------------------------------------
# 关系流向系列构建函数
# ---------------------------------------------------------------------------

def _tree_data(tr) -> list:
    """树图示例数据：组织架构（三级）。"""
    g = lambda k: tr(f"data.org.{k}")  # noqa: E731 简短别名便于排版
    return [{
        "name": g("ceo"), "children": [
            {"name": g("tech"), "children": [
                {"name": g("frontend")}, {"name": g("backend")},
                {"name": g("algorithm")}]},
            {"name": g("product"), "children": [
                {"name": g("product_group")}, {"name": g("design_group")}]},
            {"name": g("operation"), "children": [
                {"name": g("market_group")}, {"name": g("service_group")}]},
        ],
    }]


def _build_tree(o, tr):
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "tree", "name": tr("data.series.org"),
            "orient": o["orient"], "edge": o["edge"],
            "symbolSize": o["size"],
            "label": {"show": True},
            "data": _tree_data(tr),
        }],
    }


def _sankey_data(tr) -> tuple:
    """桑基图示例数据：能源流向（节点名列表 + 边）。"""
    g = lambda k: tr(f"data.energy.{k}")  # noqa: E731 简短别名便于排版
    nodes = [g(k) for k in ("coal", "hydro", "wind", "solar",
                            "industry", "residential", "transport", "loss")]
    edges = [("coal", "industry", 46), ("coal", "residential", 12),
             ("hydro", "industry", 18), ("hydro", "residential", 10),
             ("wind", "transport", 8), ("wind", "residential", 6),
             ("solar", "industry", 9), ("solar", "loss", 3),
             ("coal", "loss", 8)]
    links = [{"source": g(a), "target": g(b), "value": v}
             for a, b, v in edges]
    return nodes, links


def _build_sankey(o, tr):
    nodes, links = _sankey_data(tr)
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "sankey", "name": tr("data.series.energy"),
            "nodeWidth": o["nodeWidth"], "nodeGap": o["nodeGap"],
            "layoutIterations": o["iters"],
            "label": {"show": True},
            "data": [{"name": n} for n in nodes],
            "links": links,
        }],
    }


def _graph_data(tr) -> tuple:
    """关系图示例数据：知识图谱（节点 + 边；芯片节点加大）。"""
    g = lambda k: tr(f"data.graph.{k}")  # noqa: E731 简短别名便于排版
    edges = [("chip", "phone"), ("chip", "car"), ("chip", "appliance"),
             ("os", "phone"), ("os", "ecosystem"), ("ecosystem", "cloud"),
             ("ai", "cloud"), ("ai", "car"), ("ai", "chip")]
    links = [{"source": g(a), "target": g(b)} for a, b in edges]
    return g, links


def _build_graph(o, tr):
    g, links = _graph_data(tr)
    data = [{"name": g("chip"), "symbolSize": o["size"] + 8}]
    data += [{"name": g(k)} for k in
             ("phone", "car", "appliance", "os", "ecosystem", "cloud", "ai")]
    return {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "graph", "name": tr("data.series.kg"),
            "layout": o["layout"],
            "force": {"repulsion": o["repulsion"], "seed": 42},
            "symbolSize": o["size"],
            "label": {"show": True},
            "data": data,
            "links": links,
        }],
    }


def _lines_routes(tr) -> list:
    """线图示例数据：热门航线（城市坐标 + 航线对）。"""
    g = lambda k: tr(f"data.city.{k}")  # noqa: E731 简短别名便于排版
    coords = {"beijing": (116.4, 39.9), "shanghai": (121.5, 31.2),
              "guangzhou": (113.3, 23.1), "shenzhen": (114.1, 22.5),
              "chengdu": (104.1, 30.7), "xian": (108.9, 34.3),
              "wuhan": (114.3, 30.6), "kunming": (102.8, 24.9)}
    city = {g(k): v for k, v in coords.items()}
    pairs = [("beijing", "shanghai"), ("beijing", "guangzhou"),
             ("beijing", "chengdu"), ("shanghai", "shenzhen"),
             ("shanghai", "wuhan"), ("guangzhou", "kunming"),
             ("chengdu", "xian"), ("xian", "beijing"),
             ("wuhan", "shenzhen")]
    return [{"coords": [list(city[g(a)]), list(city[g(b)])]}
            for a, b in pairs]


def _build_lines(o, tr):
    return {
        "tooltip": {"trigger": "item"},
        "grid": {"left": 44, "right": 16, "top": 30, "bottom": 34},
        "xAxis": {"type": "value", "name": tr("data.axis.longitude"),
                  "min": 98, "max": 126},
        "yAxis": {"type": "value", "name": tr("data.axis.latitude"),
                  "min": 18, "max": 44},
        "series": [{
            "type": "lines", "name": tr("data.series.routes"),
            "lineStyle": {"width": o["width"], "curveness": o["curveness"]},
            "trailEffect": {"show": o["trail"], "period": 4,
                            "symbolSize": 5},
            "data": _lines_routes(tr),
        }],
    }


# ---------------------------------------------------------------------------
# 坐标系与地图构建函数
# ---------------------------------------------------------------------------

def _build_grid_mix(o, tr):
    months = _months(tr)[:8]
    series = [
        {"type": "bar", "name": tr("data.series.sales"),
         "data": [120, 200, 150, 260, 220, 300, 280, 340],
         "barWidth": 0.5, "barBorderRadius": 3},
        {"type": "line", "name": tr("data.series.price"),
         "data": [86, 92, 78, 105, 98, 120, 112, 128],
         "smooth": o["smooth"], "yAxisIndex": 0},
    ]
    if o["area"]:
        series[1]["areaStyle"] = {"opacity": 0.15}
    if o["scatter"]:
        series.append({"type": "scatter", "name": tr("data.series.promo"),
                       "symbolSize": 14,
                       "data": [[1, 200], [3, 260], [5, 300], [7, 340]]})
    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"show": True},
        "grid": {"left": 48, "right": 16, "top": 30, "bottom": 46},
        "xAxis": {"type": "category", "data": months},
        "yAxis": {"type": "value", "name": tr("data.unit.amount")},
        "series": series,
    }


def _build_polar(o, tr):
    directions = [tr(f"data.dir.{i}") for i in range(1, 9)]
    freq = [12, 8, 15, 22, 18, 9, 6, 10]
    series = {
        "type": "line", "name": tr("data.series.wind"),
        "coordinateSystem": "polar",
        "smooth": o["smooth"],
        "data": [[d, v] for d, v in zip(directions, freq)],
    }
    if o["area"]:
        series["areaStyle"] = {"opacity": 0.2}
    return {
        "tooltip": {"trigger": "item"},
        "polar": {"shape": o["shape"]},
        "angleAxis": {"type": "category", "data": directions},
        "radiusAxis": {"type": "value"},
        "series": [series],
    }


def _build_single_axis(o, tr):
    rnd = random.Random(601)
    data = [round(rnd.gauss(75, 12), 1) for _ in range(o["n"])]
    return {
        "tooltip": {"trigger": "item"},
        "singleAxis": {"left": 40, "right": 40, "name": tr("data.axis.score")},
        "series": [{
            "type": "scatter", "name": tr("data.series.scores_dist"),
            "coordinateSystem": "singleAxis",
            "symbolSize": o["size"],
            "data": data,
        }],
    }


def _build_calendar_coord(o, tr):
    return {
        "tooltip": {"trigger": "item"},
        "calendar": {"year": int(o["year"]), "cellSize": o["cell"]},
        "visualMap": {"min": 0, "max": 12,
                      "inRange": {"colors": _HEAT_RAMP["warm"]},
                      "orient": "vertical"},
        "series": [{"type": "heatmap", "name": tr("data.series.steps"),
                    "coordinateSystem": "calendar",
                    "data": _year_data(int(o["year"]), seed=41)}],
    }


def _build_map(o, tr):
    values = (82, 36, 95, 71, 58, 44, 27)
    data = [{"name": tr(f"data.region.{i}"), "value": v}
            for i, v in enumerate(values, start=1)]
    opt = {
        "tooltip": {"trigger": "item"},
        "series": [{
            "type": "map", "name": tr("data.series.region_sales"),
            "map": "demo",
            "data": data,
        }],
    }
    if o["visualMap"]:
        opt["visualMap"] = {"min": 0, "max": 100,
                            "inRange": {"colors": _HEAT_RAMP[o["ramp"]]},
                            "orient": o["orient"]}
    return opt


# ---------------------------------------------------------------------------
# 组件综合演示
# ---------------------------------------------------------------------------

_COMP_YEARS = {
    "2024": {"bar": [150, 180, 132, 210, 190, 260, 240, 300, 280, 330, 310, 380],
             "line": [96, 102, 88, 115, 108, 130, 122, 138, 131, 145, 140, 158]},
    "2025": {"bar": [180, 210, 168, 240, 220, 290, 270, 330, 310, 360, 345, 420],
             "line": [104, 112, 98, 126, 118, 142, 133, 150, 142, 156, 150, 172]},
    "2026": {"bar": [210, 250, 200, 280, 260, 330, 310, 370, 350, 400, 390, 460],
             "line": [112, 124, 108, 138, 129, 154, 145, 163, 154, 170, 163, 186]},
}


def _comp_markline(kind, tr):
    """标线定义：average / max / threshold 三种。"""
    if kind == "average":
        return [{"type": "average", "name": tr("data.mark.average")}]
    if kind == "max":
        return [{"type": "max", "name": tr("data.mark.max")}]
    return [{"yAxis": 300, "name": tr("data.mark.threshold")}]


def _comp_series(o, year, tr):
    """综合演示某年度的完整系列定义（timeline 帧为 list 替换语义，
    帧内必须携带 type/name/标注，不能只给 data）。"""
    y = _COMP_YEARS[year]
    bar = {"type": "bar", "name": tr("data.series.month_sales"),
           "data": y["bar"], "barWidth": 0.55, "barBorderRadius": 3}
    line = {"type": "line", "name": tr("data.series.month_price"),
            "data": y["line"], "smooth": True,
            "markPoint": {"data": [{"type": "max"}, {"type": "min"}]},
            "markLine": {"data": _comp_markline(o["markLine"], tr)}}
    if o["markArea"]:
        months = _months(tr)
        line["markArea"] = {"data": [[{"xAxis": months[2]},
                                      {"xAxis": months[4]}]]}
    return [bar, line]


def _build_comprehensive(o, tr):
    """组件综合：bar+line + mark* + visualMap + dataZoom + brush + toolbox + timeline。"""
    opt = {
        "title": {"text": tr("comp.chart_title"),
                  "subtext": tr("comp.chart_sub")},
        "tooltip": {"trigger": "axis"},
        "legend": {"show": True},
        "grid": {"left": 52, "right": 56, "top": 56, "bottom": 108},
        "xAxis": {"type": "category", "data": _months(tr)},
        "yAxis": {"type": "value", "name": tr("data.unit.amount")},
        "series": _comp_series(o, "2024", tr),
        "dataZoom": [{"type": "slider", "start": 0, "end": o["zoomEnd"]},
                     {"type": "inside"}],
        "brush": {"toolbox": ["rect", "clear"],
                  "outOfBrush": {"opacity": 0.35}},
        "toolbox": {"feature": ["saveAsImage", "dataZoom", "restore"]},
        "timeline": {"data": list(_COMP_YEARS), "autoPlay": False},
        "options": [{"series": _comp_series(o, year, tr)}
                    for year in _COMP_YEARS],
    }
    if o["visualMap"]:
        opt["visualMap"] = {"min": 60, "max": 460,
                            "inRange": {"colors": _HEAT_RAMP["warm"]},
                            "orient": "vertical"}
    return opt


# ---------------------------------------------------------------------------
# 卡片规格表：(卡片键, 构建函数, 参数规格, 提示键)
# 参数规格第 3 元素与选项对第 1 元素均为取词键，构建时经 _translate_specs 翻译。
# ---------------------------------------------------------------------------

_SYMBOL_OPTS = [("opt.symbol.rect", "rect"), ("opt.symbol.circle", "circle"),
                ("opt.symbol.pin", "pin")]
_STEP_OPTS = [("opt.step.none", "none"), ("opt.step.start", "start"),
              ("opt.step.middle", "middle"), ("opt.step.end", "end")]
_RAMP_OPTS = [("opt.ramp.blue", "blue"), ("opt.ramp.warm", "warm")]
_CELL_OPTS = [("opt.cell.auto", "auto"), ("opt.cell.s", 10),
              ("opt.cell.m", 14), ("opt.cell.l", 18)]
_YEAR_OPTS = [("opt.year.2024", 2024), ("opt.year.2025", 2025),
              ("opt.year.2026", 2026)]

_CARTESIAN_CARDS = [
    ("bar", _build_bar,
     [("bool", "stack", "bar.p.stack", False),
      ("float", "barWidth", "bar.p.bar_width", 0.6, 0.2, 0.9, {"step": 0.1}),
      ("int", "radius", "bar.p.radius", 3, 0, 10),
      ("bool", "horizontal", "bar.p.horizontal", False)],
     "bar.hint"),
    ("pictorial", _build_pictorial,
     [("choice", "symbol", "pictorial.p.symbol", "circle", list(_SYMBOL_OPTS)),
      ("bool", "repeat", "pictorial.p.repeat", True),
      ("int", "size", "pictorial.p.size", 12, 6, 24)],
     "pictorial.hint"),
    ("line", _build_line,
     [("bool", "smooth", "line.p.smooth", True),
      ("bool", "area", "line.p.area", False),
      ("choice", "step", "line.p.step", "none", list(_STEP_OPTS)),
      ("bool", "symbol", "line.p.symbol", True)],
     "line.hint"),
    ("scatter", _build_scatter,
     [("int", "n", "scatter.p.n", 40, 8, 120),
      ("bool", "zmap", "scatter.p.zmap", True),
      ("int", "size", "scatter.p.size", 12, 4, 24)],
     "scatter.hint"),
    ("effect_scatter", _build_effect_scatter,
     [("float", "period", "effect_scatter.p.period", 3.0, 1.0, 6.0,
       {"step": 0.5}),
      ("float", "scale", "effect_scatter.p.scale", 2.6, 1.5, 4.0,
       {"step": 0.1}),
      ("int", "size", "effect_scatter.p.size", 12, 6, 20)],
     "effect_scatter.hint"),
    ("candlestick", _build_candlestick,
     [("int", "n", "candlestick.p.n", 30, 10, 60),
      ("int", "width", "candlestick.p.width", 0, 0, 24)],
     "candlestick.hint"),
    ("boxplot", _build_boxplot,
     [("int", "groups", "boxplot.p.groups", 4, 2, 6),
      ("int", "width", "boxplot.p.width", 0, 0, 28)],
     "boxplot.hint"),
    ("heatmap_grid", _build_heatmap_grid,
     [("bool", "visualMap", "heatmap_grid.p.visual_map", True),
      ("choice", "ramp", "heatmap_grid.p.ramp", "blue", list(_RAMP_OPTS))],
     "heatmap_grid.hint"),
    ("heatmap_calendar", _build_heatmap_calendar,
     [("choice", "year", "heatmap_calendar.p.year", 2026, list(_YEAR_OPTS)),
      ("choice", "cell", "heatmap_calendar.p.cell", "auto", list(_CELL_OPTS)),
      ("bool", "visualMap", "heatmap_calendar.p.visual_map", False)],
     "heatmap_calendar.hint"),
    ("parallel", _build_parallel,
     [("int", "dims", "parallel.p.dims", 5, 3, 5),
      ("int", "n", "parallel.p.n", 6, 3, 12)],
     "parallel.hint"),
    ("themeriver", _build_themeriver,
     [("int", "series", "themeriver.p.series", 4, 2, 5),
      ("int", "months", "themeriver.p.months", 8, 4, 12)],
     "themeriver.hint"),
]

_HIERARCHY_CARDS = [
    ("pie", _build_pie,
     [("bool", "donut", "pie.p.donut", True),
      ("choice", "rose", "pie.p.rose", "none",
       [("opt.rose.none", "none"), ("opt.rose.radius", "radius"),
        ("opt.rose.area", "area")]),
      ("choice", "labelPos", "pie.p.label_pos", "outside",
       [("opt.label_pos.outside", "outside"), ("opt.label_pos.inside", "inside"),
        ("opt.label_pos.center", "center")])],
     "pie.hint"),
    ("radar", _build_radar,
     [("choice", "shape", "radar.p.shape", "polygon",
       [("opt.shape.polygon", "polygon"), ("opt.shape.circle", "circle")]),
      ("bool", "area", "radar.p.area", True),
      ("int", "split", "radar.p.split", 5, 3, 6)],
     "radar.hint"),
    ("gauge", _build_gauge,
     [("int", "value", "gauge.p.value", 72, 0, 100),
      ("bool", "progress", "gauge.p.progress", True),
      ("bool", "segments", "gauge.p.segments", True)],
     "gauge.hint"),
    ("funnel", _build_funnel,
     [("choice", "sort", "funnel.p.sort", "descending",
       [("opt.sort.descending", "descending"),
        ("opt.sort.ascending", "ascending"),
        ("opt.sort.none", "none")]),
      ("int", "gap", "funnel.p.gap", 2, 0, 8),
      ("choice", "labelPos", "funnel.p.label_pos", "outer",
       [("opt.funnel_label.outer", "outer"),
        ("opt.funnel_label.inside", "inside")])],
     "funnel.hint"),
    ("sunburst", _build_sunburst,
     [("bool", "labels", "sunburst.p.labels", True),
      ("int", "minAngle", "sunburst.p.min_angle", 8, 0, 20)],
     "sunburst.hint"),
    ("treemap", _build_treemap,
     [("bool", "crumb", "treemap.p.crumb", True),
      ("int", "gap", "treemap.p.gap", 1, 0, 4),
      ("bool", "labels", "treemap.p.labels", True)],
     "treemap.hint"),
]

_RELATION_CARDS = [
    ("tree", _build_tree,
     [("choice", "orient", "tree.p.orient", "LR",
       [("opt.orient.lr", "LR"), ("opt.orient.tb", "TB")]),
      ("choice", "edge", "tree.p.edge", "polyline",
       [("opt.edge.polyline", "polyline"), ("opt.edge.curve", "curve")]),
      ("int", "size", "tree.p.size", 8, 4, 14)],
     "tree.hint"),
    ("sankey", _build_sankey,
     [("int", "nodeWidth", "sankey.p.node_width", 14, 6, 24),
      ("int", "nodeGap", "sankey.p.node_gap", 10, 4, 20),
      ("int", "iters", "sankey.p.iters", 6, 0, 12)],
     "sankey.hint"),
    ("graph", _build_graph,
     [("choice", "layout", "graph.p.layout", "force",
       [("opt.layout.force", "force"), ("opt.layout.circular", "circular")]),
      ("float", "repulsion", "graph.p.repulsion", 1.0, 0.2, 3.0,
       {"step": 0.2}),
      ("int", "size", "graph.p.size", 14, 8, 24)],
     "graph.hint"),
    ("lines", _build_lines,
     [("float", "curveness", "lines.p.curveness", 0.2, 0.0, 0.5,
       {"step": 0.05}),
      ("bool", "trail", "lines.p.trail", True),
      ("int", "width", "lines.p.width", 2, 1, 4)],
     "lines.hint"),
]

_COORD_CARDS = [
    ("grid_mix", _build_grid_mix,
     [("bool", "smooth", "grid_mix.p.smooth", True),
      ("bool", "area", "grid_mix.p.area", False),
      ("bool", "scatter", "grid_mix.p.scatter", True)],
     "grid_mix.hint"),
    ("polar", _build_polar,
     [("choice", "shape", "polar.p.shape", "polygon",
       [("opt.shape.polygon", "polygon"), ("opt.shape.circle", "circle")]),
      ("bool", "area", "polar.p.area", True),
      ("bool", "smooth", "polar.p.smooth", False)],
     "polar.hint"),
    ("single_axis", _build_single_axis,
     [("int", "n", "single_axis.p.n", 40, 10, 100),
      ("int", "size", "single_axis.p.size", 10, 4, 20)],
     "single_axis.hint"),
    ("calendar_coord", _build_calendar_coord,
     [("choice", "year", "calendar_coord.p.year", 2026, list(_YEAR_OPTS)),
      ("choice", "cell", "calendar_coord.p.cell", "auto", list(_CELL_OPTS))],
     "calendar_coord.hint"),
    ("map", _build_map,
     [("bool", "visualMap", "map.p.visual_map", True),
      ("choice", "ramp", "map.p.ramp", "blue", list(_RAMP_OPTS)),
      ("choice", "orient", "map.p.orient", "vertical",
       [("opt.map_orient.vertical", "vertical"),
        ("opt.map_orient.horizontal", "horizontal")])],
     "map.hint"),
]

_COMP_SPECS = [
    ("choice", "markLine", "comp.p.mark_line", "average",
     [("opt.mark_line.average", "average"), ("opt.mark_line.max", "max"),
      ("opt.mark_line.threshold", "threshold")]),
    ("bool", "markArea", "comp.p.mark_area", True),
    ("bool", "visualMap", "comp.p.visual_map", False),
    ("int", "zoomEnd", "comp.p.zoom_end", 100, 20, 100),
]


# ---------------------------------------------------------------------------
# 页面组装
# ---------------------------------------------------------------------------

def _translate_options(item, tr):
    """choice 规格的选项对（取词键, 值）翻译为（显示文案, 值）。"""
    if isinstance(item, list) and item and isinstance(item[0], tuple):
        return [(tr(k), v) for k, v in item]
    return item


def _translate_specs(rows, tr) -> list:
    """把规格行的标签键与 choice 选项键译为当前语言。"""
    return [(kind, name, tr(label_key),
             *[_translate_options(item, tr) for item in rest])
            for kind, name, label_key, *rest in rows]


def _make_cards(specs, tr) -> list:
    """按卡片规格表构建演示卡（标题 / 提示 / 参数标签均取词）。"""
    return [ChartDemoCard(tr(f"{key}.title"),
                          lambda o, b=build: b(o, tr),
                          _translate_specs(spec, tr), hint=tr(hint_key))
            for key, build, spec, hint_key in specs]


def _comprehensive_section(i18n) -> Section:
    """组件综合演示：大图 + 右侧参数面板 + option 键说明。"""
    tr = bind_tr(i18n, "charts")
    box = Section(tr("comp.sec"))
    host = QWidget()
    lay = QGridLayout(host)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(10)

    card = ChartDemoCard(tr("comp.card_title"),
                         lambda o: _build_comprehensive(o, tr),
                         [], hint="", size=(560, 420), auto_apply=False)
    lay.addWidget(card, 0, 0)

    panel = PlaygroundPanel(tr("comp.panel_title"), width=252, i18n=i18n)
    opts = card.opts
    add_specs(panel.form, opts, _translate_specs(_COMP_SPECS, tr))
    panel.form.changed.connect(lambda *_: card.apply())
    card.apply()
    card.panel = panel  # 便于测试访问

    side = QWidget()
    side_lay = QVBoxLayout(side)
    side_lay.setContentsMargins(0, 0, 0, 0)
    side_lay.setSpacing(8)
    side_lay.addWidget(panel)
    side_lay.addWidget(hint_label(tr("comp.keys_note"), role="tertiary"))
    side_lay.addStretch(1)
    lay.addWidget(side, 0, 1)
    lay.setColumnStretch(0, 1)

    box.layout().addWidget(host)
    box.card = card  # 便于测试访问
    return box


def create_page(i18n: Optional[ILocalizationFacade] = None) -> QWidget:
    """图表演示页（InstructionX_UIKit.charts 原生引擎全系列）。"""
    tr = bind_tr(i18n, "charts")
    sec_cart = Section(tr("sec.cartesian"))
    sec_cart.layout().addWidget(
        ResponsiveCardGrid(_make_cards(_CARTESIAN_CARDS, tr)))

    sec_hier = Section(tr("sec.hierarchy"))
    sec_hier.layout().addWidget(
        ResponsiveCardGrid(_make_cards(_HIERARCHY_CARDS, tr)))

    sec_rel = Section(tr("sec.relation"))
    sec_rel.layout().addWidget(
        ResponsiveCardGrid(_make_cards(_RELATION_CARDS, tr)))

    sec_coord = Section(tr("sec.coord"))
    sec_coord.layout().addWidget(
        ResponsiveCardGrid(_make_cards(_COORD_CARDS, tr)))

    return make_page(tr("title"), tr("desc"),
                     [sec_cart, sec_hier, sec_rel, sec_coord,
                      _comprehensive_section(i18n)])
