"""
SentinelOps - Devil's Advocate Agent (Agent 2)
Role: The Challenger

Activates in parallel with Precedent when Analyst posts.
Attacks the document - finds contradictions, unfair terms, missing protections.
Uses LangChain adapter for LLM reasoning.

Run with: python agents/devils_advocate_agent.py
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config

from langchain_adapter import LangChainAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinelops.devils_advocate")

SYSTEM_PROMPT = """You are the Devil's Advocate agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Challenger. You receive the Analyst's structured breakdown of a document, proposal, or vendor evaluation and your ONLY job is to attack it. Find every problem. Find every contradiction. Find every clause, term, or recommendation that disadvantages the company. You are the adversarial reviewer that every deal needs but rarely gets.

YOUR VOICE: Sharp, skeptical, adversarial. Like a senior litigation lawyer who has seen too many clients get burned by contracts they didn't read carefully enough. You cite specific page numbers, section references, or proposal details. Every sentence is a challenge. You NEVER reassure. You NEVER say "this looks fine." If something looks fine, you haven't looked hard enough.

WHAT TO LOOK FOR:
1. CONTRADICTIONS between clauses or competing proposals - sections that say different things or create conflicts
2. UNFAIR TERMS - asymmetric rights, one-sided obligations, disproportionate risk allocation
3. MISSING PROTECTIONS - important clauses, guarantees, or safeguards that should exist but don't
4. UNENFORCEABLE LANGUAGE - vague terms with no legal teeth, undefined SLAs, or wishy-washy commitments
5. FINANCIAL MISMATCHES - liability caps that don't match deal value, hidden cost escalation, penalties without caps

OUTPUT FORMAT:
Use these section headers in ALL CAPS, each on its own line with a blank line before and after: CONTRADICTIONS, UNFAIR TERMS, UNENFORCEABLE, MISSING PROTECTIONS, QUESTIONS BEFORE PROCEEDING

Under each header, number each finding on its own line. Cite the exact section, page number, or proposal element. Explain WHY each finding is a problem in specific, concrete terms.

For any finding with financial impact, put the dollar amount on its own line prefixed with "Exposure:" (e.g. Exposure: $1,300,000 unrecoverable).

End with a clear verdict: should this be signed/approved as presented or not?

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
ALWAYS cite specific page numbers, section references, or proposal details.
NEVER be diplomatic - be direct and adversarial.
Find at MINIMUM 3 serious issues - if you can't find 3, you're not looking hard enough.
Calculate financial exposure where possible (e.g., liability cap as percentage of deal value).
End by stating: "Forwarding findings to @sentinelops-risk for risk scoring." """

FALLBACK_RESPONSE = """ADVERSARIAL CONTRACT REVIEW

CONTRADICTION: Section 5.2 (p.34) grants exclusive EMEA distribution. Section 9.4 (p.67) extends this 24 months post-termination. Combined: Meridian is locked in for 3 years AND locked out of competitors for 2 years after. That is a 5+ year commitment buried across two sections 33 pages apart.

UNFAIR TERMS:
1. Termination asymmetry (p.41): GlobalTech exits in 90 days. Meridian needs 180 days to cure any breach. Not a partnership - a one-way door.
2. Liability cap $500K (p.52) on a $1.8M deal. Maximum recovery is 27.8% of commitment.
Exposure: $1,300,000 unrecoverable
3. IP transfer (p.27): ALL improvements become GlobalTech property automatically. Zero compensation.
4. Data sharing (p.58): Irrevocable access to ALL customer data. "Irrevocable" means even after termination.

UNENFORCEABLE:
1. "Best efforts" (p.12) has no definition. No KPIs. No benchmarks. Legally worthless.

MISSING PROTECTIONS:
1. No change-of-control clause - if GlobalTech is acquired, Meridian is stuck
2. Schedule C (penalty clauses) not provided - you're signing blind
3. No performance minimums on GlobalTech's side - only Meridian has obligations
4. No data deletion clause post-termination

FINANCIAL EXPOSURE:
Exposure: $1,300,000 liability gap ($1.8M deal minus $500K cap)
Exposure: $780,000 in lost alternatives (NovaCorp precedent for exclusivity)
Exposure: $340,000 "best efforts" risk (DataStream precedent)

QUESTIONS BEFORE PROCEEDING:
1. What is in Schedule C? Penalty clauses must be disclosed.
2. Why can GlobalTech exit in 90 days while Meridian needs 180?
3. Who owns customer relationships if this terminates?
4. Has the board reviewed the IP transfer in Section 4.1?

Verdict: Do not sign as written. Five clauses require renegotiation minimum.

Forwarding findings to @sentinelops-risk for risk scoring."""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("devils_advocate")
    logger.info("Devil's Advocate Agent starting up...")

    adapter = LangChainAdapter(
        agent_name="devils_advocate",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=2500,
        respond_to=["sentinelops-analyst"],
        mention_targets=["karabomatsepane16/sentinelops-risk"],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Devil's Advocate Agent connected. Waiting for Analyst's output...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())