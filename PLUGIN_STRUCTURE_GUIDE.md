# Official Plugin Cluster 结构规范

本规范定义 InstructionX 官方插件集（`plugin/` 目录）的统一目录结构和代码组织方式。所有官方插件必须遵循此规范。

## 总体结构

```
plugin/                                    # 官方插件集根目录
├── IXRepo.json                           # 插件集描述文件
├── PLUGIN_STRUCTURE_GUIDE.md             # 本文件
├── README.md                             # 插件集说明
└── <plugin-name>/                        # 单个插件目录
    ├── IXPlugin.json                     # 插件描述文件（文件名大小写敏感，必须为 IXPlugin.json）
    ├── __init__.py                       # Python 包标识
    ├── entrance.py                       # 插件入口（胶水层）
    ├── service.py                        # 接口层（仅暴露 API）
    ├── information.py                    # 元数据（继承 IPluginInfo）
    ├── config/                           # 配置文件
    │   └── default.json
    ├── text/                             # 语言包目录（可选）：<语言代码>.xml，一个语言一个文件
    │   ├── zh.xml                        # 默认语言文件（必须覆盖全部键）
    │   └── en.xml
    ├── ui/                               # UI 组件层
    │   ├── __init__.py
    │   └── main_widget.py                # 主控件
    ├── function/                         # 业务功能层
    │   ├── __init__.py
    │   └── services/                     # 服务子模块
    │       ├── __init__.py
    │       └── core_service.py           # 核心业务逻辑
    ├── icons/                            # 图标资源
    ├── assets/                           # 其他资源
    └── docs/                             # 插件文档
        ├── PRD.md                        # 设计文档
        └── IMPLEMENTATION_core.md        # 实现文档
```

## 职责划分（严格区分）

| 文件/目录 | 职责 | 禁止 |
|-----------|------|------|
| `entrance.py` | 胶水层：实例化 Service 和 UI，连接两者 | 写业务逻辑、写 UI 构建代码 |
| `service.py` | 接口层：对外暴露 API，委托给 `function/` | 写业务逻辑、UI 操作代码 |
| `function/services/` | 业务逻辑：数据处理、外部 API 调用 | 创建 QWidget、依赖 PySide6 |
| `ui/` | UI 层：所有 Qt 控件相关代码 | 写业务逻辑 |
| `information.py` | 元数据：版本、作者、描述、service_api | 写运行时逻辑 |
| `config/` | 配置：所有可配置项，禁止魔法数 | — |
| `text/` | 语言包：用户可见文案按 `<语言代码>.xml` 组织，经 `services.localization` 取词；框架加载时自动扫描注册 | 在代码中硬编码用户可见文案 |

## 导入规范

统一使用相对导入：

```python
# entrance.py
from .service import Service
from .ui.main_widget import MainWidget

# service.py
from .function.services.core_service import CoreService

# ui/main_widget.py
from ..service import Service
```

## 配置规范

`config/default.json` 必须集中承载插件的所有可配置项（禁止魔法数散落在代码中）。内部结构按插件业务分组组织，不做固定 schema 限定，例如：

```json
{
    "graph": {"max_nodes": 64},
    "preview": {"max_width": 640, "max_height": 480},
    "panel": {"right_panel_width": 360}
}
```

配置项必须在代码中真实接线读取；删除某个配置项时同步移除读取方，新增可配置数值时优先进配置而非硬编码常量。

## 文档规范

### PRD 与 SPEC（docs/req/）

需求文档存放在 `docs/req/<YYYY-MM-DD>/` 下，按日期分文件夹；文件命名 `PRD-<需求名>-<YYYYMMDD>.md` 与 `SPEC-<需求名>-<YYYYMMDD>.md`，文首注明创建日期与修改日期（与 `AGENTS-for-PLUGIN-DEV.md` 的开发流程一致）。

- **PRD 内容**：概述（解决的问题与核心价值）、用户故事、功能需求（编号列表）、非功能需求、插件类型与 ID、描述文件清单；
- **SPEC 内容**：技术方案与设计决策（Why）、目录结构与模块划分、数据流向（mermaid）、类与接口关系（mermaid 类图）、状态机设计（如适用）、涉及修改的描述文件与配置项。

> 历史说明：`framework_api_demo/docs/` 下保留的旧式 `PRD.md` / `IMPLEMENTATION_core.md` 为规范演进前的文档形态，仅作溯源参考，新增需求一律采用 `docs/req/` 规范。
