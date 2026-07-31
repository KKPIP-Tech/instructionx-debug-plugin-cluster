# -*- coding: utf-8 -*-
"""blueprint_opencv function 层命名常量与共享异常。

本模块集中定义：引脚 id / 引脚数据类型、节点分类与 accent 配色、
节点级 / 运行级状态枚举值、内置 start 节点约定，以及全 function 层
共用的 ``NodeExecutionError`` 异常类型。

所有取值与 ``docs/req/2026-07-30/SPEC-blueprint-opencv-20260730.md``
§3.0 / §4.3 / §6 的契约保持一致，修改时需同步更新 SPEC。
"""

from typing import Dict


class NodeExecutionError(Exception):
    """节点执行/校验失败异常（function 层统一错误类型）。

    message 必须使用中文、面向用户可读；执行引擎捕获后将其标记为
    节点 error 状态并中断当前 exec 分支，不向上抛出导致程序崩溃。
    """


# ---------------------------------------------------------------------------
# 引脚约定（SPEC §3.0）
# ---------------------------------------------------------------------------

#: exec 输入引脚 id
PIN_EXEC_IN = "exec_in"
#: exec 输出引脚 id
PIN_EXEC_OUT = "exec_out"
#: 图像输入引脚 id
PIN_IMAGE_IN = "image_in"
#: 图像输出引脚 id
PIN_IMAGE_OUT = "image_out"

#: exec 引脚数据类型（Blueprint 内置）
PIN_DATA_TYPE_EXEC = "exec"
#: 图像引脚数据类型（Blueprint 内置）
PIN_DATA_TYPE_IMAGE = "image"

#: 内置起始节点类型名（Blueprint 自带，exec 链唯一起点）
START_TYPE_NAME = "start"
#: 内置 start 节点的 exec 输出引脚 id（由 UIKit Blueprint 内置定义）
START_EXEC_OUT_PIN = "out"

#: preview 节点类型名（引擎据此触发 on_preview 回调）
PREVIEW_TYPE_NAME = "preview"

# ---------------------------------------------------------------------------
# 节点分类与 accent 配色（SPEC §3.0）
# ---------------------------------------------------------------------------

CATEGORY_INPUT = "输入"
CATEGORY_BASIC = "基础"
CATEGORY_FILTER = "滤波"
CATEGORY_THRESHOLD = "阈值与边缘"
CATEGORY_MORPHOLOGY = "形态学"
CATEGORY_ADJUST = "调整"
CATEGORY_OUTPUT = "输出"

#: 分类 → accent 强调色（hex，SPEC §3.0 约定值）
CATEGORY_ACCENTS: Dict[str, str] = {
    CATEGORY_INPUT: "#4CAF50",
    CATEGORY_BASIC: "#2196F3",
    CATEGORY_FILTER: "#9C27B0",
    CATEGORY_THRESHOLD: "#FF9800",
    CATEGORY_MORPHOLOGY: "#795548",
    CATEGORY_ADJUST: "#00BCD4",
    CATEGORY_OUTPUT: "#F44336",
}

# ---------------------------------------------------------------------------
# 状态枚举值（SPEC §4.3 / §6）
# ---------------------------------------------------------------------------

#: 节点级状态（BlueprintNode.status 同款取值）
NODE_STATUS_IDLE = "idle"
NODE_STATUS_RUNNING = "running"
NODE_STATUS_DONE = "done"
NODE_STATUS_ERROR = "error"

#: 运行级状态（PipelineController 状态机，SPEC §6.1）
RUN_STATUS_IDLE = "idle"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_STOPPING = "stopping"
RUN_STATUS_DONE = "done"
RUN_STATUS_ERROR = "error"

# ---------------------------------------------------------------------------
# 防御性上限与默认值
# ---------------------------------------------------------------------------

#: 单次运行允许的最大节点数（与 config/default.json graph.max_nodes 一致）
DEFAULT_MAX_NODES = 256

#: preview 信息 dict 的键名（SPEC §4.2.4 契约）
INFO_WIDTH = "width"
INFO_HEIGHT = "height"
INFO_CHANNELS = "channels"
INFO_ELAPSED_MS = "elapsed_ms"
