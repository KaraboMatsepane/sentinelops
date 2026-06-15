"""
LangChain-based LLM adapter for Band SDK.

Uses LangChain's ChatOpenAI + ChatPromptTemplate + StrOutputParser chain pattern
instead of raw httpx calls for LLM reasoning. Demonstrates cross-framework support
in SentinelOps -- proving Band can coordinate agents built with different
LLM frameworks (raw API, LangChain, OpenAI SDK).

Default provider: AI/ML API (Claude) with Featherless AI (Qwen) fallback.
"""

import logging
import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from band.core.protocols import AgentToolsProtocol
from band.core.types import PlatformMessage

from base_adapter import BaseAdapter

logger = logging.getLogger(__name__)


class LangChainAdapter(BaseAdapter):
    """
    Band adapter that uses LangChain chains for LLM reasoning.

    Builds a ChatPromptTemplate | ChatOpenAI | StrOutputParser chain for each
    provider and invokes it asynchronously via .ainvoke(). Falls back across
    providers in order: AI/ML API -> Featherless AI -> hardcoded response.
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
        self._aiml_chain = self._build_aiml_chain()
        self._featherless_chain = self._build_featherless_chain()

    def _build_aiml_chain(self):
        api_key = os.getenv("AIML_API_KEY", "")
        base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.aimlapi.com")
        if not api_key:
            logger.warning("[%s] AIML_API_KEY not set - AI/ML chain disabled", self.agent_name)
            return None

        llm = ChatOpenAI(
            model="claude-sonnet-4-5-20250929",
            api_key=api_key,
            base_url=f"{base_url}/v1",
            max_tokens=self.max_tokens,
            temperature=0.7,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt),
            ("human", "{input}"),
        ])
        return prompt | llm | StrOutputParser()

    def _build_featherless_chain(self):
        api_key = os.getenv("FEATHERLESS_API_KEY", "")
        if not api_key:
            logger.warning("[%s] FEATHERLESS_API_KEY not set - Featherless chain disabled", self.agent_name)
            return None

        llm = ChatOpenAI(
            model="Qwen/Qwen3-30B-A3B-Instruct-2507",
            api_key=api_key,
            base_url="https://api.featherless.ai/v1",
            max_tokens=self.max_tokens,
            temperature=0.7,
        )
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._system_prompt),
            ("human", "{input}"),
        ])
        return prompt | llm | StrOutputParser()

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
            logger.info("[%s] Ignoring message from %s (not in respond_to)", self.agent_name, sender)
            return

        user_text = msg.format_for_llm()

        if room_id not in self._history:
            self._history[room_id] = []
        self._history[room_id].append({"role": "user", "content": user_text})

        await self._notify_dashboard_status("active")

        history_context = self._build_history_context(room_id)

        text = None
        provider_used = "fallback"

        if self._aiml_chain is not None:
            try:
                logger.info("[%s] Trying LangChain AI/ML API chain...", self.agent_name)
                text = await self._aiml_chain.ainvoke({"input": history_context})
                provider_used = "langchain-aiml"
                logger.info("[%s] LangChain AI/ML API succeeded (%d chars)", self.agent_name, len(text))
            except Exception as exc:
                logger.warning("[%s] LangChain AI/ML API failed: %s", self.agent_name, exc)

        if text is None and self._featherless_chain is not None:
            try:
                logger.info("[%s] Trying LangChain Featherless chain...", self.agent_name)
                text = await self._featherless_chain.ainvoke({"input": history_context})
                provider_used = "langchain-featherless"
                logger.info("[%s] LangChain Featherless succeeded (%d chars)", self.agent_name, len(text))
            except Exception as exc:
                logger.warning("[%s] LangChain Featherless failed: %s", self.agent_name, exc)

        if text is None:
            logger.warning("[%s] All LangChain providers failed - using fallback response", self.agent_name)
            text = self.fallback_response
            provider_used = "fallback"

        await self._send_and_notify(tools, text, provider_used, room_id)

    def _build_history_context(self, room_id: str) -> str:
        entries = self._history.get(room_id, [])
        if not entries:
            return ""
        if len(entries) == 1:
            return entries[0]["content"]

        parts: list[str] = []
        for entry in entries[:-1]:
            role_label = "User" if entry["role"] == "user" else "Assistant"
            parts.append(f"[{role_label}]: {entry['content']}")

        latest = entries[-1]
        parts.append(f"\n[Current message]: {latest['content']}")
        return "\n\n".join(parts)