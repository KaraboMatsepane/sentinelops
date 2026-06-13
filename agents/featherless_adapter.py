"""
Custom Band adapter for Featherless AI (OpenAI-compatible API).

Used by the Precedent Agent to demonstrate meaningful use of Featherless AI
as a second LLM provider alongside AI/ML API.
"""

import logging
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

FEATHERLESS_BASE_URL = "https://api.featherless.ai/v1"


class FeatherlessAdapter(SimpleAdapter[HistoryProvider]):
    """
    Featherless AI adapter using OpenAI-compatible chat completions API.
    Sends messages to Featherless, posts responses back to Band.
    """

    SUPPORTED_EMIT: ClassVar[frozenset[Emit]] = frozenset()
    SUPPORTED_CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset()

    def __init__(
        self,
        model: str,
        system_prompt: str,
        api_key: str,
        max_tokens: int = 2000,
        base_url: str = FEATHERLESS_BASE_URL,
    ):
        super().__init__(history_converter=None, features=AdapterFeatures())
        self.model = model
        self._system_prompt = system_prompt
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.base_url = base_url
        self._history: dict[str, list[dict[str, str]]] = {}

    async def on_started(self, agent_name: str, agent_description: str) -> None:
        await super().on_started(agent_name, agent_description)
        logger.info("Featherless adapter started for agent: %s (model: %s)", agent_name, self.model)

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
        user_text = msg.format_for_llm()
        logger.info("Room %s: Received message from %s", room_id, msg.sender_name)

        if room_id not in self._history:
            self._history[room_id] = []

        self._history[room_id].append({"role": "user", "content": user_text})

        messages = [
            {"role": "system", "content": self._system_prompt},
            *self._history[room_id],
        ]

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": self.max_tokens,
                        "temperature": 0.7,
                    },
                )
                resp.raise_for_status()
                data = resp.json()

            text = data["choices"][0]["message"]["content"]
            logger.info("Room %s: Featherless returned %d chars", room_id, len(text))

        except Exception as e:
            logger.error("Featherless API call failed: %s", e, exc_info=True)
            text = f"[Precedent Agent error: Featherless API call failed — {e}]"

        self._history[room_id].append({"role": "assistant", "content": text})

        await tools.send_message(text)

    async def on_cleanup(self, room_id: str) -> None:
        if room_id in self._history:
            del self._history[room_id]
            logger.debug("Room %s: Cleaned up Featherless history", room_id)
