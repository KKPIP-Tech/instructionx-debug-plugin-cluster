# Official Plugin Cluster 结构规范

本规范定义 InstructionX 官方插件集（`plugin/` 目录）的统一目录结构和代码组织方式。所有官方插件必须遵循此规范。

## 总体结构

```
plugin/                                    # 官方插件集根目录
├── IXRepo.json                           # 插件集描述文件
├── PLUGIN_STRUCTURE_GUIDE.md             # 本文件
├── README.md                             # 插件集说明
└── <plugin-name>/                        # 单个插件目录
    ├── ixplugin.json                     # 插件描述文件
    ├── __init__.py                       # Python 包标识
    ├── entrance.py                       # 插件入口（胶水层）
    ├── service.py                        # 接口层（仅暴露 API）
    ├── information.py                    # 元数据（继承 IPluginInfo）
    ├── config/                           # 配置文件
    │   └── default.json
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

`config/default.json` 必须包含插件的所有可配置项：

```json
{
    "plugin_id": "plugin-id",
    "plugin_name": "Plugin Name",
    "defaults": {
        "key": "value"
    }
}
```

## 文档规范

### PRD.md

每个插件必须包含 `docs/PRD.md`，内容：
1. 概述 — 解决的问题和核心价值
2. 用户故事 — 目标用户和使用场景
3. 功能需求 — 编号列表
4. 插件类型和 ID
5. 目录结构（tree 图形）
6. 架构图（mermaid）

### IMPLEMENTATION_core.md

每个插件必须包含 `docs/IMPLEMENTATION_core.md`，内容：
1. 功能概述
2. 设计决策
3. 实现细节
4. 代码引用
5. mermaid 流程图和类图
