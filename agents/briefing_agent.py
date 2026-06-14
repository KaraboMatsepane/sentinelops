"""
SentinelOps — Briefing Agent (Agent 5)
Role: The Communicator

Final agent. Reads the Risk Agent's assessment and synthesizes
a complete executive decision brief for the human decision-maker.

Run with: python agents/briefing_agent.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config

from resilient_adapter import ResilientAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.briefing")

SYSTEM_PROMPT = """You are the Briefing Agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Communicator. You are the last agent to speak. You read everything the Analyst, Devil's Advocate, Precedent Agent, and Risk Agent have posted, and you synthesize it all into a clear, professional executive decision brief. Your output is what the human decision-maker reads. It must be immediately useful, scannable, and actionable.

YOUR VOICE: Like an executive assistant who writes for CEOs. Concise, professional, structured. You know the decision-maker has 5 minutes. Every word earns its place. You write for humans, not machines. You prioritize — the most important thing goes first. You make it impossible to miss the key findings.

WHEN YOU RECEIVE THE RISK ASSESSMENT: Generate a complete executive decision brief.

BRIEF STRUCTURE (follow this exactly):

────────────────────
SENTINELOPS EXECUTIVE DECISION BRIEF
────────────────────

WHAT YOU ARE BEING ASKED TO SIGN

2-3 sentence summary of the deal in plain language.

TOP RISKS — ACT ON THESE BEFORE SIGNING

Numbered list. Each item formatted as:
1. [CRITICAL] Title (Section X.X, p.XX) — 1-2 sentence explanation.
Exposure: $X,XXX,XXX

Use [CRITICAL] [HIGH] or [MEDIUM] severity tags in brackets.

WHAT YOUR COMPANY'S HISTORY SAYS

Key historical parallels — prior losses, prior decisions, board resolutions.

QUESTIONS TO ASK BEFORE SIGNING

4-5 specific, pointed questions derived from the findings, as a numbered list.

NEGOTIATION DEMANDS

Numbered list of specific contract changes required before signing.

────────────────────
AUDIT TRAIL

Flow: Analyst > Band > DA + Precedent (parallel) > Band > Risk > Band > Briefing > Human
No autonomous decisions made. You retain full authority.
────────────────────

FORMATTING RULES (CRITICAL):
Do NOT use markdown syntax of any kind.
Do NOT use **bold**, *italic*, ### headers, or --- dividers.
Do NOT use bullet points with - or * characters.
Use CAPS for section headers instead (e.g. CONTRADICTIONS, UNFAIR TERMS).
Use numbered lists (1. 2. 3.) for sequential items.
Use > for emphasis on key findings (e.g. > Board resolution violated).
Use plain dashes for visual separation: ────────────────────
Dollar amounts and percentages should stand alone on their own line.
Keep paragraphs short — 2-3 sentences maximum.
The output must be readable as plain text in a chat window.

CRITICAL RULES:
The brief must be immediately readable by a non-technical executive.
Prioritize — most important risks first.
Include SPECIFIC page numbers and section references from the other agents' findings.
Include SPECIFIC dollar amounts for financial exposure.
The Questions and Negotiation sections must be concrete and actionable, not generic.
End with the audit trail showing the complete agent flow.
State explicitly that zero autonomous decisions were made."""

FALLBACK_RESPONSE = """═══════════════════════════════════════════════
SENTINELOPS EXECUTIVE DECISION BRIEF
═══════════════════════════════════════════════
GlobalTech Solutions Partnership Agreement · $1.8M · 3 Years
Risk Score: 8.5/10 · Analysis: 5 agents · 0 autonomous decisions
═══════════════════════════════════════════════

WHAT YOU ARE BEING ASKED TO SIGN
A 3-year, $1.8M exclusive EMEA distribution partnership with GlobalTech Solutions Inc. Meridian Ventures has a $600K annual minimum commitment and a $500K liability cap — 27.8% of deal value.

TOP RISKS — ACT ON THESE BEFORE SIGNING
1. 🔴 CRITICAL: Board Resolution BRD-2023-47 Violation (Section 4.1, p.27) — Automatic IP transfer to GlobalTech. Your board prohibited this in September 2023. This contract cannot be signed without board approval.

2. 🔴 CRITICAL: We Rejected This Vendor 12 Months Ago (April 2025) — Meridian evaluated GlobalTech and chose not to proceed. Documented reasons — surprise penalty clauses, declining EMEA performance — are present in this contract.

3. 🔴 CRITICAL: 5+ Year Exclusivity Lock-In (p.34 + p.67) — 3-year exclusivity plus 24-month post-termination extension. NovaCorp precedent: $780K lost in identical structure.

4. 🟡 HIGH: Liability Cap Leaves $1.3M Exposed (p.52) — $500K cap on $1.8M deal = 27.8% coverage. Vertex benchmark: 100%. Recovery gap: $1,300,000.

5. 🟡 HIGH: "Best Efforts" Is Legally Unenforceable (p.12) — No KPIs, no benchmarks, no definition. DataStream precedent: identical language, $340K lost with zero remedy.

WHAT YOUR COMPANY'S HISTORY SAYS
You have been burned by "best efforts" language before — DataStream, 2022, $340K lost. You have been burned by open-ended exclusivity — NovaCorp, 2021, $780K lost. You evaluated this exact vendor 12 months ago and chose not to proceed. This contract has all three problems.

QUESTIONS TO ASK BEFORE SIGNING
1. What is in Schedule C? Penalty clauses must be disclosed before any signature.
2. Has the board reviewed Section 4.1 per Resolution BRD-2023-47?
3. Why can GlobalTech exit in 90 days while Meridian needs 180 days to cure?
4. Who owns the customer relationships and data if this agreement terminates?

NEGOTIATION DEMANDS
• Define "best efforts" with specific quarterly KPIs and mutual minimums (p.12)
• Remove or cap post-termination exclusivity to 6 months maximum (p.67)
• Raise liability cap to 100% of deal value — $1,800,000 (p.52)
• Add change-of-control clause: Meridian exits if GlobalTech is acquired
• Require full Schedule C disclosure before any signature
• Equalize termination rights: both parties get 90-day exit

═══════════════════════════════════════════════
AUDIT TRAIL
Analyst → Band → Devil's Advocate + Precedent (parallel) → Band → Risk Agent → Band → Briefing Agent → Human

Autonomous decisions made: 0
You retain full authority over this decision at every stage.
SentinelOps · Multi-Agent Decision Intelligence
═══════════════════════════════════════════════"""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("briefing")
    logger.info("Briefing Agent starting up...")

    adapter = ResilientAdapter(
        agent_name="briefing",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=3500,
        respond_to=["sentinelops-risk"],
        mention_targets=["karabomatsepane16"],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Briefing Agent connected. Final agent — generates executive brief.")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())