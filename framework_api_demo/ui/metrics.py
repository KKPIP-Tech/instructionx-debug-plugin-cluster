# -*- coding: utf-8 -*-
"""演示插件 UI 布局度量常量。

集中管理主控件与各 Tab 的间距/边距/限高（单位均为像素），
避免魔法数散落在各布局构建代码中。0（无边距/无间距）属无语义
字面量，不入本表。
"""

# ---- 滚动 Tab 内容容器 ----
TAB_CONTENT_SPACING = 10
TAB_CONTENT_MARGIN = 4

# ---- 分组 / 表单 / 按钮行间距 ----
GROUP_SPACING = 8
FORM_SPACING = 6
ROW_SPACING = 8

# ---- 列表与文本区限高 ----
LIST_BOX_MAX_HEIGHT = 80        # Provider/模型/插件/API/Function Tools 等列表
CONV_LIST_MAX_HEIGHT = 100      # 会话列表
CHAT_RESULT_MAX_HEIGHT = 80     # 聊天结果区 / 工具流式结果区
CONV_RESULT_MAX_HEIGHT = 100    # 会话回复区
TASK_LIST_MAX_HEIGHT = 100      # 任务列表
CALL_RESULT_MAX_HEIGHT = 60     # 跨插件调用结果区
SERVER_STATUS_MAX_HEIGHT = 90   # MCP Server 状态区
BRIDGE_NOTE_MAX_HEIGHT = 70     # 桥接说明文本
REMOTE_CONFIG_MAX_HEIGHT = 130  # 远程 MCP 配置编辑区
MCP_LIST_MAX_HEIGHT = 90        # 桥接工具 / 远程 Server 列表
LOG_PANEL_MAX_HEIGHT = 160      # 主控件执行日志面板

# ---- 主控件布局 ----
MAIN_MARGIN = 12
MAIN_SPACING = 12
LEFT_PANEL_SPACING = 8
PANEL_INNER_SPACING = 4
# 标签头水平内边距：实例级收窄（UIKit 默认 16px），使 6 个标签在固定宽度内完整显示
TAB_BAR_H_PADDING = 6
