# -*- coding: utf-8 -*-
"""LLM 演示 Tab 的多模态与统计校验分组（mixin）。

llm_tab.py 体量控制：将「多模态」「统计与校验」两个分组的构建与事件
处理拆到本模块，由 LLMTab 以 mixin 方式继承，行为与内联实现一致。
静态文案经宿主类 _tr 取词并登记绑定，语言切换由基类 retranslate() 统一重设。
"""

import json
from typing import Any, Dict

from PySide6.QtWidgets import QFormLayout, QGroupBox

from InstructionX_UIKit.components import LineEdit

from ...function.services.llm_service import (
    IMAGE_DONE_EVENT,
    IMAGE_ERROR_PREFIX,
    TTS_DONE_EVENT,
    TTS_ERROR_PREFIX,
)


class LLMMediaStatsGroupsMixin:
    """多模态 / 统计与校验分组 mixin（由 LLMTab 继承）

    依赖宿主类提供：self.llm_service、self._display_result、self._log、
    self._tr / self._bind / self._make_group / self._make_button /
    self._make_label（由 LLMTab / BaseTab 注入）。
    """

    def _build_llm_multimodal_group(self) -> QGroupBox:
        """构建「多模态」分组（图片生成 + 文本转语音）"""
        group = self._make_group("group.multimodal")
        form = QFormLayout()
        form.setSpacing(6)
        self.image_prompt_input = self._make_default_input("default.image_prompt")
        form.addRow(self._make_label("tab_llm", "label.prompt"), self.image_prompt_input)
        self.image_gen_btn = self._make_button(
            "btn.gen_image", self._on_generate_image, variant="primary")
        form.addRow("", self.image_gen_btn)
        self.tts_text_input = self._make_default_input("default.tts_text")
        form.addRow(self._make_label("tab_llm", "label.text"), self.tts_text_input)
        self.tts_btn = self._make_button(
            "btn.tts", self._on_text_to_speech, variant="primary")
        form.addRow("", self.tts_btn)
        group.setLayout(form)
        return group

    def _build_llm_stats_group(self) -> QGroupBox:
        """构建「统计与校验」分组（用量统计 + Provider 校验）"""
        group = self._make_group("group.stats")
        form = QFormLayout()
        form.setSpacing(6)
        self.usage_conv_id_input = self._make_placeholder_input("placeholder.usage_conv_id")
        form.addRow(self._make_label("tab_llm", "label.conv_id"), self.usage_conv_id_input)
        self.usage_stats_btn = self._make_button(
            "btn.usage_stats", self._on_get_usage_stats, variant="primary")
        form.addRow("", self.usage_stats_btn)
        self.validate_provider_input = self._make_placeholder_input("placeholder.provider_id")
        form.addRow(self._make_label("tab_llm", "label.provider"),
                    self.validate_provider_input)
        self.validate_provider_btn = self._make_button(
            "btn.validate", self._on_validate_provider, variant="primary")
        form.addRow("", self.validate_provider_btn)
        group.setLayout(form)
        return group

    def _make_default_input(self, key: str) -> LineEdit:
        """创建默认值取词的输入框（默认演示文案随语言切换，不登记绑定）"""
        return LineEdit(text=self._tr("tab_llm", key))

    def _make_placeholder_input(self, key: str) -> LineEdit:
        """创建占位提示取词并登记重翻译绑定的输入框"""
        edit = LineEdit(placeholder=self._tr("tab_llm", key))
        self._bind(edit, "tab_llm", key, setter="setPlaceholderText")
        return edit

    # ------------------------------------------------------------------
    #  事件处理（槽函数仅取输入、调服务、显示结果）
    # ------------------------------------------------------------------

    def _on_generate_image(self):
        """发起图片生成（后台任务，结果经 notifier 事件上抛）"""
        result = self.llm_service.generate_image_demo(self.image_prompt_input.text())
        self._log(self._tr("tab_llm", "log.image_start", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.image_start_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_text_to_speech(self):
        """发起语音合成（后台任务，结果经 notifier 事件上抛）"""
        result = self.llm_service.text_to_speech_demo(self.tts_text_input.text())
        self._log(self._tr("tab_llm", "log.tts_start", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.tts_start_fail"),
                                 result.get("error", ""), is_error=True)

    def _on_get_usage_stats(self):
        """查询用量统计（同步快速调用，直接展示）"""
        conversation_id = self.usage_conv_id_input.text().strip() or None
        result = self.llm_service.get_usage_stats_demo(conversation_id)
        self._show_usage_stats_result(result)

    def _show_usage_stats_result(self, result: Dict[str, Any]):
        """展示用量统计结果（JSON 格式化，失败弹错误）"""
        self._log(self._tr("tab_llm", "log.usage", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.usage_fail"),
                                 result.get("error", ""), is_error=True)
            return
        content = json.dumps(result.get("stats", {}), ensure_ascii=False, indent=2)
        self._display_result(self._tr("tab_llm", "title.usage"), content)

    def _on_validate_provider(self):
        """校验 Provider 配置（留空时由服务层解析默认 chat 实例）"""
        provider = self.validate_provider_input.text().strip() or None
        result = self.llm_service.validate_provider_demo(provider)
        self._show_validate_result(result)

    def _show_validate_result(self, result: Dict[str, Any]):
        """展示 Provider 校验结果（通过/未通过/调用失败）"""
        self._log(self._tr("tab_llm", "log.validate", result=result))
        if not result.get("success"):
            self._display_result(self._tr("tab_llm", "title.validate_fail"),
                                 result.get("error", ""), is_error=True)
            return
        valid = result.get("valid")
        title_key = "title.validate_ok" if valid else "title.validate_not_ok"
        content = self._tr("tab_llm", "msg.validate_content",
                           provider=result.get("provider"),
                           message=result.get("message")
                           or self._tr("tab_llm", "msg.config_valid"))
        self._display_result(self._tr("tab_llm", title_key), content,
                             is_error=not valid)

    # ------------------------------------------------------------------
    #  多模态 notifier 事件分发
    # ------------------------------------------------------------------

    def _dispatch_multimodal_event(self, message: str) -> bool:
        """UI 线程分发多模态事件；命中多模态协议返回 True，否则返回 False"""
        if message == IMAGE_DONE_EVENT:
            self._show_media_result(self._tr("tab_llm", "title.image_result"),
                                    self.llm_service.get_last_image_result())
            return True
        if message.startswith(IMAGE_ERROR_PREFIX):
            self._show_media_error("title.image_fail", message, IMAGE_ERROR_PREFIX)
            return True
        if message == TTS_DONE_EVENT:
            self._show_media_result(self._tr("tab_llm", "title.tts_result"),
                                    self.llm_service.get_last_audio_result())
            return True
        if message.startswith(TTS_ERROR_PREFIX):
            self._show_media_error("title.tts_fail", message, TTS_ERROR_PREFIX)
            return True
        return False

    def _show_media_error(self, title_key: str, message: str, prefix: str):
        """统一展示多模态失败：按协议前缀剥离错误文本后展示"""
        self._display_result(self._tr("tab_llm", title_key),
                             message[len(prefix):], is_error=True)

    def _show_media_result(self, title: str, payload: Dict[str, Any]):
        """多模态完成事件后拉取聚合结果，在结果面板展示（保存路径/大小/URL 等）"""
        result = payload.get("result") or {}
        lines = [f"{key}: {value}" for key, value in result.items() if value is not None]
        self._display_result(title, "\n".join(lines))
