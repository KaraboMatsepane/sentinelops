"""
OpenAI SDK adapter for Band -- used by the Precedent Agent.

Demonstrates cross-framework usage in SentinelOps: while other agents use
httpx-based (ResilientAdapter) or LangChain-based approaches, this adapter
uses the official OpenAI Python SDK to call OpenAI-compatible endpoints.

Provider order: Featherless AI (primary) -> AI/ML API (fallback) -> hardcoded response.
"""

import logging
import os
from typing import Any

from openai import AsyncOpenAI

from band.core.protocols import AgentToolsProtocol
from band.core.types import PlatformMessage

from base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class OpenAIAdapter(BaseAdapter):
    """
    Band adapter that uses the official OpenAI Python SDK for LLM calls.

    Connects to OpenAI-compatible endpoints via AsyncOpenAI:
     - Primary: Featherless AI (Qwen/Qwen3-30B-A3B-Instruct-2507)
     - Fallback: AI/ML API (claude-sonnet-4-5-20250929)
     - Final fallback: hardcoded response if both providers fail
    """

    def __init__(
        self,
        *,
        agent_name: str,
        system_prompt: str,
        fallback_response: str,
        max_tokens: int = 2500,
        respond_to: list[str] | None = None,
        mention_targets: list[str] | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            fallback_response=fallback_response,
            max_tokens=max_tokens,
            respond_to=respond_to,
            mention_targets=mention_targets,
        )
        self._system_prompt = system_prompt

        featherless_api_key = os.getenv("FEATHERLESS_API_KEY", "")
        self._featherless_client = AsyncOpenAI(
            base_url="https://api.featherless.ai/v1",
            api_key=featherless_api_key,
        ) if featherless_api_key else None
        self._featherless_model = "Qwen/Qwen3-30B-A3B-Instruct-2507"

        aiml_api_key = os.getenv("AIML_API_KEY", "")
        aiml_base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.aimlapi.com")
        self._aiml_client = AsyncOpenAI(
            base_url=f"{aiml_base_url}/v1",
            api_key=aiml_api_key,
        ) if aiml_api_key else None
        self._aiml_model = "claude-sonnet-4-5-20250929"

    async def _call_featherless(self, messages: list[dict[str, str]]) -> str:
        if self._featherless_client is None:
            raise ValueError("FEATHERLESS_API_KEY not set")
        response = await self._featherless_client.chat.completions.create(
            model=self._featherless_model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Featherless returned empty content")
        return content

    async def _call_aiml(self, messages: list[dict[str, str]]) -> str:
        if self._aiml_client is None:
            raise ValueError("AIML_API_KEY not set")
        response = await self._aiml_client.chat.completions.create(
            model=self._aiml_model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("AI/ML API returned empty content")
        return content

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history: Any,
        participants_msg: str | None,
        contacts_msg: str | None,
        *,
        is_session_bootstrap: bool,
        room_id: str,
    ) -> None:
        sender = msg.sender_name or "unknown"
        logger.info("[%s] Message from %s (%s)", self.agent_name, sender, msg.sender_type)

        if not self._should_respond(msg):
            logger.info("[%s] Ignoring message from %s", self.agent_name, sender)
            return

        user_text = msg.format_for_llm()

        if room_id not in self._history:
            self._history[room_id] = []
        self._history[room_id].append({"role": "user", "content": user_text})

        messages = [
            {"role": "system", "content": self._system_prompt},
            *self._history[room_id],
        ]

        await self._notify_dashboard_status("active")

        text: str | None = None
        provider_used = "fallback"

        try:
            logger.info("[%s] Trying Featherless AI (OpenAI SDK)...", self.agent_name)
            text = await self._call_featherless(messages)
            provider_used = "openai-featherless"
            logger.info("[%s] Featherless AI succeeded (%d chars)", self.agent_name, len(text))
        except Exception as e:
            logger.warning("[%s] Featherless AI failed: %s", self.agent_name, e)

        if text is None:
            try:
                logger.info("[%s] Trying AI/ML API (OpenAI SDK)...", self.agent_name)
                text = await self._call_aiml(messages)
                provider_used = "openai-aiml"
                logger.info("[%s] AI/ML API succeeded (%d chars)", self.agent_name, len(text))
            except Exception as e:
                logger.warning("[%s] AI/ML API failed: %s", self.agent_name, e)

        if text is None:
            logger.warning("[%s] All providers failed - using fallback response", self.agent_name)
            text = self.fallback_response
            provider_used = "fallback"

        await self._send_and_notify(tools, text, provider_used, room_id)