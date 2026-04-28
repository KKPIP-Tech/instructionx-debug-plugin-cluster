"""
任务报告生成器服务
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from core.data.data_provider import DataProvider, DataProviderError, DataNamespace
from utils.logging_tools import LoggerManager, get_name

DEFAULT_CONFIG = {
    "refresh": {"interval_ms": 3000, "event_history_limit": 20},
    "task_manager": {"default_key": "TaskManager", "statistics_key": "statistics",
                     "last_event_key": "last_event"},
    "report": {"default_format": "json", "supported_formats": ["json", "txt", "html"],
               "event_limit": 50, "event_display_limit": 10}
}


def _load_config() -> Dict[str, Any]:
    """从 config/default.json 加载配置，失败时返回默认值"""
    try:
        config_path = Path(__file__).parent / "config" / "default.json"
        raw = config_path.read_text(encoding="utf-8")
        local = json.loads(raw)
        cfg = DEFAULT_CONFIG.copy()
        for section, values in local.items():
            if isinstance(values, dict):
                cfg.setdefault(section, {}).update(values)
            else:
                cfg[section] = values
        return cfg
    except Exception:
        return DEFAULT_CONFIG


class Service:
    """报告生成服务"""

    _logger = LoggerManager()
    _config = _load_config()

    def __init__(self, plugin_id: str):
        self.plugin_id = plugin_id
        self.data_provider = DataProvider()
        self.event_log: List[Dict[str, Any]] = []

    def get_active_task_manager_id(self) -> Optional[str]:
        key = self._config.get("task_manager", {}).get("default_key", "TaskManager")
        return self.data_provider.get_active_instance(key)

    def _resolve_task_manager_id(self, task_manager_id: Optional[str]) -> Optional[str]:
        if task_manager_id:
            return task_manager_id
        return self.get_active_task_manager_id()

    def subscribe_to_task_manager(self, task_manager_id: Optional[str] = None) -> bool:
        resolved_id = self._resolve_task_manager_id(task_manager_id)
        if not resolved_id:
            self._logger.warning(get_name(), "Subscribe failed: No active TaskManager instance")
            return False
        try:
            cfg = self._config.get("task_manager", {})
            self.data_provider.subscribe(self.plugin_id, resolved_id, cfg.get("statistics_key", "statistics"), self._on_statistics_changed)
            self.data_provider.subscribe(self.plugin_id, resolved_id, cfg.get("last_event_key", "last_event"), self._on_task_event)
            return True
        except DataProviderError as e:
            self._logger.warning(get_name(), f"Subscribe failed: {e}")
            return False

    def unsubscribe_from_task_manager(self, task_manager_id: Optional[str] = None):
        self.data_provider.unsubscribe(self.plugin_id, task_manager_id)

    def _on_statistics_changed(self, target_plugin_id: str, key: str,
                                old_value: Any, new_value: Any):
        self.event_log.append({
            "timestamp": datetime.now().isoformat(),
            "type": "statistics_changed",
            "plugin_id": target_plugin_id,
            "old_stats": old_value,
            "new_stats": new_value
        })
        self._save_event_log()

    def _on_task_event(self, target_plugin_id: str, key: str,
                       old_value: Any, new_value: Any):
        if new_value and "type" in new_value:
            self.event_log.append({
                "timestamp": datetime.now().isoformat(),
                "type": "task_event",
                "plugin_id": target_plugin_id,
                "event_type": new_value.get("type"),
                "event_data": new_value
            })
            self._save_event_log()

    def _save_event_log(self) -> None:
        try:
            self.data_provider.set_plugin_data(
                self.plugin_id, "event_log", self.event_log, DataNamespace.PRIVATE)
        except DataProviderError as e:
            self._logger.warning(get_name(), f"Cannot save event log: {e}")

    def get_statistics_report(self, task_manager_id: Optional[str] = None) -> Dict[str, Any]:
        resolved_id = self._resolve_task_manager_id(task_manager_id)
        if not resolved_id:
            return {"error": "未找到活跃的 TaskManager 实例"}
        try:
            key = self._config.get("task_manager", {}).get("statistics_key", "statistics")
            stats = self.data_provider.get_plugin_data(resolved_id, key, DataNamespace.PUBLIC, None)
            if not stats:
                return {"error": "无法获取统计信息"}
            total = stats.get("total", 0)
            completed = stats.get("completed", 0)
            completion_rate = (completed / total * 100) if total > 0 else 0
            ratio = lambda k: round(stats.get(k, 0) / total * 100, 2) if total > 0 else 0
            return {"generated_at": datetime.now().isoformat(), "task_manager_id": resolved_id, "statistics": stats,
                    "metrics": {"completion_rate": round(completion_rate, 2), "pending_ratio": ratio("pending"), "in_progress_ratio": ratio("in_progress")}}
        except Exception as e:
            return {"error": str(e)}

    def get_event_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            self.event_log = self.data_provider.get_plugin_data(
                self.plugin_id, "event_log", DataNamespace.PRIVATE, [])
        except DataProviderError:
            self.event_log = []
        default_limit = self._config.get("refresh", {}).get("event_history_limit", 20)
        return self.event_log[-min(limit, default_limit):]

    def generate_report(self, task_manager_id: Optional[str] = None, format: str = "json") -> str:
        resolved_id = self._resolve_task_manager_id(task_manager_id)
        if not resolved_id:
            raise ValueError("未找到活跃的 TaskManager 实例")
        cfg = self._config.get("report", {})
        stats_report = self.get_statistics_report(resolved_id)
        events = self.get_event_history(cfg.get("event_limit", 50))
        report_data = {"generated_at": datetime.now().isoformat(), "task_manager_id": resolved_id,
                       "statistics_report": stats_report, "recent_events": events, "total_events": len(self.event_log)}
        if format not in cfg.get("supported_formats", ["json", "txt", "html"]):
            raise ValueError(f"不支持的报告格式: {format}")
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        dl = cfg.get("event_display_limit", 10)
        builders = {"json": (json.dumps(report_data, ensure_ascii=False, indent=2).encode("utf-8"), f"report_{ts}.json"),
                    "txt": (self._build_txt_report(report_data, stats_report, events, dl), f"report_{ts}.txt"),
                    "html": (self._build_html_report(report_data, stats_report, events, dl), f"report_{ts}.html")}
        content, filename = builders[format]
        return self.data_provider.save_asset(self.plugin_id, filename, content)

    def _build_txt_report(self, report_data: Dict, stats_report: Dict,
                          events: List, display_limit: int) -> bytes:
        lines = self._txt_header(report_data)
        lines.extend(self._txt_stats_section(stats_report))
        lines.extend(self._txt_events_section(events, display_limit))
        lines.append(f"总事件数: {report_data['total_events']}")
        return "\n".join(lines).encode("utf-8")

    def _txt_header(self, report_data: Dict) -> List[str]:
        return [
            "任务管理器报告", "=" * 50,
            f"生成时间: {report_data['generated_at']}",
            f"任务管理器ID: {report_data['task_manager_id']}", "",
            "统计信息:", "-" * 30
        ]

    def _txt_stats_section(self, stats_report: Dict) -> List[str]:
        lines = []
        if "statistics" in stats_report:
            stats = stats_report["statistics"]
            for label, key in [("总计", "total"), ("待办", "pending"),
                                ("进行中", "in_progress"), ("已完成", "completed"),
                                ("已取消", "cancelled")]:
                lines.append(f"  {label}: {stats.get(key, 0)}")
            lines.append("")
        if "metrics" in stats_report:
            lines.extend(["性能指标:", "-" * 30])
            for label, key in [("完成率", "completion_rate"),
                               ("待办比例", "pending_ratio"),
                               ("进行中比例", "in_progress_ratio")]:
                lines.append(f"  {label}: {stats_report['metrics'].get(key, 0)}%")
            lines.append("")
        return lines

    def _txt_events_section(self, events: List, display_limit: int) -> List[str]:
        lines = ["最近事件:", "-" * 30]
        for event in events[-display_limit:]:
            ts = event.get("timestamp", "")
            typ = event.get("type", "unknown")
            lines.append(f"  [{ts}] {typ}")
        lines.append("")
        return lines

    def _build_html_report(self, report_data: Dict, stats_report: Dict,
                           events: List, display_limit: int) -> bytes:
        html = self._html_header(report_data)
        html += self._html_stats(stats_report)
        html += self._html_metrics(stats_report)
        html += self._html_events(events, display_limit, report_data["total_events"])
        return html.encode("utf-8")

    def _html_header(self, report_data: Dict) -> str:
        return (
            "<!DOCTYPE html>\n<html>\n<head>\n"
            "    <meta charset=\"UTF-8\">\n"
            "    <title>任务管理器报告</title>\n"
            + self._html_style()
            + "</head>\n<body>\n"
            f"    <h1>任务管理器报告</h1>\n"
            f"    <p><strong>生成时间:</strong> {report_data['generated_at']}</p>\n"
            f"    <p><strong>任务管理器ID:</strong> {report_data['task_manager_id']}</p>\n"
            "    <h2>统计信息</h2>\n"
        )

    def _html_style(self) -> str:
        return (
            "    <style>\n"
            "        body { font-family: Arial, sans-serif; margin: 20px; }\n"
            "        h1 { color: #333; }\n"
            "        table { border-collapse: collapse; width: 100%; margin-top: 20px; }\n"
            "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }\n"
            "        th { background-color: #4CAF50; color: white; }\n"
            "        tr:nth-child(even) { background-color: #f2f2f2; }\n"
            "        .metric { margin: 10px 0; padding: 10px; "
            "background: #e7f3ff; border-radius: 5px; }\n"
            "    </style>\n"
        )

    def _html_stats(self, stats_report: Dict) -> str:
        if "statistics" not in stats_report:
            return ""
        stats = stats_report["statistics"]
        rows = [
            ("总计", "total"), ("待办", "pending"),
            ("进行中", "in_progress"), ("已完成", "completed"), ("已取消", "cancelled")
        ]
        html = "    <table>\n        <tr><th>状态</th><th>数量</th></tr>\n"
        for label, key in rows:
            html += f"        <tr><td>{label}</td><td>{stats.get(key, 0)}</td></tr>\n"
        return html + "    </table>\n"

    def _html_metrics(self, stats_report: Dict) -> str:
        if "metrics" not in stats_report:
            return ""
        m = stats_report["metrics"]
        html = "    <h2>性能指标</h2>\n"
        for label, key in [("完成率", "completion_rate"),
                          ("待办比例", "pending_ratio"),
                          ("进行中比例", "in_progress_ratio")]:
            html += f"    <div class=\"metric\">{label}: {m.get(key, 0)}%</div>\n"
        return html

    def _html_events(self, events: List, display_limit: int, total: int) -> str:
        html = (
            f"    <h2>最近事件</h2>\n"
            f"    <p><strong>总事件数:</strong> {total}</p>\n"
            "    <table>\n"
            "        <tr><th>时间</th><th>类型</th></tr>\n"
        )
        for event in events[-display_limit:]:
            ts = event.get("timestamp", "")
            typ = event.get("type", "unknown")
            html += f"        <tr><td>{ts}</td><td>{typ}</td></tr>\n"
        return html + "    </table>\n</body>\n</html>\n"

    def clear_event_log(self) -> None:
        self.event_log = []
        self._save_event_log()
