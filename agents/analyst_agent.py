"""
SentinelOps - Analyst Agent (Agent 1)
Role: The Mapper

Receives the input document, maps everything into structured data,
and posts to Band - triggering Devil's Advocate and Precedent simultaneously.

Scenario data is loaded dynamically from JSON files via the scenario_loader
module. The agent detects which scenario (A or B) is being requested from
the incoming message and injects the corresponding data into the system
prompt before calling the LLM.

Run with: python agents/analyst_agent.py
"""

import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config
from band.core.protocols import AgentToolsProtocol
from band.core.types import PlatformMessage

from resilient_adapter import ResilientAdapter
from base_adapter import strip_markdown  # noqa: F401
from scenario_loader import load_scenario, detect_scenario, format_scenario_for_prompt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.analyst")

# ---------------------------------------------------------------------------
# System prompt template - scenario data is injected at runtime via
# the {scenario_data} placeholder.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT_TEMPLATE = """You are the Analyst agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Mapper. You receive enterprise decision documents and extract ALL critical information into a structured breakdown. You do NOT evaluate or judge the merits - you map every key element thoroughly and precisely so other agents can analyze it.

YOUR VOICE: Precise, neutral, clinical. Like a senior analyst preparing a comprehensive briefing book for a board meeting. You are thorough and miss nothing.

WHEN YOU RECEIVE A MESSAGE asking you to analyze a document, produce a structured breakdown of the document below. Extract: all parties, financial terms, key clauses with exact page/section references, commitments, deadlines, and anything that a reviewer should examine closely.

THE DOCUMENT TO ANALYZE:
{scenario_data}

OUTPUT FORMAT: Use clear headers and bullet points. Include exact section numbers and page references for every clause. End your analysis by stating: "Forwarding to @sentinelops-devils-advocate and @sentinelops-precedent for parallel review."

CRITICAL RULES:
- Extract EVERY section - do not skip any clause
- Always cite the exact page number and section number
- Flag any terms that seem one-sided or unusual (but do not evaluate them - just note them)
- Be complete - the other agents depend on your thoroughness
- Keep your output focused and structured, not narrative"""

# ---------------------------------------------------------------------------
# Fallback response for Scenario A - used when all LLM providers fail.
# ---------------------------------------------------------------------------
FALLBACK_RESPONSE = """STRUCTURED CONTRACT BREAKDOWN

Document: GlobalTech Solutions Partnership Agreement (74 pages)
Parties: Meridian Ventures Ltd <-> GlobalTech Solutions Inc
Value: $1,800,000 over 3 years | Annual minimum: $600,000

Key Clauses Extracted:
 - Section 1.2 (p.8): 35% revenue share on all EMEA/APAC distribution
 - Section 2.1 (p.12): "Best efforts" commitment - undefined, no KPIs
 - Section 3.4 (p.19): $600K annual minimum purchase, penalties in Schedule C
 - Section 4.1 (p.27): All IP improvements transfer to GlobalTech automatically
 - Section 5.2 (p.34): Exclusive EMEA distribution rights
 - Section 6.3 (p.41): GlobalTech exits in 90 days; Meridian needs 180-day cure
 - Section 7.1 (p.52): $500K liability cap on $1.8M deal
 - Section 8.2 (p.58): Irrevocable customer data access to GlobalTech
 - Section 9.4 (p.67): 24-month post-termination non-compete
 - Section 10.1 (p.71): Binding arbitration in Delaware, class action waiver

Key Financial Terms:
 - Total deal value: $1,800,000
 - Annual minimum commitment: $600,000
 - Revenue share: 35% to GlobalTech
 - Liability cap: $500,000 (27.8% of deal value)
 - Penalty schedule: Referenced in Schedule C but NOT provided

Flagged for Review:
 - "Best efforts" (Section 2.1) is undefined - no KPIs, no benchmarks
 - IP auto-transfer (Section 4.1) - one-sided, no compensation
 - Termination asymmetry (Section 6.3) - GlobalTech 90 days vs Meridian 180 days
 - Liability cap (Section 7.1) - significantly below deal value
 - Non-compete survives termination by 24 months (Section 9.4)

Analysis complete. Forwarding to @sentinelops-devils-advocate and @sentinelops-precedent for parallel review."""


# ---------------------------------------------------------------------------
# AnalystAdapter - extends ResilientAdapter to inject scenario data
# into the system prompt dynamically based on the incoming message.
# ---------------------------------------------------------------------------
class AnalystAdapter(ResilientAdapter):
    """
    A thin extension of ResilientAdapter that detects which scenario the
    user is asking about (A or B), loads the corresponding JSON data, and
    populates the system prompt template before the LLM call proceeds.
    """

    def __init__(self, *, prompt_template: str, **kwargs):
        default_scenario = load_scenario("a")
        initial_prompt = prompt_template.format(
            scenario_data=format_scenario_for_prompt(default_scenario)
        )
        super().__init__(system_prompt=initial_prompt, **kwargs)
        self._prompt_template = prompt_template

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
        # Detect which scenario the incoming message refers to.
        user_text = msg.format_for_llm()
        scenario_id = detect_scenario(user_text)
        logger.info(
            "[analyst] Detected scenario %s from incoming message",
            scenario_id.upper(),
        )

        # Load the scenario data and rebuild the system prompt.
        scenario = load_scenario(scenario_id)
        self._system_prompt = self._prompt_template.format(
            scenario_data=format_scenario_for_prompt(scenario)
        )

        # Delegate to the parent adapter for LLM call, fallback, and
        # dashboard notification.
        await super().on_message(
            msg,
            tools,
            history,
            participants_msg,
            contacts_msg,
            is_session_bootstrap=is_session_bootstrap,
            room_id=room_id,
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("analyst")
    logger.info("Analyst Agent starting up...")

    adapter = AnalystAdapter(
        prompt_template=SYSTEM_PROMPT_TEMPLATE,
        agent_name="analyst",
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=2500,
        respond_to=["User"],
        trigger_phrase="Analyze",
        mention_targets=[
            "karabomatsepane16/sentinelops-devils-advoc",
            "karabomatsepane16/sentinelops-precedent",
        ],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Analyst Agent connected to Band. Waiting for trigger...")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
