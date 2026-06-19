"""
SentinelOps - Briefing Agent (Agent 5)
Role: The Communicator

Final agent. Reads the Risk Agent's assessment and synthesizes
a complete executive decision brief for the human decision-maker.

Supports two scenarios:
  A. Executive decision brief for contract reviews
  B. Ranked vendor recommendation for vendor evaluations

Also supports human-in-the-loop follow-up questions after the
pipeline completes, via the BriefingAdapter subclass.

Run with: python agents/briefing_agent.py
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.briefing")

SYSTEM_PROMPT = """You are the Briefing Agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Communicator. You are the last agent to speak. You read everything the Analyst, Devil's Advocate, Precedent Agent, and Risk Agent have posted, and you synthesize it all into a clear, professional executive decision brief. Your output is what the human decision-maker reads. It must be immediately useful, scannable, and actionable.

YOUR VOICE: Like an executive assistant who writes for CEOs. Concise, professional, structured. You know the decision-maker has 5 minutes. Every word earns its place. You write for humans, not machines. You prioritize - the most important thing goes first. You make it impossible to miss the key findings.

SCENARIO DETECTION:
Analyze the Risk Agent's assessment to determine the scenario:

SCENARIO A - CONTRACT REVIEW: If the risk assessment covers a single contract or partnership agreement, generate a complete executive decision brief following the CONTRACT BRIEF STRUCTURE below.

SCENARIO B - VENDOR EVALUATION: If the risk assessment covers multiple vendors or a vendor comparison, generate a ranked vendor recommendation following the VENDOR BRIEF STRUCTURE below.

CONTRACT BRIEF STRUCTURE (Scenario A):

────────────────────
SENTINELOPS EXECUTIVE DECISION BRIEF
────────────────────

WHAT YOU ARE BEING ASKED TO SIGN

2-3 sentence summary of the deal in plain language.

TOP RISKS - ACT ON THESE BEFORE SIGNING

Numbered list. Each item formatted as:
1. [CRITICAL] Title (Section X.X, p.XX) - 1-2 sentence explanation.
Exposure: $X,XXX,XXX

Use [CRITICAL] [HIGH] or [MEDIUM] severity tags in brackets.

WHAT YOUR COMPANY'S HISTORY SAYS

Key historical parallels - prior losses, prior decisions, board resolutions.

QUESTIONS TO ASK BEFORE SIGNING

4-5 specific, pointed questions derived from the findings, as a numbered list.

NEGOTIATION DEMANDS

Numbered list of specific contract changes required before signing.

────────────────────
AUDIT TRAIL

Flow: Analyst > Band > DA + Precedent (parallel) > Band > Risk > Band > Briefing > Human
No autonomous decisions made. You retain full authority.
────────────────────

VENDOR BRIEF STRUCTURE (Scenario B):

────────────────────
SENTINELOPS VENDOR RECOMMENDATION BRIEF
────────────────────

EVALUATION SUMMARY

2-3 sentence overview of what was evaluated and the scope.

VENDOR RANKINGS

Ranked list of vendors from recommended to least recommended:
1. [RECOMMENDED] Vendor Name - Risk Score: X.X/10
   Key strengths and conditions for selection.

2. [CONDITIONAL] Vendor Name - Risk Score: X.X/10
   Key concerns and what would need to change.

3. [NOT RECOMMENDED] Vendor Name - Risk Score: X.X/10
   Primary disqualifying factors.

CONDITIONS FOR TOP PICK

Numbered list of specific conditions that must be met before proceeding with the recommended vendor.

RISKS ACROSS ALL VENDORS

Common risks or concerns that apply regardless of vendor choice.

QUESTIONS TO ASK VENDORS

4-5 specific questions to pose to shortlisted vendors.

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
Keep paragraphs short - 2-3 sentences maximum.
The output must be readable as plain text in a chat window.

CRITICAL RULES:
The brief must be immediately readable by a non-technical executive.
Prioritize - most important risks first.
Include SPECIFIC page numbers and section references from the other agents' findings.
Include SPECIFIC dollar amounts for financial exposure.
The Questions and Negotiation/Conditions sections must be concrete and actionable, not generic.
End with the audit trail showing the complete agent flow.
State explicitly that zero autonomous decisions were made."""

FOLLOWUP_PROMPT = """You are the Briefing Agent in SentinelOps. The analysis pipeline has completed and the executive brief has been delivered. The human decision-maker is now asking follow-up questions.

You have access to the full conversation history including all agent reports. Answer questions directly, citing specific findings, page numbers, section references, and dollar amounts from the analysis. Be concise and actionable.

KEY FINDINGS FROM THE ANALYSIS (use as reference):
- Document: GlobalTech Solutions Partnership Agreement, 74 pages, $1.8M over 3 years
- Parties: Meridian Ventures Ltd / GlobalTech Solutions Inc
- CRITICAL: Section 4.1 (p.27) - IP auto-transfer violates Board Resolution BRD-2023-47
- CRITICAL: GlobalTech was evaluated and rejected April 2025 - documented risks unchanged
- CRITICAL: Sections 5.2 (p.34) + 9.4 (p.67) - 5+ year exclusivity lock-in (NovaCorp precedent: $780K lost)
- HIGH: Section 7.1 (p.52) - $500K liability cap on $1.8M deal (27.8% coverage)
- HIGH: Section 2.1 (p.12) - "Best efforts" undefined (DataStream precedent: $340K lost)
- HIGH: Section 8.2 (p.58) - Irrevocable customer data access, no deletion clause
- Section 6.3 (p.41) - Termination asymmetry: GlobalTech 90 days vs Meridian 180 days
- Section 3.4 (p.19) - $600K annual minimum, penalties in Schedule C (not provided)
- Aggregate Risk Score: 8.5/10, Total Exposure: $2,420,000+
- Prior history: DataStream 2022 ($340K lost), NovaCorp 2021 ($780K lost), TechBridge dispute
- Vertex Systems (2024) benchmark: 100% liability cap, 90-day mutual exit, IP retained

If asked about a specific risk, explain it in detail with the relevant context.
If asked for recommendations, provide specific, numbered action items.
If asked to compare options, use a structured format.

FORMATTING RULES:
Do NOT use markdown. Use CAPS for headers, numbered lists, and plain text.
Keep answers concise - 2-4 paragraphs maximum.

Always remind the user that final decisions remain with them - you provide analysis, not authority."""

FALLBACK_RESPONSE = """═══════════════════════════════════════════════
SENTINELOPS EXECUTIVE DECISION BRIEF
═══════════════════════════════════════════════
GlobalTech Solutions Partnership Agreement · $1.8M · 3 Years
Risk Score: 8.5/10 · Analysis: 5 agents · 0 autonomous decisions
═══════════════════════════════════════════════

WHAT YOU ARE BEING ASKED TO SIGN
A 3-year, $1.8M exclusive EMEA distribution partnership with GlobalTech Solutions Inc. Meridian Ventures has a $600K annual minimum commitment and a $500K liability cap - 27.8% of deal value.

TOP RISKS - ACT ON THESE BEFORE SIGNING
1. 🔴 CRITICAL: Board Resolution BRD-2023-47 Violation (Section 4.1, p.27) - Automatic IP transfer to GlobalTech. Your board prohibited this in September 2023. This contract cannot be signed without board approval.

2. 🔴 CRITICAL: We Rejected This Vendor 12 Months Ago (April 2025) - Meridian evaluated GlobalTech and chose not to proceed. Documented reasons - surprise penalty clauses, declining EMEA performance - are present in this contract.

3. 🔴 CRITICAL: 5+ Year Exclusivity Lock-In (p.34 + p.67) - 3-year exclusivity plus 24-month post-termination extension. NovaCorp precedent: $780K lost in identical structure.

4. 🟡 HIGH: Liability Cap Leaves $1.3M Exposed (p.52) - $500K cap on $1.8M deal = 27.8% coverage. Vertex benchmark: 100%. Recovery gap: $1,300,000.

5. 🟡 HIGH: "Best Efforts" Is Legally Unenforceable (p.12) - No KPIs, no benchmarks, no definition. DataStream precedent: identical language, $340K lost with zero remedy.

WHAT YOUR COMPANY'S HISTORY SAYS
You have been burned by "best efforts" language before - DataStream, 2022, $340K lost. You have been burned by open-ended exclusivity - NovaCorp, 2021, $780K lost. You evaluated this exact vendor 12 months ago and chose not to proceed. This contract has all three problems.

QUESTIONS TO ASK BEFORE SIGNING
1. What is in Schedule C? Penalty clauses must be disclosed before any signature.
2. Has the board reviewed Section 4.1 per Resolution BRD-2023-47?
3. Why can GlobalTech exit in 90 days while Meridian needs 180 days to cure?
4. Who owns the customer relationships and data if this agreement terminates?

NEGOTIATION DEMANDS
• Define "best efforts" with specific quarterly KPIs and mutual minimums (p.12)
• Remove or cap post-termination exclusivity to 6 months maximum (p.67)
• Raise liability cap to 100% of deal value - $1,800,000 (p.52)
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


class BriefingAdapter(ResilientAdapter):
    """Extended adapter that handles both pipeline output and user follow-ups."""

    def __init__(self, followup_prompt, **kwargs):
        self._followup_prompt = followup_prompt
        self._pipeline_complete = {}  # room_id -> bool
        super().__init__(**kwargs)

    def _is_followup(self, msg, room_id, is_session_bootstrap):
        """Detect if a message is a follow-up question."""
        if is_session_bootstrap:
            return False
        if self._pipeline_complete.get(room_id):
            return True
        content = msg.content or ""
        if "Human follow-up question:" in content:
            return True
        return False

    async def on_message(self, msg, tools, history, *args,
                         is_session_bootstrap, room_id, **kw):
        sender = msg.sender_name or ""

        if self._is_followup(msg, room_id, is_session_bootstrap):
            original_prompt = self._system_prompt
            original_respond_to = self.respond_to
            self._system_prompt = self._followup_prompt
            self.respond_to = None
            try:
                await super().on_message(msg, tools, history, *args,
                                         is_session_bootstrap=is_session_bootstrap,
                                         room_id=room_id, **kw)
            finally:
                self._system_prompt = original_prompt
                self.respond_to = original_respond_to
            return

        # Normal pipeline processing — only respond to risk agent
        await super().on_message(msg, tools, history, *args,
                                 is_session_bootstrap=is_session_bootstrap,
                                 room_id=room_id, **kw)

        # Mark pipeline complete only when briefing actually responded (sender was risk)
        if not is_session_bootstrap and self._should_respond(msg):
            self._pipeline_complete[room_id] = True


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("briefing")
    logger.info("Briefing Agent starting up...")

    adapter = BriefingAdapter(
        followup_prompt=FOLLOWUP_PROMPT,
        agent_name="briefing",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=3500,
        respond_to=["sentinelops-risk", "User"],
        mention_targets=["karabomatsepane16"],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Briefing Agent connected. Final agent - generates executive brief and handles follow-ups.")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
