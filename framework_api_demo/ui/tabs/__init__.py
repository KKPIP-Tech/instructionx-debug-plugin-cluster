# -*- coding: utf-8 -*-
"""ui/tabs 包：Framework API Demo 各演示 Tab。

re-export 各 Tab 类，保持外部引用稳定（from .tabs import DataTab 等）。
"""

from .data_tab import DataTab
from .task_tab import TaskTab
from .llm_tab import LLMTab
from .api_tab import APITab
from .info_tab import InfoTab

__all__ = ["DataTab", "TaskTab", "LLMTab", "APITab", "InfoTab"]
