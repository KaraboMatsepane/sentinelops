"""
Shared base adapter for all SentinelOps Band agents.

Provides dashboard integration, message filtering, and lifecycle hooks
that are common across all three LLM integration frameworks (httpx,
LangChain, OpenAI SDK).
"""

import logging
import os
import re
import time
from typing import Any, ClassVar

import httpx

from band.core.simple_adapter import SimpleAdapter
from band.core.types import (
    AdapterFeatures,
    Emit,
    Capability,
    PlatformMessage,
    HistoryProvider,
)

logger = logging.getLogger(__name__)

if os.environ.get("SENTINELOPS_CLEAN"):
    for _noisy in ("httpx", "band", "phoenix_channels", "langchain", "openai"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)

DASHBOARD_URL = "http://localhost:8080/api/event"


def strip_markdown(text: str) -> str:
    """
    Convert markdown to clean plain text for Band chat.
    Band renders markdown as raw characters -- this keeps the room readable.
    The dashboard receives the original markdown separately for rich rendering.
    """
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^[-=]{3,}\s*$', '', text, flags=re.MULTILINE)

    def clean_table_row(match: re.Match) -> str:
        row = match.group(0)
        if re.match(r'^\|[\s\-|:]+\|$', row.strip()):
            return ''
        cells = [c.strip() for c in row.strip().strip('|').split('|')]
        return '  |  '.join(cells)

    text = re.sub(r'^\|.+\|$', clean_table_row, text, flags=re.MULTILINE)
    text = re.sub(r'^[\s]*[-*•]\s+', '  · ', text, flags=re.MULTILINE)
    text = re.sub(r'^(\d+)\.\s+', r'\1. ', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


class BaseAdapter(SimpleAdapter[HistoryProvider]):
    """
    Foundation adapter for SentinelOps agents.

    Handles dashboard event posting, message filtering by sender,
    conversation history management, and agent lifecycle hooks.
    Subclasses implement LLM-specific call logic.
    """

    SUPPORTED_EMIT: ClassVar[frozenset[Emit]] = frozenset()
    SUPPORTED_CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset()

    def __init__(
        self,
        *,
        agent_name: str,
        fallback_response: str,
        max_tokens: int = 2500,
        respond_to: list[str] | None = None,
        mention_targets: list[str] | None = None,
    ):
        super().__init__(history_converter=None, features=AdapterFeatures())
        self.agent_name = agent_name
        self.fallback_response = fallback_response
        self.max_tokens = max_tokens
        self.respond_to = respond_to
        self.mention_targets = mention_targets
        self._history: dict[str, list[dict[str, str]]] = {}

    # -- Dashboard notifications ------------------------------------------

    async def _notify_dashboard(self, content: str, provider: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(DASHBOARD_URL, json={
                    "agent": self.agent_name,
                    "type": "message",
                    "content": content,
                    "provider": provider,
                    "timestamp": time.time(),
                })
        except Exception as e:
            logger.warning("[%s] Dashboard notification failed: %s", self.agent_name, e)

    async def _notify_dashboard_status(self, status: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(DASHBOARD_URL, json={
                    "agent": self.agent_name,
                    "type": "status",
                    "status": status,
                    "timestamp": time.time(),
                })
        except Exception as e:
            logger.warning("[%s] Status notification failed: %s", self.agent_name, e)

    # -- Message filtering ------------------------------------------------

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

    # -- Lifecycle --------------------------------------------------------

    async def on_started(self, agent_name: str, agent_description: str) -> None:
        await super().on_started(agent_name, agent_description)
        logger.info("%s adapter started for %s", type(self).__name__, agent_name)
        await self._notify_dashboard_status("connected")

    async def on_cleanup(self, room_id: str) -> None:
        self._history.pop(room_id, None)

    # -- Helpers ----------------------------------------------------------

    async def _send_and_notify(
        self,
        tools: Any,
        text: str,
        provider: str,
        room_id: str,
    ) -> None:
        """Send plain text to Band and markdown to dashboard, then mark complete."""
        self._history[room_id].append({"role": "assistant", "content": text})
        band_text = strip_markdown(text)
        try:
            await tools.send_message(band_text, mentions=self.mention_targets)
        except Exception as e:
            logger.warning("[%s] Band send failed: %s", self.agent_name, e)
        await self._notify_dashboard(text, provider)
        await self._notify_dashboard_status("complete")
