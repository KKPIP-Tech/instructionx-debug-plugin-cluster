# Blueprint OpenCV

基于 **InstructionX_UIKit Blueprint** 组件的 **OpenCV 节点化图像处理蓝图编辑器**，同时是 Blueprint 用法的官方样板插件：展示节点类型注册、exec/data 双链执行、外部属性面板参数编辑、工作线程处理与跨线程结果封送、图序列化持久化的完整范式。

## 功能特性

- **节点化编辑**：在蓝图画布上右键创建节点、拖拽连线，所见即所得地搭建 OpenCV 图像处理管线
- **exec/data 双链语义**：白色 `exec` 引脚决定执行顺序（从内置 `start` 节点出发拓扑排序），`image` 引脚决定数据流向（上游未求值时按需递归求值，一轮运行内按节点缓存）
- **外部属性面板**：选中节点后按参数 schema 动态重建表单，修改即时写回节点属性（Blueprint 官方推荐的参数编辑范式）
- **工作线程执行**：cv2 处理经框架后台任务线程池执行，不阻塞 UI；结果经 Qt 信号跨线程排队封送，预览图与节点状态实时刷新
- **图持久化**：画布序列化后经 DataProvider 保存/恢复，损坏存档自动回退预置示例图
- **跨插件 / MCP API**：六个 service_api 方法供其他插件或 MCP 客户端远程驱动管线

## 节点清单（20 个）

| 分类 | 节点 |
|------|------|
| 输入 | 加载图片 `load_image`、生成噪声 `generate_noise`、纯色图像 `solid_color` |
| 基础 | 灰度化 `grayscale`、反色 `invert`、缩放 `resize`、翻转 `flip`、旋转 `rotate` |
| 滤波 | 高斯模糊 `gaussian_blur`、中值模糊 `median_blur`、双边滤波 `bilateral` |
| 阈值与边缘 | 固定阈值 `threshold`、自适应阈值 `adaptive_threshold`、Canny 边缘 `canny` |
| 形态学 | 形态学操作 `morphology`（腐蚀/膨胀/开/闭/梯度/顶帽/黑帽） |
| 调整 | 亮度对比度 `brightness_contrast`、锐化 `sharpen`、HSV 转换 `hsv_convert` |
| 输出 | 预览 `preview`、保存图片 `save_image` |

除输入类节点只有图像输出、`save_image` 只有图像输入外，所有节点均有 `exec_in`/`exec_out` 与 `image_in`/`image_out` 引脚。

## 使用说明

1. 在技能面板点击 **Blueprint OpenCV** 打开插件界面；
2. 画布右键创建节点：先放置内置 `start` 节点作为执行起点，再按需添加处理节点；
3. 连线：从 `start` 的 exec 输出沿处理节点串起执行链，用 `image` 引脚连接数据流；
4. 选中节点，在右侧属性面板编辑参数（如高斯核大小、阈值等）；
5. 点击工具条 **运行**，节点状态与耗时实时高亮，`preview` 节点结果显示在预览区；
6. **保存/加载** 可将当前图持久化；插件启动时自动恢复上次存档，无存档则加载预置示例图。

依赖：`opencv-python >= 4.8.0`、`numpy >= 1.24.0`（安装插件时由框架自动检查安装）。

## service_api（跨插件 / MCP）

全部返回 `{"success": bool, ...}`，失败时含 `"error"`（中文原因）：

| 方法 | 说明 |
|------|------|
| `run_pipeline()` | 运行当前图管线（异步，工作线程执行） |
| `stop_pipeline()` | 请求停止当前运行（协作式） |
| `save_graph(name="default")` | 将当前图序列化并经 DataProvider 持久化 |
| `load_graph(name="default")` | 恢复指定图；不存在/损坏时回退示例图 |
| `list_node_types()` | 列出全部已注册节点类型（含参数 schema） |
| `get_last_result_info()` | 最近一次运行汇总与 preview 结果元数据（不含图像本体） |

## 架构简介

严格四层（entrance 胶水 → service 接口 → function 业务 → ui 视图）：

```
blueprint_opencv/
├── entrance.py     # IPlugin 入口：生命周期、节点注册、服务初始化、主控件创建
├── information.py  # IPluginInfo：版本/依赖/service_api 声明
├── service.py      # BlueprintOpenCVService（QObject 门面 + Qt 信号封送 + service_api）
├── function/       # 纯 Python 业务层（禁 PySide6）：节点目录、op 实现、
│                   #   执行引擎（拓扑排序 + 数据流求值）、图像编解码、运行会话
├── ui/             # 视图层：BlueprintCanvas 宿主、工具条、属性面板、预览面板
├── config/         # 默认配置（图存档、预览尺寸、面板宽度、资产路径）
└── assets/         # 预置示例输入图片与示例图
```

关键设计：

- **线程边界**：`function/` 仅在工作线程活动（纯 numpy/PNG 字节），`ui/` 仅在 UI 线程；两者之间只传不可变数据，经 service 的 Qt 信号（`preview_ready` / `node_status_changed` / `run_finished`）自动排队封送，QPixmap 只在 UI 线程创建。
- **注册幂等**：`register_all_node_types()` 先查后注册，插件热重载不产生重复节点。
- **停止语义**：协作式停止，执行引擎在每个节点开始前检查停止标志。

详细技术方案见 `docs/req/2026-07-30/SPEC-blueprint-opencv-20260730.md`。
