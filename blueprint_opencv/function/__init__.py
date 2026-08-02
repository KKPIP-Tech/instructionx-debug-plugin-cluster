# -*- coding: utf-8 -*-
"""function 目录 - 业务功能层（纯 Python + numpy + cv2，禁止 import PySide6 / QWidget）

模块划分（SPEC §2）：

- ``constants``：引脚 id、分类 accent、状态枚举值等命名常量与 NodeExecutionError；
- ``param_schema``：参数 schema 类型定义与校验（属性面板 / 引擎共用）；
- ``node_catalog``：NODE_DEFINITIONS 注册表与注册载荷（纯 dict，不含 Qt）；
- ``image_codec``：numpy ↔ PNG 字节编解码、尺寸归一；
- ``executor``：PipelineExecutor（exec 拓扑排序 + 数据流求值 + 状态回调）；
- ``graph_migration``：存档图引脚自动迁移（污染期旧存档 in/out/img 引脚
  按同方向索引映射纠正为目录标准定义，幂等）；
- ``pipeline_controller``：PipelineController（运行会话状态、停止标志、最近结果）；
- ``ops/``：20 个节点 op 实现（op(inputs, props) -> outputs）。
"""
