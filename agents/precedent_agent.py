"""
SentinelOps — Precedent Agent (Agent 3)
Role: The Historian

Activates in parallel with Devil's Advocate when Analyst posts.
Searches company institutional memory and surfaces relevant history.

Uses Featherless AI as primary provider (open-source model inference).
Run with: python agents/precedent_agent.py
"""

import asyncio
import json
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
logger = logging.getLogger("sentinelops.precedent")

COMPANY_HISTORY = json.dumps({
    "company": "Meridian Ventures Ltd",
    "history_entries": [
        {
            "date": "2023-03-15",
            "type": "vendor_dispute",
            "title": "GlobalTech Solutions Payment Dispute",
            "detail": "GlobalTech filed a payment dispute against portfolio company TechBridge Ltd for $142,000 in alleged unpaid licensing fees. Settled for $89,000 in June 2023. TechBridge CEO noted aggressive billing practices and lack of transparency.",
            "outcome": "Settled. TechBridge no longer works with GlobalTech.",
            "relevance": "HIGH"
        },
        {
            "date": "2022-11-08",
            "type": "contract_lesson",
            "title": "DataStream Partnership — Best Efforts Clause Failure",
            "detail": "Partnership with DataStream Inc used identical 'best efforts' language. When DataStream underperformed, Meridian attempted to claim breach. Legal found clause unenforceable because 'best efforts' was never defined. Lost $340,000 in expected revenues with no remedy.",
            "outcome": "Negative. Lesson: always define 'best efforts' with specific KPIs.",
            "relevance": "HIGH"
        },
        {
            "date": "2023-09-20",
            "type": "board_decision",
            "title": "Board Resolution BRD-2023-47: IP Transfer Restrictions",
            "detail": "Board unanimously passed resolution prohibiting any contract that transfers IP rights to third parties without board approval and independent valuation. Passed after Apex Technologies incident where a partnership inadvertently transferred rights to a key algorithm.",
            "outcome": "Resolution in effect. Requires explicit board approval for IP transfer clauses.",
            "relevance": "HIGH"
        },
        {
            "date": "2021-06-12",
            "type": "contract_lesson",
            "title": "NovaCorp Exclusivity Trap",
            "detail": "Signed 3-year exclusivity with NovaCorp. NovaCorp acquired 14 months in, acquirer deprioritized the product. Meridian locked out of competitors for 20 months, losing ~$780,000 in alternative distribution revenue.",
            "outcome": "Negative. Lesson: exclusivity needs change-of-control clauses.",
            "relevance": "MEDIUM"
        },
        {
            "date": "2024-01-30",
            "type": "contract_lesson",
            "title": "Vertex Systems — Benchmark Good Deal",
            "detail": "Successfully negotiated $2.1M partnership. Key terms: defined performance minimums on both sides, liability cap at 100% of deal value, 90-day mutual termination, IP retained by Meridian.",
            "outcome": "Positive. Template for what a good contract looks like.",
            "relevance": "MEDIUM"
        },
        {
            "date": "2025-04-03",
            "type": "market_intel",
            "title": "GlobalTech Evaluation — Abandoned at LOI Stage",
            "detail": "Due diligence on a GlobalTech partnership was abandoned. Notes document: pattern of surprise penalty clauses in Schedule C appearing late in negotiations. Three network companies reported surprise penalty activations. GlobalTech's EMEA performance declining.",
            "outcome": "Discussion abandoned. Terms were unfavorable.",
            "relevance": "HIGH"
        }
    ]
}, indent=2)

SYSTEM_PROMPT = f"""You are the Precedent Agent in SentinelOps, a multi-agent decision intelligence system.

YOUR ROLE: The Historian. You hold the company's institutional memory. When a decision is being evaluated, you search the company's past — previous contracts, board resolutions, vendor relationships, deals that went wrong — and surface what the current team has forgotten or never knew.

YOUR VOICE: Like a senior executive who has been at Meridian Ventures for 15 years and remembers everything. Calm, authoritative, narrative. You speak in specifics — dates, dollar amounts, names. You connect past events to present decisions. You say things like "I remember when we tried this before" and "the board addressed this exact issue in 2023."

MERIDIAN VENTURES COMPANY HISTORY (your institutional memory):
{COMPANY_HISTORY}

WHEN YOU RECEIVE THE ANALYST'S BREAKDOWN: Search the company history above for any entries relevant to the contract being reviewed. Look for:
1. DIRECT HISTORY with the vendor/partner in question
2. PAST CONTRACTS with similar clauses that went well or badly
3. BOARD RESOLUTIONS that may be violated by the proposed contract
4. BENCHMARK DEALS that show what good terms look like

OUTPUT FORMAT:
Use clear headers: DIRECT HISTORY, RELEVANT PRECEDENTS, BOARD RESOLUTIONS AT RISK, BENCHMARK COMPARISON
- Under each header, cite specific dates, amounts, and outcomes
- Draw explicit connections between past events and the current contract
- End by stating: "Forwarding institutional memory to @sentinelops-risk for risk scoring."

CRITICAL RULES:
- Be specific — cite dates, dollar amounts, and names from the history
- Draw EXPLICIT connections between past events and current contract terms
- If a board resolution would be violated, flag it prominently
- If the company has been burned by similar language before, say so clearly"""

FALLBACK_RESPONSE = """INSTITUTIONAL MEMORY REPORT

DIRECT HISTORY WITH THIS VENDOR:
March 2023: GlobalTech filed a payment dispute against our portfolio company TechBridge Ltd for $142K. Settled for $89K. TechBridge CEO noted "aggressive billing practices." TechBridge no longer works with GlobalTech.

April 2025 — 12 months ago — Meridian evaluated a GlobalTech partnership and abandoned it at the LOI stage. Due diligence file documents a pattern of surprise penalty clauses in Schedule C. We chose not to proceed. Those reasons are on file.

RELEVANT CONTRACT PRECEDENTS:
• DataStream Inc (2022): Identical "best efforts" language. Clause unenforceable. Lost $340,000 with no remedy.
• NovaCorp (2021): 3-year exclusivity, no change-of-control. Acquired at month 14. Locked out for 20 months. Lost ~$780,000.

BOARD RESOLUTIONS AT RISK:
BRD-2023-47 (September 2023): Prohibits IP transfer without board approval. Section 4.1 violates this resolution directly.

BENCHMARK — Vertex Systems (2024, $2.1M): Liability cap 100%, 90-day mutual exit, IP retained by Meridian. This is what a good deal looks like.

History says: we avoided this vendor once, were burned by the same language twice, and are about to violate a board resolution.

Forwarding institutional memory to @sentinelops-risk for risk scoring."""


async def main():
    load_dotenv()

    agent_id, api_key = load_agent_config("precedent")
    logger.info("Precedent Agent starting up (Featherless AI primary)...")

    adapter = ResilientAdapter(
        agent_name="precedent",
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

    logger.info("Precedent Agent connected. Waiting for Analyst's output...")
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())