# -*- coding: utf-8 -*-
"""blueprint_opencv UI 层冒烟测试（offscreen，qapp/qtbot fixture）。

覆盖范围：

- MainWidget 创建：无 default 存档时回退构建预置示例图
  （start→load_image→gaussian_blur→canny→preview，5 节点 7 边）；
- 预置图内容：节点类型序列、exec 边 4 条 + image 边 3 条、
  load_image 节点默认 file_path 指向插件 assets/sample.png；
- 面板存在性：GraphListPanel / NodeListPanel 已组装，节点列表行数
  与画布节点同步（5 行），空存档时蓝图列表 0 行；
- 快照 / 恢复：graph_snapshot → restore_graph 往返后节点数不变。

均以隔离 plugin_id + tmp_path DataProvider 运行，不污染真实数据目录。
"""

from plugin.blueprint_opencv.service import BlueprintOpenCVService
from plugin.blueprint_opencv.ui.graph_list_panel import GraphListPanel
from plugin.blueprint_opencv.ui.main_widget import MainWidget
from plugin.blueprint_opencv.ui.node_bootstrap import ensure_node_types_registered
from plugin.blueprint_opencv.ui.node_list_panel import NodeListPanel

import pytest


@pytest.fixture(autouse=True)
def _assert_node_specs():
    """每个用例前重新断言节点注册（含同名冲突纠正）。

    全量运行时 ui_demo 套件会把同名类型（load_image 等）覆盖注册为
    外来引脚定义；本插件的纠正逻辑入口在模块 import 与 showEvent，
    offscreen 测试两条路径都不触发，需在 fixture 中显式断言。
    """
    ensure_node_types_registered()

#: 预置示例图节点类型序列（SPEC-graph-list §1.5）
_PRESET_TYPE_SEQUENCE = ["start", "load_image", "gaussian_blur", "canny",
                         "preview"]
#: 预置图节点数 / 边数（exec 4 条 + image 3 条）
_PRESET_NODE_COUNT = 5
_PRESET_EDGE_COUNT = 7


def _make_widget(qtbot, plugin_id: str, provider) -> MainWidget:
    """构建隔离的 MainWidget 并注册到 qtbot 生命周期管理。"""
    service = BlueprintOpenCVService(plugin_id=plugin_id,
                                     data_provider=provider)
    widget = MainWidget(service)
    qtbot.addWidget(widget)
    return widget


class TestMainWidgetCreation:
    """MainWidget 创建与预置示例图。"""

    def test_preset_graph_structure(self, qtbot, plugin_id, provider):
        """无存档启动：画布构建预置示例图（5 节点 7 边）。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        assert len(widget.graph.nodes()) == _PRESET_NODE_COUNT
        assert len(widget.graph.edges()) == _PRESET_EDGE_COUNT

    def test_preset_node_types(self, qtbot, plugin_id, provider):
        """预置图节点类型序列为 start→加载→高斯→Canny→预览。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        type_names = [node.type_name for node in widget.graph.nodes()]
        assert type_names == _PRESET_TYPE_SEQUENCE

    def test_preset_edges_split(self, qtbot, plugin_id, provider):
        """预置图边构成：4 条 exec 边 + 3 条 image 边。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        pins = [(edge.from_pin, edge.to_pin) for edge in widget.graph.edges()]
        exec_edges = [p for p in pins if p[1] == "exec_in"]
        image_edges = [p for p in pins if p == ("image_out", "image_in")]
        assert len(exec_edges) == 4
        assert len(image_edges) == 3

    def test_preset_load_image_path(self, qtbot, plugin_id, provider):
        """预置图 load_image 节点默认 file_path 指向存在的 sample.png。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        load_node = next(n for n in widget.graph.nodes()
                         if n.type_name == "load_image")
        file_path = str(load_node.properties.get("file_path", ""))
        assert file_path.endswith("sample.png")


class TestPanels:
    """左右侧面板组装与数据同步。"""

    def test_panels_exist(self, qtbot, plugin_id, provider):
        """GraphListPanel / NodeListPanel 作为公开属性存在且类型正确。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        assert isinstance(widget.graph_list_panel, GraphListPanel)
        assert isinstance(widget.node_list_panel, NodeListPanel)

    def test_node_list_rows_synced(self, qtbot, plugin_id, provider):
        """节点列表行数与画布节点数同步（5 行）。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        assert widget.node_list_panel.row_count() == _PRESET_NODE_COUNT

    def test_graph_list_empty_initially(self, qtbot, plugin_id, provider):
        """无存档时蓝图列表为空（0 行，空态显示）。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        assert widget.graph_list_panel.row_count() == 0


class TestSnapshotRoundTrip:
    """图快照与恢复。"""

    def test_snapshot_and_restore(self, qtbot, plugin_id, provider):
        """graph_snapshot → restore_graph 往返：节点数 / 边数保持不变。"""
        widget = _make_widget(qtbot, plugin_id, provider)
        snapshot = widget.graph_snapshot()
        assert "graph" in snapshot
        widget.restore_graph(snapshot)
        assert len(widget.graph.nodes()) == _PRESET_NODE_COUNT
        assert len(widget.graph.edges()) == _PRESET_EDGE_COUNT
