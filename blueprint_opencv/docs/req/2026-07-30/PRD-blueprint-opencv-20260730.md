# PRD — Blueprint OpenCV 插件

> - 创建日期：2026-07-30
> - 修改日期：2026-07-30
> - 文档状态：草案（待开发者评审）
> - 插件 id：`blueprint-opencv`
> - 对应技术方案：`SPEC-blueprint-opencv-20260730.md`（同目录）

---

## 1. 概述

**Blueprint OpenCV** 是 InstructionX 官方插件集（`plugin/`）下的一个新插件，承载双重价值：

1. **示范价值**：作为 UIKit Blueprint（蓝图节点图）组件的官方用法样板。完整演示 `BlueprintGraph` / `BlueprintCanvas` / `register_node_type` / `ExecutionController` 的核心用法：模块级节点类型注册、拖拉拽编辑、磁吸连线、`selection_changed` 驱动外部属性面板、图序列化（`to_dict` / `from_dict`）与预置示例图。开发者可以照抄本插件的组织方式开发自己的蓝图插件。
2. **实用价值**：一个可用的图像处理工具。将 OpenCV 常用操作节点化（输入、基础变换、滤波、阈值与边缘、形态学、调整、输出共 20 个节点），用户通过拖拉拽节点、连线、调节参数搭建图像处理管线，并在插件内实时预览处理结果。

定位参照：`plugin/ui_demo/ui/pages/blueprint.py` 是 Blueprint 组件的"功能演示页"（静态展示），本插件则是 Blueprint 的"完整应用样板"（可持久化、可执行、对外暴露 service_api）。

### 1.1 目标用户

- **插件开发者**：需要一个 Blueprint 组件的完整、可运行的参考实现。
- **最终用户**：需要快速验证 OpenCV 处理参数效果（如模糊核大小、Canny 阈值、形态学操作选择）的图像处理使用者。

### 1.2 非目标（Out of Scope）

- 不做视频/摄像头流处理，仅处理单张静态图像。
- 不做任意 Python 表达式节点、不做自定义节点脚本。
- 不做多图批处理与处理历史管理。
- 不做张量（tensor）数据流与深度学习推理节点。

---

## 2. 用户故事

| 编号 | 角色 | 故事 | 验收要点 |
|------|------|------|----------|
| US-1 | 插件开发者 | 阅读本插件源码，了解 Blueprint 节点类型注册、属性面板、执行指示的完整用法 | 代码分层清晰（entrance/service/function/ui），每个用法点有中文注释 |
| US-2 | 最终用户 | 打开插件即看到一张预置示例图（start→加载图片→高斯模糊→Canny→预览），点击"运行"看到处理结果与每个节点的执行状态 | 无需任何配置即可跑通；节点依次显示 running/done，预览区显示边缘检测结果 |
| US-3 | 最终用户 | 右键画布创建节点，从输出引脚拖线连接到下游输入引脚，搭出自己的处理链 | 创建菜单按分类分组；连线有类型校验（image 只能连 image）；单连接语义（一个输入引脚一条边） |
| US-4 | 最终用户 | 选中节点，在右侧属性面板修改参数（如高斯模糊 ksize），重新运行查看效果变化 | 属性面板按节点参数 schema 生成表单；修改即时写回节点 properties |
| US-5 | 最终用户 | 将搭好的图保存，下次打开插件自动恢复；也可另存/加载不同图 | 图经 DataProvider 持久化，重启应用后仍在 |
| US-6 | 最终用户 | 参数错误（如图片路径不存在）时，单个节点标红报错并中断该分支，其余分支不受影响，且弹窗告知原因 | 错误不导致应用崩溃；日志有完整上下文 |
| US-7 | 其他插件/MCP 客户端 | 通过 service_api 查询节点类型清单、触发管线运行、读取最近一次运行结果信息 | service_api 方法返回 `{"success": bool, ...}` 结构 |

---

## 3. 功能需求

### FR-1 节点目录（Node Catalog）

- FR-1.1：提供 20 个内置节点，分 7 个分类：**输入**（load_image、generate_noise、solid_color）、**基础**（grayscale、invert、resize、flip、rotate）、**滤波**（gaussian_blur、median_blur、bilateral）、**阈值与边缘**（threshold、adaptive_threshold、canny）、**形态学**（morphology）、**调整**（brightness_contrast、sharpen、hsv_convert）、**输出**（preview、save_image）。
- FR-1.2：每个节点定义 = Blueprint 注册信息（type_name / 标题 / 分类 / 引脚 / accent）+ 参数 schema（供属性面板生成表单）+ op 函数引用（纯 numpy/cv2 实现，位于 `function/`，不依赖 PySide6）。
- FR-1.3：节点引脚 data_type 使用内置类型 `image`（图像数据）与 `exec`（执行流），享有 Blueprint 内置引脚配色；`exec` 链决定执行顺序，`image` 链传递图像数据。
- FR-1.4：配合 Blueprint 内置 "start" 节点（流程分类，exec 输出）作为执行起点。
- FR-1.5：节点类型注册必须**幂等**：模块级注册在插件热重载（重复 import）时不得重复注册或抛异常（见 NFR-4）。

### FR-2 拖拉拽图编辑

- FR-2.1：右键画布弹出节点创建菜单，按分类分组展示全部节点类型，选中后在鼠标位置创建节点（`add_node_at`）。
- FR-2.2：从输出引脚拖线至输入引脚磁吸连线，类型不匹配时拒绝；输入引脚遵循单连接语义（重复连线替换旧边）。
- FR-2.3：Delete 键删除选中节点/边；删除节点时联动删除其所有连线。
- FR-2.4：提供"适应视图"（fit_view）与"清空画布"工具条操作；清空需二次确认。

### FR-3 参数面板

- FR-3.1：选中单个节点时，右侧面板按该节点的参数 schema 重建表单（ParamForm 风格：int/float/str/choice/file_path/color 六种字段类型）。
- FR-3.2：参数修改即时写回 `node.properties[key] = value` 并触发 `node.changed.emit()`；无需"应用"按钮。
- FR-3.3：未选中节点或多选时，面板显示空态提示（如"选中一个节点以编辑参数"）。
- FR-3.4：file_path 类型字段提供文件选择对话框；数值字段带范围约束（min/max）。

### FR-4 执行引擎

- FR-4.1：点击"运行"后，从 start 节点出发沿 exec 链拓扑排序得到执行顺序；无 start 节点或 exec 链成环时给出中文错误提示并拒绝运行。
- FR-4.2：数据流求值：执行到某节点时，沿其 `image` 输入边向上游取数（结果按图缓存，同一轮运行内每个节点只求值一次）。
- FR-4.3：执行期间每个节点经 `ExecutionController` 显示状态（running / done / error）与耗时。
- FR-4.4：单节点异常（如文件不存在、参数非法、cv2 报错）时该节点标 error、错误信息写日志并弹窗告知用户，当前 exec 分支中断；其余已连通的独立分支不受影响。
- FR-4.5：执行全程在 BackgroundTaskManager 工作线程进行，不得阻塞 UI（见 NFR-1）；运行中"运行"按钮置为"停止"，停止操作为协作式中断（当前节点执行完后停止）。
- FR-4.6：提供"重置状态"能力（`ExecutionController.reset`），清除全部节点状态指示。

### FR-5 结果预览

- FR-5.1：`preview` 节点执行时将其输入图像编码（imencode → PNG 字节）经回调上抛 UI，右下预览区（ImageView）显示。
- FR-5.2：多个 preview 节点时预览区显示最后一个执行的 preview 结果；结果信息区显示图像尺寸、通道数、节点耗时与运行总耗时。
- FR-5.3：预览区支持失败占位与空态（未运行时显示提示文案）。
- FR-5.4：QPixmap 创建与 ImageView.set_source 必须发生在 UI 线程。

### FR-6 图保存 / 加载

- FR-6.1："保存图"将 `canvas.to_dict()`（图结构 + 节点 properties + 视图状态）经 DataProvider save_asset 持久化到插件私有命名空间。
- FR-6.2：插件启动时若存在已保存图则自动恢复（`from_dict`），否则加载预置示例图。
- FR-6.3：支持命名多图（默认图 `default`）：工具条提供保存/加载入口，加载失败（数据损坏、含未知节点类型）时回退到示例图并弹窗提示。
- FR-6.4：图 JSON 同时可通过 service_api 读写（供跨插件/MCP 演示）。

### FR-7 预置示例图

- FR-7.1：内置示例图：start → load_image（指向插件自带示例图片资产）→ gaussian_blur → canny → preview，布局整齐、参数已填好默认值，开箱即可运行。
- FR-7.2：示例图片资产随插件分发（小尺寸 PNG，置于插件资产目录）。

### FR-8 跨插件 API（service_api）

- FR-8.1：`service.py` 提供 `BlueprintOpenCVService`（类名以 Service 结尾），`information.py` 声明 `service_api`，框架自动注册跨插件 API 并同步为 MCP 工具。
- FR-8.2：暴露方法：`run_pipeline()`、`stop_pipeline()`、`save_graph(name)`、`load_graph(name)`、`list_node_types()`、`get_last_result_info()`（完整签名见 SPEC §7）。
- FR-8.3：全部方法返回 `{"success": bool, ...}` 结构；在工作线程/跨线程场景下保证线程安全（运行触发走线程封送）。

---

## 4. 非功能需求

### NFR-1 性能与响应性

- cv2 图像处理全部在 BackgroundTaskManager 工作线程执行，UI 线程零阻塞；工作线程只产出 imencode 字节，QPixmap 创建与控件刷新回 UI 线程（经 Qt 信号自动排队或 `utils/thread_utils.run_in_ui_thread`）。
- 单图处理目标：1920×1080 图像、10 节点以内的管线，运行总耗时 < 2s（本机开发机参考值，不作为硬性 SLA）。

### NFR-2 依赖声明

- 框架未声明 OpenCV 依赖，插件必须在 `IXPlugin.json` 的 `dependencies` 中声明：`{"opencv-python": ">=4.8.0", "numpy": ">=1.24.0"}`，由框架 DependencyManager 自动检查/安装。
- 除上述两项外不引入新的第三方依赖；其余仅用框架（core）、UIKit 与 Python 标准库。

### NFR-3 代码规范

- 遵循插件开发硬性规则：`function/` 业务层禁 PySide6 / 禁 QWidget；ui/ 槽函数 ≤ 5 行并委托 service/function；函数 ≤ 20 行；嵌套 ≤ 3 层；无魔法数（有业务含义的字面量一律命名常量或进配置）；import 全部置顶（插件内相对导入、框架绝对导入）；中文注释与 docstring；全量 type hints。
- 目录名 snake_case（`blueprint_opencv/`），插件 id kebab-case（`blueprint-opencv`）。

### NFR-4 热重载安全

- 节点类型注册为模块级但**幂等**：重复 import（热重载）时跳过已注册类型，不抛异常、不产生重复菜单项。
- 卸载时不得残留：不持有全局画布实例引用；DataProvider 数据按插件命名空间隔离，随卸载语义由框架处理。

### NFR-5 错误处理

- 禁止裸 except 与静默吞异常；节点执行异常必须捕获、标 error、记 ERROR 日志（含节点 id/类型/参数上下文）并弹窗（影响用户操作结果的错误）。
- 图加载失败、依赖缺失（cv2 未安装）需有明确中文提示与降级路径。

### NFR-6 可测试性

- `function/` 层（节点 op、执行引擎、图像编解码）为纯 Python，可用脚本直接冒烟验证（临时脚本放仓库 `temp/`）；节点 op 以构造的 numpy 数组做输入断言输出。

---

## 5. 插件类型判断

- 本插件为 **`plugin/` 官方插件集内的新插件**（非 `custom_plugin/` 第三方插件），目录 `plugin/blueprint_opencv/`。
- 作为官方插件集成员，需**同步更新 `plugin/IXRepo.json`**（多插件仓库描述文件）登记新插件条目，保证 GitHub 一键安装/更新检查链路可发现本插件。
- 归 `plugin/` 仓库 dev 分支，按功能颗粒度提交（提交计划见 SPEC §9）。

---

## 6. 描述文件清单（IXPlugin.json 草案）

```json
{
  "id": "blueprint-opencv",
  "name": "Blueprint OpenCV",
  "version": "alpha.0.1.0",
  "description": "UIKit Blueprint 蓝图节点图官方样板：节点化 OpenCV 图像处理管线，拖拉拽搭建、参数调节、实时预览。",
  "author": "LumenThread",
  "dependencies": {
    "opencv-python": ">=4.8.0",
    "numpy": ">=1.24.0"
  },
  "min_app_version": "alpha.1.0.3",
  "category": "official",
  "tags": ["blueprint", "opencv", "image-processing", "demo"],
  "entry": "entrance.py"
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `id` | kebab-case，全仓库唯一 |
| `name` | 面板显示名 |
| `version` | `PluginVersion.from_string("alpha.0.1.0")`；新插件自测阶段用 alpha，随发布节奏升级 |
| `description` | 一句话说明双重定位（Blueprint 样板 + OpenCV 工具） |
| `author` | 官方插件统一 `LumenThread` |
| `dependencies` | Python 依赖声明，框架自动检查/安装；**必须包含 opencv-python 与 numpy** |
| `min_app_version` | 依赖的最低框架版本（Blueprint 组件自 alpha-v1.0.0 UIKit 起可用，当前框架 Alpha 1.0.3） |
| `category` / `tags` / `entry` | 面板分类展示与入口声明 |

### 随插件分发的文件清单

| 文件/目录 | 用途 |
|-----------|------|
| `IXPlugin.json` | 插件描述文件（如上草案） |
| `entrance.py` | IPlugin 入口（胶水层） |
| `information.py` | IPluginInfo（版本、service_api 声明） |
| `service.py` | BlueprintOpenCVService |
| `function/` | 节点目录、op 实现、执行引擎、图像编解码（纯 Python） |
| `ui/` | 主界面（画布、工具条、属性面板、预览区） |
| `config/default.json` | 默认配置（见 SPEC §8） |
| `assets/` | 示例图片等资产 |
| `README.md` | 插件说明（用法 + 作为 Blueprint 样板的导读） |
| `docs/req/2026-07-30/` | 本文档与 SPEC |

---

## 7. 里程碑

| 批次 | 内容 | 对应 FR |
|------|------|---------|
| B1 | 插件骨架 + 描述文件 | §6 |
| B2 | 节点目录与 op 实现 | FR-1 |
| B3 | 执行引擎 + 图像编解码 | FR-4（核心逻辑） |
| B4 | 主界面（画布/工具条/属性面板/预览） | FR-2、FR-3、FR-5 |
| B5 | service_api + 图保存/加载 | FR-6、FR-8 |
| B6 | 预置示例图 + 冒烟验证 | FR-7 |
| B7 | IXRepo.json 同步 + 文档收尾 | §5 |

详细任务拆分与 commit 信息建议见 SPEC §9。
