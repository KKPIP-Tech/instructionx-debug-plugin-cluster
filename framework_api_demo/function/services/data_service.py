"""
Framework API Demo 数据演示服务

演示 DataProvider 接口（注册/注销插件、私有/公共数据读写、资源文件、
发布订阅通信与活跃实例查询）。
"""

import hashlib
from typing import Any, Callable, Dict, List, Optional

from core.data.data_provider import DataNamespace
from utils.logging_tools import get_name

from .base import Service, _load_config

# 订阅事件缓存上限：超出后丢弃最旧的事件，防止长期订阅导致内存无限增长
MAX_SUBSCRIPTION_EVENTS = 100


class DataDemoService(Service):
    """演示 DataProvider 接口的服务类"""

    def __init__(self, plugin_id, services=None, data_provider=None,
                 event_notifier: Optional[Callable[[str], None]] = None):
        super().__init__(plugin_id, services=services, data_provider=data_provider)
        config = _load_config()
        demo_cfg = config.get("demo", {})
        prefix = demo_cfg.get("plugin_id_prefix", "demo-target")
        hex_len = demo_cfg.get("plugin_id_hex_length", 8)
        # 使用确定性哈希，确保服务重建后 demo_plugin_id 不变
        hash_val = hashlib.md5(plugin_id.encode()).hexdigest()[:hex_len]
        self.demo_plugin_id = f"{prefix}-{hash_val}"
        self._last_asset_path: Optional[str] = None
        # 订阅事件缓存与 UI 通知回调（订阅回调在工作线程触发，
        # 事件先入缓存，UI 经 notifier 封送后自行拉取展示）
        self._events: List[Dict[str, Any]] = []
        self._event_notifier = event_notifier

    def register_demo_plugin(self) -> Dict[str, Any]:
        """演示注册插件"""
        try:
            self.dp.register_plugin(self.demo_plugin_id, "DemoTarget")
            self.logger.info(get_name(), f"成功注册演示插件: {self.demo_plugin_id}")
            return {"success": True, "message": f"插件 {self.demo_plugin_id} 注册成功"}
        except Exception as e:
            self.logger.error(get_name(), f"注册插件失败: {e}")
            return {"success": False, "error": str(e)}

    def unregister_demo_plugin(self) -> Dict[str, Any]:
        """演示注销插件"""
        try:
            self.dp.unregister_plugin(self.demo_plugin_id)
            self.logger.info(get_name(), f"成功注销演示插件: {self.demo_plugin_id}")
            return {"success": True, "message": f"插件 {self.demo_plugin_id} 注销成功"}
        except Exception as e:
            self.logger.error(get_name(), f"注销插件失败: {e}")
            return {"success": False, "error": str(e)}

    def cleanup(self) -> None:
        """卸载清理：先取消全部订阅，再注销演示插件命名空间（逐项容错记日志）"""
        try:
            self.dp.unsubscribe(self.plugin_id)
            self.logger.info(get_name(), "卸载清理：已取消全部数据订阅")
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：取消订阅失败: {e}")
        try:
            self.dp.unregister_plugin(self.demo_plugin_id)
            self.logger.info(get_name(), f"卸载清理：已注销演示插件 {self.demo_plugin_id}")
        except Exception as e:
            self.logger.error(get_name(), f"卸载清理：注销演示插件失败: {e}")

    def write_private_data(self, key: str, value: Any) -> Dict[str, Any]:
        """演示写入私有数据"""
        try:
            self.dp.set_plugin_data(self.plugin_id, key, value, DataNamespace.PRIVATE)
            return {"success": True, "message": f"写入私有数据成功: {key}={value}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_private_data(self, key: str, default: Any = None) -> Dict[str, Any]:
        """演示读取私有数据"""
        try:
            value = self.dp.get_plugin_data(self.plugin_id, key, DataNamespace.PRIVATE, default)
            return {"success": True, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_public_data(self, key: str, value: Any) -> Dict[str, Any]:
        """演示写入公共数据"""
        try:
            self.dp.set_plugin_data(self.plugin_id, key, value, DataNamespace.PUBLIC)
            return {"success": True, "message": f"写入公共数据成功: {key}={value}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_public_data(self, key: str, default: Any = None) -> Dict[str, Any]:
        """演示读取公共数据"""
        try:
            value = self.dp.get_plugin_data(self.plugin_id, key, DataNamespace.PUBLIC, default)
            return {"success": True, "value": value}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_all_data(self) -> Dict[str, Any]:
        """演示获取所有数据"""
        try:
            private_data = self.dp.get_all_plugin_data(self.plugin_id, DataNamespace.PRIVATE)
            public_data = self.dp.get_all_plugin_data(self.plugin_id, DataNamespace.PUBLIC)
            return {"success": True, "private": private_data, "public": public_data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_demo_asset(self) -> Dict[str, Any]:
        """演示保存资源文件"""
        try:
            content = b"Demo asset content"
            relative_path = self.dp.save_asset(self.plugin_id, "demo.txt", content)
            self._last_asset_path = relative_path
            return {"success": True, "path": relative_path}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_demo_asset(self, relative_path: str = None) -> Dict[str, Any]:
        """演示加载资源文件"""
        try:
            default_path = f"assets/plugins/{self.plugin_id}/demo.txt"
            path = relative_path or self._last_asset_path or default_path
            content = self.dp.load_asset(path)
            return {"success": True, "content": content.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  发布订阅演示
    # ------------------------------------------------------------------

    def subscribe_demo(self, key: str) -> Dict[str, Any]:
        """演示订阅：以本插件身份订阅演示插件 PUBLIC 命名空间下指定键的变化"""
        try:
            self.dp.subscribe(
                subscriber_id=self.plugin_id,
                target_plugin_id=self.demo_plugin_id,
                target_key=key,
                callback=self._on_subscription_event,
            )
            self.logger.info(get_name(), f"已订阅 {self.demo_plugin_id}.{key}")
            return {"success": True, "message": f"已订阅 {self.demo_plugin_id} 的键: {key}"}
        except Exception as e:
            self.logger.error(get_name(), f"订阅失败: {e}")
            return {"success": False, "error": str(e)}

    def publish_demo(self, key: str, value: Any) -> Dict[str, Any]:
        """演示发布：以演示插件身份向 PUBLIC 命名空间发布数据（触发订阅回调）"""
        try:
            self.dp.publish(self.demo_plugin_id, key, value)
            return {"success": True, "message": f"已发布 {self.demo_plugin_id}.{key} = {value}"}
        except Exception as e:
            self.logger.error(get_name(), f"发布失败: {e}")
            return {"success": False, "error": str(e)}

    def unsubscribe_demo(self) -> Dict[str, Any]:
        """演示取消订阅：取消本插件的全部订阅"""
        try:
            self.dp.unsubscribe(self.plugin_id)
            return {"success": True, "message": "已取消本插件的全部订阅"}
        except Exception as e:
            self.logger.error(get_name(), f"取消订阅失败: {e}")
            return {"success": False, "error": str(e)}

    def get_subscription_events(self) -> Dict[str, Any]:
        """返回已收集的订阅事件列表（供 UI 拉取展示）"""
        return {"success": True, "events": list(self._events)}

    def get_active_instance_demo(self) -> Dict[str, Any]:
        """演示按插件类型查询当前活跃实例 ID"""
        try:
            active_id = self.dp.get_active_instance("DemoTarget")
            return {"success": True, "plugin_type": "DemoTarget", "active_instance": active_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _on_subscription_event(self, target_plugin_id: str, key: str,
                               old_value: Any, new_value: Any) -> None:
        """订阅回调（在工作线程执行）：事件入有界缓存并通知 UI，异常仅记日志"""
        try:
            event = {
                "target_plugin_id": target_plugin_id,
                "key": key,
                "old_value": old_value,
                "new_value": new_value,
            }
            self._events.append(event)
            if len(self._events) > MAX_SUBSCRIPTION_EVENTS:
                del self._events[:len(self._events) - MAX_SUBSCRIPTION_EVENTS]
            self._notify_event(f"订阅事件: {target_plugin_id}.{key} = {new_value}")
        except Exception as e:
            self.logger.error(get_name(), f"订阅回调处理失败: {e}")
