# -*- coding: utf-8 -*-
"""DataDemoService 数据演示服务测试。

覆盖 function/services/data_service.py：
- demo_plugin_id 的确定性（同 plugin_id 重建不变、不同 plugin_id 不同、前缀）；
- 私有/公共数据读写与 get_all_data；
- 资源文件 save/load 与读取不存在资源的错误路径；
- 发布订阅：订阅→发布→事件收集（old/new value）、取消订阅后不再收事件、
  未注册演示插件时发布失败的异常路径；
- 事件通知回调（event_notifier）的上抛；
- register/unregister/cleanup 生命周期。

全部数据经隔离 DataProvider 落盘到 tmp_path，不触碰真实 data/ 目录。
"""

from plugin.framework_api_demo.function.services import DataDemoService

# 与 data_service 内默认配置一致的资源演示内容
DEMO_ASSET_CONTENT = "Demo asset content"


class TestDemoPluginId:
    """demo_plugin_id 的确定性生成"""

    def test_deterministic_across_instances(self, plugin_id, registered_provider):
        """同一 plugin_id 重建服务，demo_plugin_id 应保持一致"""
        first = DataDemoService(plugin_id, data_provider=registered_provider)
        second = DataDemoService(plugin_id, data_provider=registered_provider)
        assert first.demo_plugin_id == second.demo_plugin_id

    def test_differs_for_different_plugin_id(self, plugin_id, registered_provider):
        """不同 plugin_id 应生成不同的 demo_plugin_id"""
        first = DataDemoService(plugin_id, data_provider=registered_provider)
        second = DataDemoService(plugin_id + "-x", data_provider=registered_provider)
        assert first.demo_plugin_id != second.demo_plugin_id

    def test_prefix(self, data_service):
        """demo_plugin_id 应以配置前缀 demo-target- 开头"""
        assert data_service.demo_plugin_id.startswith("demo-target-")


class TestPrivatePublicData:
    """私有/公共数据读写"""

    def test_private_write_read_roundtrip(self, data_service):
        """私有数据写入后应读回相同值"""
        assert data_service.write_private_data("pkey", {"a": 1})["success"] is True
        result = data_service.read_private_data("pkey")
        assert result["success"] is True
        assert result["value"] == {"a": 1}

    def test_private_read_default_for_missing_key(self, data_service):
        """读取不存在的私有键应返回指定默认值"""
        result = data_service.read_private_data("missing", default="fallback")
        assert result["success"] is True
        assert result["value"] == "fallback"

    def test_public_write_read_roundtrip(self, data_service):
        """公共数据写入后应读回相同值"""
        assert data_service.write_public_data("ukey", 42)["success"] is True
        result = data_service.read_public_data("ukey")
        assert result["success"] is True
        assert result["value"] == 42

    def test_get_all_data_separates_namespaces(self, data_service):
        """get_all_data 应区分私有/公共命名空间，互不串数据"""
        data_service.write_private_data("only_private", "p")
        data_service.write_public_data("only_public", "u")
        result = data_service.get_all_data()
        assert result["success"] is True
        assert result["private"] == {"only_private": "p"}
        assert result["public"] == {"only_public": "u"}


class TestAssetOperation:
    """资源文件保存/加载"""

    def test_save_then_load_roundtrip(self, data_service):
        """保存资源后应能按默认路径读回原始内容"""
        save_result = data_service.save_demo_asset()
        assert save_result["success"] is True
        assert save_result["path"].endswith("demo.txt")

        load_result = data_service.load_demo_asset()
        assert load_result["success"] is True
        assert load_result["content"] == DEMO_ASSET_CONTENT

    def test_load_with_explicit_path(self, data_service):
        """显式传入 save 返回的相对路径也应读回内容"""
        save_result = data_service.save_demo_asset()
        load_result = data_service.load_demo_asset(save_result["path"])
        assert load_result["success"] is True
        assert load_result["content"] == DEMO_ASSET_CONTENT

    def test_load_nonexistent_asset_returns_error(self, data_service):
        """读取不存在的资源应返回 success=False 而非抛异常"""
        result = data_service.load_demo_asset("assets/plugins/none/not-here.txt")
        assert result["success"] is False
        assert result["error"]


class TestPublishSubscribe:
    """发布订阅演示与事件收集"""

    def test_subscribe_publish_collects_event(self, data_service):
        """订阅后发布应在事件缓存中记录 old/new value"""
        assert data_service.register_demo_plugin()["success"] is True
        assert data_service.subscribe_demo("greeting")["success"] is True
        assert data_service.publish_demo("greeting", "hello")["success"] is True

        events = data_service.get_subscription_events()["events"]
        assert len(events) == 1
        event = events[0]
        assert event["target_plugin_id"] == data_service.demo_plugin_id
        assert event["key"] == "greeting"
        assert event["old_value"] is None
        assert event["new_value"] == "hello"

    def test_second_publish_reports_old_value(self, data_service):
        """第二次发布同一键应携带上一次的 old_value"""
        data_service.register_demo_plugin()
        data_service.subscribe_demo("counter")
        data_service.publish_demo("counter", 1)
        data_service.publish_demo("counter", 2)

        events = data_service.get_subscription_events()["events"]
        assert len(events) == 2
        assert events[1]["old_value"] == 1
        assert events[1]["new_value"] == 2

    def test_unsubscribe_stops_events(self, data_service):
        """取消订阅后再发布不应产生新事件"""
        data_service.register_demo_plugin()
        data_service.subscribe_demo("k")
        data_service.publish_demo("k", "v1")
        assert data_service.unsubscribe_demo()["success"] is True
        data_service.publish_demo("k", "v2")

        events = data_service.get_subscription_events()["events"]
        assert len(events) == 1

    def test_publish_without_register_returns_error(self, data_service):
        """演示插件未注册时发布应返回 success=False"""
        result = data_service.publish_demo("k", "v")
        assert result["success"] is False
        assert result["error"]

    def test_subscribe_to_unregistered_target_returns_error(self, data_service):
        """订阅未注册的目标插件应返回 success=False"""
        result = data_service.subscribe_demo("k")
        assert result["success"] is False
        assert result["error"]

    def test_event_notifier_invoked(self, plugin_id, registered_provider):
        """注入的 event_notifier 应在发布时收到事件消息"""
        notified = []
        service = DataDemoService(
            plugin_id,
            data_provider=registered_provider,
            event_notifier=notified.append,
        )
        service.register_demo_plugin()
        service.subscribe_demo("k")
        service.publish_demo("k", "v")
        assert any("订阅事件" in message for message in notified)


class TestLifecycle:
    """注册/注销/清理生命周期"""

    def test_register_then_unregister(self, data_service):
        """注册演示插件后注销应成功"""
        assert data_service.register_demo_plugin()["success"] is True
        result = data_service.unregister_demo_plugin()
        assert result["success"] is True

    def test_unregister_without_register_returns_error(self, data_service):
        """未注册即注销应返回 success=False"""
        result = data_service.unregister_demo_plugin()
        assert result["success"] is False
        assert result["error"]

    def test_cleanup_is_tolerant(self, data_service):
        """cleanup 对未注册状态应容错不抛异常"""
        data_service.cleanup()

    def test_get_active_instance_after_register(
        self, data_service, registered_provider,
    ):
        """注册并设为活跃实例后，活跃实例查询应返回 demo_plugin_id"""
        data_service.register_demo_plugin()
        registered_provider.set_active_instance(data_service.demo_plugin_id)
        result = data_service.get_active_instance_demo()
        assert result["success"] is True
        assert result["plugin_type"] == "DemoTarget"
        assert result["active_instance"] == data_service.demo_plugin_id
