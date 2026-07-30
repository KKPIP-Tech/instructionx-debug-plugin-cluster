# -*- coding: utf-8 -*-
"""LLM 演示 Tab 的多模态与统计校验分组（mixin）。

llm_tab.py 体量控制：将「多模态」「统计与校验」两个分组的构建与事件
处理拆到本模块，由 LLMTab 以 mixin 方式继承，行为与内联实现一致。
"""

import json
from typing import Any, Dict

from PySide6.QtWidgets import QFormLayout, QGroupBox

from InstructionX_UIKit.components import Button, LineEdit

from ...function.services.llm_service import (
    IMAGE_DONE_EVENT,
    IMAGE_ERROR_PREFIX,
    TTS_DONE_EVENT,
    TTS_ERROR_PREFIX,
)

# 多模态演示默认输入（无配置语义，仅演示占位）
DEFAULT_IMAGE_PROMPT = "一只在草地上晒太阳的猫"
DEFAULT_TTS_TEXT = "你好，这是文本转语音演示"


class LLMMediaStatsGroupsMixin:
    """多模态 / 统计与校验分组 mixin（由 LLMTab 继承）

    依赖宿主类提供：self.llm_service、self._display_result、self._log
    （由 LLMTab / BaseTab 注入）。
    """

    def _build_llm_multimodal_group(self) -> QGroupBox:
        """构建「多模态」分组（图片生成 + 文本转语音）"""
        group = QGroupBox("多模态")
        form = QFormLayout()
        form.setSpacing(6)
        self.image_prompt_input = LineEdit(text=DEFAULT_IMAGE_PROMPT)
        form.addRow("提示词:", self.image_prompt_input)
        self.image_gen_btn = Button("生成图片", variant="primary")
        self.image_gen_btn.clicked.connect(self._on_generate_image)
        form.addRow("", self.image_gen_btn)
        self.tts_text_input = LineEdit(text=DEFAULT_TTS_TEXT)
        form.addRow("文本:", self.tts_text_input)
        self.tts_btn = Button("文本转语音", variant="primary")
        self.tts_btn.clicked.connect(self._on_text_to_speech)
        form.addRow("", self.tts_btn)
        group.setLayout(form)
        return group

    def _build_llm_stats_group(self) -> QGroupBox:
        """构建「统计与校验」分组（用量统计 + Provider 校验）"""
        group = QGroupBox("统计与校验")
        form = QFormLayout()
        form.setSpacing(6)
        self.usage_conv_id_input = LineEdit(placeholder="会话 id（留空查全部）")
        form.addRow("会话 id:", self.usage_conv_id_input)
        self.usage_stats_btn = Button("获取用量统计", variant="primary")
        self.usage_stats_btn.clicked.connect(self._on_get_usage_stats)
        form.addRow("", self.usage_stats_btn)
        self.validate_provider_input = LineEdit(placeholder="Provider 实例 id（留空用默认）")
        form.addRow("Provider:", self.validate_provider_input)
        self.validate_provider_btn = Button("校验 Provider", variant="primary")
        self.validate_provider_btn.clicked.connect(self._on_validate_provider)
        form.addRow("", self.validate_provider_btn)
        group.setLayout(form)
        return group

    # ------------------------------------------------------------------
    #  事件处理（槽函数仅取输入、调服务、显示结果）
    # ------------------------------------------------------------------

    def _on_generate_image(self):
        """发起图片生成（后台任务，结果经 notifier 事件上抛）"""
        result = self.llm_service.generate_image_demo(self.image_prompt_input.text())
        self._log(f"图片生成发起: {result}")
        if not result.get("success"):
            self._display_result("图片生成发起失败", result.get("error", ""), is_error=True)

    def _on_text_to_speech(self):
        """发起语音合成（后台任务，结果经 notifier 事件上抛）"""
        result = self.llm_service.text_to_speech_demo(self.tts_text_input.text())
        self._log(f"语音合成发起: {result}")
        if not result.get("success"):
            self._display_result("语音合成发起失败", result.get("error", ""), is_error=True)

    def _on_get_usage_stats(self):
        """查询用量统计（同步快速调用，直接展示）"""
        conversation_id = self.usage_conv_id_input.text().strip() or None
        result = self.llm_service.get_usage_stats_demo(conversation_id)
        self._show_usage_stats_result(result)

    def _show_usage_stats_result(self, result: Dict[str, Any]):
        """展示用量统计结果（JSON 格式化，失败弹错误）"""
        self._log(f"用量统计: {result}")
        if not result.get("success"):
            self._display_result("获取用量统计失败", result.get("error", ""), is_error=True)
            return
        content = json.dumps(result.get("stats", {}), ensure_ascii=False, indent=2)
        self._display_result("用量统计", content)

    def _on_validate_provider(self):
        """校验 Provider 配置（留空时由服务层解析默认 chat 实例）"""
        provider = self.validate_provider_input.text().strip() or None
        result = self.llm_service.validate_provider_demo(provider)
        self._show_validate_result(result)

    def _show_validate_result(self, result: Dict[str, Any]):
        """展示 Provider 校验结果（通过/未通过/调用失败）"""
        self._log(f"Provider 校验: {result}")
        if not result.get("success"):
            self._display_result("校验 Provider 失败", result.get("error", ""), is_error=True)
            return
        valid = result.get("valid")
        title = "Provider 校验通过" if valid else "Provider 校验未通过"
        content = f"Provider: {result.get('provider')}\n{result.get('message') or '配置有效'}"
        self._display_result(title, content, is_error=not valid)

    # ------------------------------------------------------------------
    #  多模态 notifier 事件分发
    # ------------------------------------------------------------------

    def _dispatch_multimodal_event(self, message: str) -> bool:
        """UI 线程分发多模态事件；命中多模态协议返回 True，否则返回 False"""
        if message == IMAGE_DONE_EVENT:
            self._show_media_result("图片生成结果", self.llm_service.get_last_image_result())
            return True
        if message.startswith(IMAGE_ERROR_PREFIX):
            self._display_result("图片生成失败", message[len(IMAGE_ERROR_PREFIX):], is_error=True)
            return True
        if message == TTS_DONE_EVENT:
            self._show_media_result("语音合成结果", self.llm_service.get_last_audio_result())
            return True
        if message.startswith(TTS_ERROR_PREFIX):
            self._display_result("语音合成失败", message[len(TTS_ERROR_PREFIX):], is_error=True)
            return True
        return False

    def _show_media_result(self, title: str, payload: Dict[str, Any]):
        """多模态完成事件后拉取聚合结果，在结果面板展示（保存路径/大小/URL 等）"""
        result = payload.get("result") or {}
        lines = [f"{key}: {value}" for key, value in result.items() if value is not None]
        self._display_result(title, "\n".join(lines))
