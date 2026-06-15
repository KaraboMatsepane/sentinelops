"""
Multi-provider LLM adapter with configurable provider order and automatic fallback.

Default: AI/ML API -> Featherless AI -> hardcoded response.
Precedent Agent: Featherless AI -> AI/ML API -> hardcoded response.
Posts events to the local dashboard server for live visualization.
"""

import logging
import os
from typing import Any

import httpx

from band.core.protocols import AgentToolsProtocol
from band.core.types import PlatformMessage

from base_adapter import BaseAdapter, strip_markdown  # noqa: F401 - re-export strip_markdown

logger = logging.getLogger(__name__)


class ResilientAdapter(BaseAdapter):
    """
    Band adapter that tries multiple LLM providers in configurable order.

    Provider order is configurable via provider_order parameter:
   - Default: ["aiml", "featherless"] (AI/ML API first)
   - Precedent Agent: ["featherless", "aiml"] (Featherless AI first)
   - Final fallback: hardcoded response if all providers fail

    Band chat: receives clean plain text (no markdown clutter)
    Dashboard: receives original markdown for rich formatted rendering
    """

    def __init__(
            self,
            *,
            agent_name: str,
            system_prompt: str,
            fallback_response: str,
            max_tokens: int = 2500,
            aiml_model: str = "claude-sonnet-4-5-20250929",
            featherless_model: str = "Qwen/Qwen3-30B-A3B-Instruct-2507",
            respond_to: list[str] | None = None,
            wait_for_all: list[str] | None = None,
            mention_targets: list[str] | None = None,
            trigger_phrase: str | None = None,
            provider_order: list[str] | None = None,
    ):
        super().__init__(
            agent_name=agent_name,
            fallback_response=fallback_response,
            max_tokens=max_tokens,
            respond_to=respond_to,
            mention_targets=mention_targets,
        )
        self._system_prompt = system_prompt
        self.aiml_model = aiml_model
        self.featherless_model = featherless_model
        self.wait_for_all = wait_for_all
        self.trigger_phrase = trigger_phrase
        self.provider_order = provider_order or ["aiml", "featherless"]
        self._received_from: dict[str, dict[str, str]] = {}

    async def _call_aiml(self, messages: list[dict]) -> str:
        api_key = os.getenv("AIML_API_KEY", "")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.aimlapi.com")
        if not api_key:
            raise ValueError("AIML_API_KEY not set")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{base_url}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.aiml_model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def _call_featherless(self, messages: list[dict]) -> str:
        api_key = os.getenv("FEATHERLESS_API_KEY", "")
        if not api_key:
            raise ValueError("FEATHERLESS_API_KEY not set")

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://api.featherless.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.featherless_model,
                    "messages": messages,
                    "max_tokens": self.max_tokens,
                    "temperature": 0.7,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

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

        user_text = msg.format_for_llm()

        is_trigger = bool(
            self.trigger_phrase
            and self.trigger_phrase.lower() in user_text.lower()
        )

        if not is_trigger and not self._should_respond(msg):
            logger.info("[%s] Ignoring message from %s", self.agent_name, sender)
            return

        if self.wait_for_all:
            if room_id not in self._received_from:
                self._received_from[room_id] = {}
            for required_sender in self.wait_for_all:
                if required_sender.lower() in sender.lower():
                    self._received_from[room_id][required_sender] = user_text
                    break

            received = set(self._received_from[room_id].keys())
            required = set(self.wait_for_all)
            if not required.issubset(received):
                still_waiting = required - received
                logger.info("[%s] Still waiting for: %s", self.agent_name, still_waiting)
                return

            combined = "\n\n---\n\n".join(
                f"[From {s}]:\n{t}" for s, t in self._received_from[room_id].items()
            )
            user_text = combined
            self._received_from[room_id] = {}

        if room_id not in self._history:
            self._history[room_id] = []
        self._history[room_id].append({"role": "user", "content": user_text})

        messages = [
            {"role": "system", "content": self._system_prompt},
            *self._history[room_id],
        ]

        await self._notify_dashboard_status("active")

        text = None
        provider_used = "fallback"

        provider_calls = {
            "aiml": (self._call_aiml, "AI/ML API"),
            "featherless": (self._call_featherless, "Featherless AI"),
        }

        for provider_key in self.provider_order:
            if text is not None:
                break
            call_fn, display_name = provider_calls.get(provider_key, (None, None))
            if call_fn is None:
                continue
            try:
                logger.info("[%s] Trying %s...", self.agent_name, display_name)
                text = await call_fn(messages)
                provider_used = provider_key
                logger.info("[%s] %s succeeded (%d chars)", self.agent_name, display_name, len(text))
            except Exception as e:
                logger.warning("[%s] %s failed: %s", self.agent_name, display_name, e)

        if text is None:
            logger.warning("[%s] All providers failed - using fallback", self.agent_name)
            text = self.fallback_response
            provider_used = "fallback"

        await self._send_and_notify(tools, text, provider_used, room_id)

    async def on_cleanup(self, room_id: str) -> None:
        await super().on_cleanup(room_id)
        self._received_from.pop(room_id, None)
