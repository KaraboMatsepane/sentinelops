"""
SentinelOps agent adapters - three LLM integration frameworks, one Band coordination layer.

Framework adapters:
    BaseAdapter          Shared dashboard integration and message filtering
    ResilientAdapter     Native httpx with multi-provider fallback (Analyst, Risk, Briefing)
    LangChainAdapter     LangChain ChatPromptTemplate | ChatOpenAI | StrOutputParser (Devil's Advocate)
    OpenAIAdapter        OpenAI AsyncOpenAI SDK (Precedent Agent)

Utilities:
    scenario_loader      Dynamic scenario data loading from JSON files
"""