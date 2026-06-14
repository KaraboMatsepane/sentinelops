"""
SentinelOps — Risk Agent (Agent 4)
Role: The Scorer

Waits for BOTH Devil's Advocate AND Precedent reports through Band.
Scores each risk by severity and financial exposure.

Run with: python agents/risk_agent.py
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
logger = logging.getLogger("sentinelops.risk")

SYSTEM_PROMPT = """You are the Risk Agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Scorer. You receive findings from the Devil's Advocate and Precedent Agent and synthesize them into a formal risk assessment matrix. You score each risk by severity and calculate financial exposure where possible. You do NOT make subjective recommendations — you frame the objective risk landscape so the decision-maker knows exactly what they're facing.

YOUR VOICE: Measured, data-driven, precise. Like a Chief Risk Officer presenting to the board. No drama, no emotion — just numbers, severity ratings, and exposure calculations. You use structured formats and quantify everything possible.

You are receiving the combined findings from BOTH the Devil's Advocate and the Precedent Agent. Synthesize both into a single risk matrix.

DEAL CONTEXT FOR CALCULATIONS:
- Deal value: $1,800,000 over 3 years
- Annual minimum commitment: $600,000
- Stated liability cap: $500,000

OUTPUT FORMAT:
Produce a RISK ASSESSMENT MATRIX with these severity levels:
- 🔴 CRITICAL: Issues that could invalidate the deal, create legal liability, or cause catastrophic loss
- 🟡 HIGH: Issues that create significant financial exposure or operational risk
- 🟢 MEDIUM: Issues that are concerning but manageable with negotiation

For each risk item:
1. Severity rating with emoji
2. One-line title with page/section reference
3. What the risk is (1-2 sentences)
4. Quantified exposure where calculable

End with:
- AGGREGATE RISK SCORE (out of 10)
- Total quantifiable exposure
- NON-NEGOTIABLE items that must be resolved before signing
- State: "Forwarding risk assessment to @sentinelops-briefing for executive brief."

CRITICAL RULES:
- ALWAYS quantify financial exposure where possible
- Compare liability cap to deal value as a percentage
- Reference prior company losses from Precedent Agent as evidence
- Score conservatively — err on the side of flagging risk
- Distinguish between risks from Devil's Advocate (contract analysis) and Precedent (historical pattern)"""

FALLBACK_RESPONSE = """RISK ASSESSMENT MATRIX
Synthesized from Devil's Advocate + Precedent Agent findings

🔴 CRITICAL — Board Resolution Violation (Section 4.1, p.27)
IP auto-transfer triggers BRD-2023-47. Deal invalidation + legal liability.
Exposure: Contract voidability

🔴 CRITICAL — Prior Vendor Rejection on File (April 2025)
Evaluated and rejected GlobalTech 12 months ago. Documented risks unchanged.
Exposure: Repeated pattern of unfavorable terms

🔴 CRITICAL — Exclusivity Lock-In (p.34 + p.67)
3-year term + 24-month post-termination = 5+ years restricted.
Exposure: ~$780,000 (NovaCorp precedent)

🟡 HIGH — Inadequate Liability Cap (p.52)
$500K cap on $1.8M deal = 27.8% coverage. Vertex benchmark: 100%.
Exposure: $1,300,000 unrecoverable

🟡 HIGH — Unenforceable "Best Efforts" (p.12)
Undefined commitment. DataStream precedent: $340K lost.
Exposure: $340,000+

🟡 HIGH — Irrevocable Data Access (p.58)
Customer data access survives termination. No deletion clause.
Exposure: Competitive intelligence loss, regulatory risk

AGGREGATE RISK SCORE: 8.5 / 10
Total quantifiable exposure: $2,420,000+

NON-NEGOTIABLE BEFORE SIGNING:
1. Board approval for Section 4.1 IP transfer (BRD-2023-47)
2. Full Schedule C disclosure
3. Equalize termination rights
4. Define "best efforts" with KPIs
5. Cap or remove post-termination non-compete

Forwarding risk assessment to @sentinelops-briefing for executive brief."""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("risk")
    logger.info("Risk Agent starting up...")

    adapter = ResilientAdapter(
        agent_name="risk",
        system_prompt=SYSTEM_PROMPT,
        fallback_response=FALLBACK_RESPONSE,
        max_tokens=2500,
        respond_to=["sentinelops-devils", "sentinelops-precedent"],
        wait_for_all=["sentinelops-devils-advocate", "sentinelops-precedent"],
        mention_targets=["karabomatsepane16/sentinelops-briefing"],
    )

    agent = Agent.create(
        adapter=adapter,
        agent_id=agent_id,
        api_key=api_key,
        ws_url=os.getenv("THENVOI_WS_URL"),
        rest_url=os.getenv("THENVOI_REST_URL"),
    )

    logger.info("Risk Agent connected. Waits for both DA and Precedent to complete...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())