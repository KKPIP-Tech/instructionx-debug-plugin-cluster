# -*- coding: utf-8 -*-
"""插件仓库 pytest 共享配置（test 分支专用）。

- 设置 offscreen 平台，保证 Qt 控件测试无窗口运行；
- 把框架根目录与 ui/ 加入 sys.path（插件以 ``plugin.<name>`` 包路径导入，
  UIKit 经 ui.uikit_bootstrap 引导为顶层包）；
- 提供 tmp_path 风格的隔离插件 id 工厂，避免测试污染真实运行数据目录。
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_FRAMEWORK_ROOT = Path(__file__).resolve().parents[2]
for _path in (str(_FRAMEWORK_ROOT), str(_FRAMEWORK_ROOT / "ui")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import ui.uikit_bootstrap  # noqa: E402,F401  # UIKit 顶层包引导（勿调整顺序）


@pytest.fixture()
def plugin_id() -> str:
    """生成一次性隔离插件 id（避免写入真实插件的数据目录）。"""
    return f"pytest-{uuid.uuid4().hex[:12]}"
