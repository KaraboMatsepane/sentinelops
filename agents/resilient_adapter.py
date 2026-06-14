"""
Multi-provider LLM adapter with automatic fallback.

Tries AI/ML API -> Featherless AI -> hardcoded response.
Posts events to the local dashboard server for live visualization.
"""

import logging
import os
import re
import time
from typing import Any, ClassVar

import httpx

from band.core.protocols import AgentToolsProtocol
from band.core.simple_adapter import SimpleAdapter
from band.core.types import (
    AdapterFeatures,
    Emit,
    Capability,
    PlatformMessage,
    HistoryProvider,
)

logger = logging.getLogger(__name__)

DASHBOARD_URL = "http://localhost:8080/api/event"

def strip_markdown(text: str) -> str:
    """
    Convert markdown to clean plain text for Band chat.
    Band renders markdown as raw characters — this keeps the room readable.
    The dashboard receives the original markdown separately for rich rendering.
    """
    # Remove markdown headers (### Header → Header)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold and italic (**text** → text, *text* → text)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)

    # Remove inline code (`code` → code)
    text = re.sub(r'`(.+?)`', r'\1', text)

    # Remove horizontal rules (--- or ═══)
    text = re.sub(r'^[-═]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Convert markdown tables to plain text rows
    # Keep the content, remove the pipe/dash table structure
    def clean_table_row(match):
        row = match.group(0)
        # Skip separator rows (|---|---|)
        if re.match(r'^\|[\s\-|:]+\|$', row.strip()):
            return ''
        # Extract cell content
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        return '  |  '.join(cells)

    text = re.sub(r'^\|.+\|$', clean_table_row, text, flags=re.MULTILINE)

    # Remove bullet list markers but keep content indented
    text = re.sub(r'^[\s]*[-*•]\s+', '  · ', text, flags=re.MULTILINE)

    # Remove numbered list markers formatting (keep numbers)
    text = re.sub(r'^(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)

    # Collapse multiple blank lines to max two
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()

class ResilientAdapter(SimpleAdapter[HistoryProvider]):
    """
    Band adapter that tries multiple LLM providers in order.
    Integrates with the local dashboard server for live visualization.

    Provider hierarchy:
    1. AI/ML API (primary — powers Analyst, DA, Risk, Briefing)
    2. Featherless AI (fallback — primary for Precedent Agent)
    3. Hardcoded fallback response

    Band chat: receives clean plain text (no markdown clutter)
    Dashboard: receives original markdown for rich formatted rendering
    """

    SUPPORTED_EMIT: ClassVar[frozenset[Emit]] = frozenset()
    SUPPORTED_CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset()

    def __init__(
            self,
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
    ):
        super().__init__(history_converter=None, features=AdapterFeatures())
        self.agent_name = agent_name
        self._system_prompt = system_prompt
        self.fallback_response = fallback_response
        self.max_tokens = max_tokens
        self.aiml_model = aiml_model
        self.featherless_model = featherless_model
        self.respond_to = respond_to
        self.wait_for_all = wait_for_all
        self.mention_targets = mention_targets
        self.trigger_phrase = trigger_phrase
        self._history: dict[str, list[dict[str, str]]] = {}
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

    async def _notify_dashboard(self, content: str, provider: str):
        """Send full markdown content to dashboard for rich rendering."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(DASHBOARD_URL, json={
                    "agent": self.agent_name,
                    "type": "message",
                    "content": content,       # full markdown — dashboard renders this
                    "provider": provider,
                    "timestamp": time.time(),
                })
                logger.info("[%s] Dashboard notified (status %d)", self.agent_name, resp.status_code)
        except Exception as e:
            logger.warning("[%s] Dashboard notification failed: %s", self.agent_name, e)

    async def _notify_dashboard_status(self, status: str):
        """Send agent status update to dashboard."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(DASHBOARD_URL, json={
                    "agent": self.agent_name,
                    "type": "status",
                    "status": status,
                    "timestamp": time.time(),
                })
                logger.debug("[%s] Status '%s' sent (status %d)", self.agent_name, status, resp.status_code)
        except Exception as e:
            logger.warning("[%s] Status notification failed: %s", self.agent_name, e)

    def _should_respond(self, msg: PlatformMessage) -> bool:
        if not self.respond_to:
            return True
        sender = (msg.sender_name or "").lower()
        sender_type = (msg.sender_type or "").lower()
        for pattern in self.respond_to:
            p = pattern.lower()
            if p in sender or p == sender_type:
                return True
        return False

    async def on_started(self, agent_name: str, agent_description: str) -> None:
        await super().on_started(agent_name, agent_description)
        logger.info("Resilient adapter started for %s", agent_name)
        await self._notify_dashboard_status("connected")

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

        try:
            logger.info("[%s] Trying AI/ML API...", self.agent_name)
            text = await self._call_aiml(messages)
            provider_used = "aiml"
            logger.info("[%s] AI/ML API succeeded (%d chars)", self.agent_name, len(text))
        except Exception as e:
            logger.warning("[%s] AI/ML API failed: %s", self.agent_name, e)

        if text is None:
            try:
                logger.info("[%s] Trying Featherless AI...", self.agent_name)
                text = await self._call_featherless(messages)
                provider_used = "featherless"
                logger.info("[%s] Featherless succeeded (%d chars)", self.agent_name, len(text))
            except Exception as e:
                logger.warning("[%s] Featherless AI failed: %s", self.agent_name, e)

        if text is None:
            logger.warning("[%s] All providers failed — using fallback", self.agent_name)
            text = self.fallback_response
            provider_used = "fallback"

        self._history[room_id].append({"role": "assistant", "content": text})

        # Send plain text to Band (readable in the chat room)
        band_text = strip_markdown(text)
        await tools.send_message(band_text, mentions=self.mention_targets)

        # Send full markdown to dashboard (rich rendering)
        await self._notify_dashboard(text, provider_used)
        await self._notify_dashboard_status("complete")

    async def on_cleanup(self, room_id: str) -> None:
        self._history.pop(room_id, None)
        self._received_from.pop(room_id, None)
