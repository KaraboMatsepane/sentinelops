# SentinelOps — Multi-Agent Decision Intelligence

**Five AI agents. One coordinated team. 90 seconds to a complete intelligence brief.**

SentinelOps deploys five specialized AI agents through [Band](https://band.ai) to simultaneously analyze any major enterprise decision — finding contradictions, surfacing forgotten history, scoring risk, and delivering a complete intelligence brief to human decision-makers in under 90 seconds. Any decision, any enterprise, zero autonomous actions — humans retain full authority at every stage.

---

## The Problem

Every enterprise makes high-stakes decisions constantly — signing contracts, choosing vendors, approving budgets. Each decision carries risk: clauses that contradict each other, assumptions that are wrong, history that was forgotten. Organizations spend millions on lawyers and consultants. They often miss things anyway, because no human can read everything, remember everything, and question everything simultaneously.

## The Solution

SentinelOps attacks every major decision from five angles at once:

| # | Agent | Role | Provider |
|---|-------|------|----------|
| 1 | **Analyst** | The Mapper — extracts and structures every key element | AI/ML API |
| 2 | **Devil's Advocate** | The Challenger — finds contradictions, unfair terms, missing protections | AI/ML API |
| 3 | **Precedent** | The Historian — searches company history for relevant precedents | Featherless AI |
| 4 | **Risk** | The Scorer — synthesizes findings into a quantified risk matrix | AI/ML API |
| 5 | **Briefing** | The Communicator — produces a clear executive decision brief | AI/ML API |

## How Band Connects Everything

Band is the coordination layer that makes this a team, not five scripts.

```
Document → Analyst → [Band] → Devil's Advocate  ─┐ (parallel)
                              → Precedent Agent   ─┘
                                     ↓
                              → [Band] → Risk Agent → [Band] → Briefing Agent → Human
```

When Analyst posts its findings to Band, Devil's Advocate and Precedent Agent **both receive it simultaneously** and activate in parallel. This true parallelism is only possible because Band broadcasts messages to all listening agents at once.

## Tech Stack

- **[Band](https://band.ai)** — Agent coordination platform (core)
- **[AI/ML API](https://aimlapi.com)** — Powers Analyst, Devil's Advocate, Risk, and Briefing agents
- **[Featherless AI](https://featherless.ai)** — Powers Precedent Agent (open-source model inference)
- **Python 3.10+** — All agent scripts
- **HTML/CSS/JS** — Real-time dashboard

## Project Structure

```
sentinelops/
├── agents/
│   ├── analyst_agent.py          # Agent 1: The Mapper (AI/ML API)
│   ├── devils_advocate_agent.py  # Agent 2: The Challenger (AI/ML API)
│   ├── precedent_agent.py        # Agent 3: The Historian (Featherless AI)
│   ├── risk_agent.py             # Agent 4: The Scorer (AI/ML API)
│   ├── briefing_agent.py         # Agent 5: The Communicator (AI/ML API)
│   └── featherless_adapter.py    # Custom Band adapter for Featherless AI
├── data/
│   ├── scenario_a.json           # Demo: $1.8M partnership contract
│   ├── scenario_b_vendor.json    # Demo: Cloud vendor selection
│   └── company_history.json      # Meridian Ventures institutional memory
├── dashboard/
│   └── index.html                # Real-time analysis dashboard
├── agent_config.yaml             # Band agent credentials (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

### Prerequisites
- Python 3.10+
- Band account ([band.ai](https://band.ai))
- AI/ML API key ([aimlapi.com](https://aimlapi.com))
- Featherless AI key ([featherless.ai](https://featherless.ai))

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sentinelops.git
cd sentinelops

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys
```

### Configure Band Agents

1. Create 5 Remote Agents on [app.band.ai](https://app.band.ai)
2. Copy each agent's ID and API key into `agent_config.yaml`
3. Add all 5 agents to a shared Band room

### Run the Demo

Open 5 terminal windows, one per agent:

```bash
# Terminal 1
python agents/analyst_agent.py

# Terminal 2
python agents/devils_advocate_agent.py

# Terminal 3
python agents/precedent_agent.py

# Terminal 4
python agents/risk_agent.py

# Terminal 5
python agents/briefing_agent.py
```

In the Band room, trigger the analysis:
```
@sentinelops-analyst analyze scenario_a
```

Watch all five agents coordinate through Band in real time.

## Demo Scenarios

### Scenario A: Partnership Contract ($1.8M)
A 74-page partnership agreement between Meridian Ventures and GlobalTech Solutions. The contract contains hidden problems: contradicting exclusivity clauses, a liability cap at 27.8% of deal value, automatic IP transfer violating a board resolution, and undefined "best efforts" language that previously cost the company $340K.

### Scenario B: Vendor Selection ($420K)
Evaluation of three cloud infrastructure vendors with competing tradeoffs: cost vs reliability vs compliance certifications vs vendor lock-in risk.

## Partner Technology Usage

**SentinelOps uses AI/ML API** to power the Analyst, Devil's Advocate, Risk, and Briefing agents — handling document parsing, adversarial contract analysis, risk scoring, and executive brief generation respectively.

**The Precedent Agent runs on Featherless AI**, using open-source model inference for specialized historical document analysis and institutional memory retrieval.

**Band** is the coordination platform that enables true parallel activation — Devil's Advocate and Precedent Agent receive the Analyst's findings simultaneously and work concurrently.

## Judging Criteria Alignment

| Criteria | How SentinelOps Addresses It |
|----------|------------------------------|
| **Technology Application** | Uses Band for agent coordination, AI/ML API for 4 agents, Featherless AI for 1 agent — all three partner technologies used meaningfully |
| **Presentation** | Story-driven demo with visible parallel agent activation, professional dashboard |
| **Business Value** | Every enterprise makes decisions. SentinelOps makes them smarter, faster, and safer. Universal applicability. |
| **Originality** | Adversarial decision intelligence — five agents that challenge decisions rather than rubber-stamp them |

---

**Band of Agents Hackathon 2026** · Track 1: Internal Enterprise Workflows