# Solutions Engineer Toolkit

**A suite of AI-powered tools that empowers Solutions Engineers to deliver results no human SE can achieve alone — built on the agentic AI stack that Google, NVIDIA, and OpenAI deploy in production.**

---

## The Problem It Solves

A senior Solutions Engineer juggles five distinct workflows in every enterprise deal:

| Workflow | Without AI | With This Toolkit |
|----------|-----------|------------------|
| Account research before a meeting | 2–3 hours manually | 60 seconds with RAG |
| Discovery session quality | Depends on SE's experience | Adaptive AI-guided questioning |
| RFP analysis | 3–6 hours reading + extracting | Under 90 seconds |
| Architecture recommendation | Senior SE + 2-day whiteboard session | Multi-agent crew in minutes |
| Proposal writing | 4–8 hours drafting | LangChain prompt chain, 5 sections |

**This toolkit does not replace the SE. It removes the low-value work so the SE can focus on what only humans can do: build trust, navigate politics, and close.**

---

## Tech Stack

Each module demonstrates a different framework from the enterprise agentic AI stack:

| Module | Framework | Why This Framework |
|--------|-----------|-------------------|
| Account Intelligence | **RAG + ChromaDB** | Retrieval-augmented generation grounds analysis in industry knowledge — no hallucination |
| Discovery Agent | **LangGraph** | Stateful multi-turn conversation with adaptive branching — the graph persists session context |
| RFP Analyzer | **OpenAI Agents SDK** | Native tool use with function calling — the agent orchestrates 3 specialized tools sequentially |
| Solution Architect | **CrewAI** | Multi-agent crew (Researcher → Architect → Reviewer) with role-based specialization |
| Proposal Writer | **LangChain** | Prompt chaining with output parsers — each section builds on context from the previous |

---

## Architecture

```
                        Solutions Engineer
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Account    │  │  Discovery   │  │     RFP      │
    │ Intelligence │  │    Agent     │  │   Analyzer   │
    │              │  │              │  │              │
    │ RAG +        │  │  LangGraph   │  │ OpenAI       │
    │ ChromaDB     │  │  stateful    │  │ Agents SDK   │
    │ vector store │  │  graph       │  │ + tool use   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                  │
           └─────────────────┼──────────────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │    Solution      │
                   │    Architect     │
                   │                  │
                   │  CrewAI crew:    │
                   │  Researcher      │
                   │  → Architect     │
                   │  → Reviewer      │
                   └────────┬─────────┘
                            │
                            ▼
                   ┌──────────────────┐
                   │    Proposal      │
                   │     Writer       │
                   │                  │
                   │  LangChain       │
                   │  prompt chain    │
                   │  5 sections      │
                   └────────┬─────────┘
                            │
                            ▼
              Customer-ready proposal (Markdown)
```

---

## Quick Start

```bash
git clone https://github.com/fabricioartur/solutions-engineer-toolkit.git
cd solutions-engineer-toolkit
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # add your OPENAI_API_KEY
```

---

## Module 1 — Account Intelligence
### RAG + ChromaDB + OpenAI

Researches a company and generates a structured pre-meeting brief enriched with industry knowledge from a local vector store.

```bash
python main.py account-intel "Meridian Bank" \
  --industry "Financial Services" \
  --output output/account.json
```

**Output:** Account brief with company overview, top AI opportunities ranked by ROI, key stakeholders with engagement tips, recommended opening questions, and known objections.

**How RAG works here:** A ChromaDB collection is seeded with industry knowledge documents (`knowledge_base/`). Before calling the LLM, the agent retrieves the 3 most relevant documents for the company + industry query. The retrieved context is injected into the prompt — grounding the analysis in real industry patterns rather than generic LLM output.

**Sample output — Meridian Bank:**

| AI Opportunity | Business Impact | Complexity | Time to Value |
|----------------|----------------|------------|---------------|
| KYC Document Intelligence | Save 900+ analyst hours/month — R$4.2M/year | Medium | 10-14 weeks |
| WhatsApp Virtual Assistant | 50-60% call deflection — R$8.1M/year savings | Medium | 12-16 weeks |
| Regulatory Reporting (BACEN) | 3 weeks → 3 days per quarter | High | 20-26 weeks |
| Credit Risk Enhancement | Reduce NPL rate by 1.2-1.8pp — R$12M/year | High | 24-32 weeks |
| SME Financial Advisory AI | +18% product attachment rate — R$5.6M/year | Medium | 16-20 weeks |

---

## Module 2 — Discovery Agent
### LangGraph stateful multi-turn conversation

Conducts an AI-powered discovery session. The agent adapts its questions based on previous answers, tracks which dimensions have been covered, and stops when it has sufficient depth to generate a structured summary.

```bash
python main.py discovery \
  --context "Brazilian bank, 50k employees, evaluating AI for customer service" \
  --output output/discovery.json
```

**How LangGraph works here:** The conversation is modeled as a graph with two nodes — `se_agent` (LLM call) and `human_input` (terminal input). State persists across turns: the agent knows which of 7 discovery dimensions it has covered and uses that to decide the next question. When coverage is sufficient, the graph transitions to `END` and outputs a structured JSON summary.

```
DiscoveryState
├── messages: list[BaseMessage]     ← full conversation history
├── dimensions_covered: int         ← tracks discovery progress
└── complete: bool                  ← graph termination signal

Graph:
  START → se_agent → (complete?) → END
                   ↘ human_input → se_agent
```

**Sample output — Meridian Bank:**

```json
{
  "discovery_quality_score": 81,
  "summary": "Strong opportunity with CDO sponsorship and R$15M pre-approved budget...",
  "gaps": [
    "KYC document quality not assessed",
    "WhatsApp intent breakdown not confirmed",
    "IT security approval timeline unknown"
  ],
  "recommended_next_questions": [
    "Can you share anonymized KYC samples for POC scoping?",
    "What are the top 5 WhatsApp intents by volume?"
  ]
}
```

---

## Module 3 — RFP Analyzer
### OpenAI Agents SDK with function calling

Analyzes procurement documents using the OpenAI Responses API with native tool use. The agent orchestrates three specialized tools in sequence — without the caller managing the loop.

```bash
python main.py rfp-analyze input/rfp.pdf \
  --output output/rfp_analysis.json
```

**How tool use works here:** Three tools are registered: `extract_requirements`, `identify_risks`, and `generate_go_no_go`. The agent decides the order and parameters. The Responses API returns `tool_calls` outputs; the client executes them and feeds results back. The loop continues until the agent produces a final JSON summary.

```
Agent loop:
  1. extract_requirements(document_text) → requirements[]
  2. identify_risks(document_text) → risks[]
  3. generate_go_no_go(requirements, risks) → recommendation
  4. Final response: complete structured analysis
```

**Output includes:**
- Requirements matrix (Technical, Commercial, Security, Legal, Compliance)
- Risk register with probability, impact, and mitigation
- GO / CONDITIONAL GO / NO-GO recommendation with rationale
- Clarification questions for the customer

---

## Module 4 — Solution Architect
### CrewAI multi-agent crew

Three specialized agents collaborate sequentially to produce a validated architecture recommendation. Each agent has a distinct role, backstory, and goal — and can only access outputs from agents that ran before it.

```bash
python main.py architect \
  --requirements "RAG pipeline for 10M financial documents, SOC2 required, AWS-only" \
  --context "Brazilian bank, data residency in Brazil mandatory" \
  --output output/architecture.json
```

**How CrewAI works here:**

```
Crew (sequential process):
  ┌─────────────────────────────────┐
  │ Agent 1: Technical Researcher   │
  │ Goal: Analyze requirements and  │
  │ identify core constraints       │
  └────────────┬────────────────────┘
               │ output →
  ┌────────────▼────────────────────┐
  │ Agent 2: Principal Architect    │
  │ Goal: Design pragmatic solution │
  │ architecture with phased plan   │
  └────────────┬────────────────────┘
               │ output →
  ┌────────────▼────────────────────┐
  │ Agent 3: Solution Reviewer      │
  │ Goal: Validate feasibility,     │
  │ identify risks and gaps         │
  └─────────────────────────────────┘
```

**Sample output — Meridian Bank architecture score: 84/100**

---

## Module 5 — Proposal Writer
### LangChain prompt chaining

Consolidates outputs from all previous modules into a polished, customer-ready proposal. Each of the 5 sections is generated by a dedicated LangChain prompt chain, with context passed between sections.

```bash
python main.py proposal \
  --account-brief output/account.json \
  --discovery output/discovery.json \
  --architecture output/architecture.json \
  --output output/proposal.md
```

**How LangChain chaining works here:**

```python
chain = ChatPromptTemplate.from_template(section_prompt) | llm | StrOutputParser()
```

Five chains run in sequence. Each section prompt receives the relevant context from previous modules. The output is a structured Markdown document ready to share with the customer.

**Generated sections:**
1. Executive Summary — business-language overview tailored to the customer's challenges
2. Solution Overview — non-technical description of the proposed architecture
3. Business Value — quantified ROI and strategic value
4. Implementation Roadmap — phased plan with milestones and success criteria
5. Next Steps — action items, open questions, and decision timeline

---

## Full Example: Meridian Bank

The `examples/meridian_bank/` directory contains pre-generated outputs for a complete fictional enterprise account — a Brazilian bank evaluating AI for customer service, compliance, and credit risk.

```bash
# Run any module against the example context
python main.py account-intel "Meridian Bank" --industry "Financial Services"
python main.py discovery --context "$(cat examples/meridian_bank/context.txt)"
```

**Pre-generated outputs:**
- [`01_account_brief.json`](examples/meridian_bank/outputs/01_account_brief.json) — Account intelligence with 5 AI opportunities and ROI estimates
- [`02_discovery_summary.json`](examples/meridian_bank/outputs/02_discovery_summary.json) — Discovery summary with 81/100 quality score
- [`03_architecture.json`](examples/meridian_bank/outputs/03_architecture.json) — 3-phase architecture recommendation scored 84/100 by the reviewer agent

---

## Project Structure

```
solutions-engineer-toolkit/
├── main.py                           # Unified CLI (Click)
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .github/
│   └── workflows/ci.yml              # GitHub Actions: lint + test + type-check
├── tools/
│   ├── config.py                     # Shared Config dataclass
│   ├── account_intelligence/
│   │   └── agent.py                  # RAG + ChromaDB + OpenAI
│   ├── discovery_agent/
│   │   └── agent.py                  # LangGraph stateful graph
│   ├── rfp_analyzer/
│   │   └── agent.py                  # OpenAI Agents SDK + tool use
│   ├── solution_architect/
│   │   └── agent.py                  # CrewAI multi-agent crew
│   └── proposal_writer/
│       └── agent.py                  # LangChain prompt chaining
├── knowledge_base/
│   ├── financial_services.md         # Industry knowledge for RAG
│   └── retail_ecommerce.md
└── examples/
    └── meridian_bank/
        ├── context.txt
        └── outputs/                  # Pre-generated module outputs
```

---

## Why This Stack

These are not toy frameworks chosen for this project. They are the exact tools that enterprise AI teams at Google Cloud, NVIDIA, and OpenAI recommend to customers building production agentic systems.

| Framework | Who Uses It in Production |
|-----------|--------------------------|
| LangGraph | Google Cloud's Vertex AI Agent Builder, production banking chatbots globally |
| CrewAI | Enterprise multi-agent orchestration, used by NVIDIA's partner ecosystem |
| OpenAI Agents SDK | Native to OpenAI platform — the recommended pattern for tool-using agents |
| LangChain | The most widely adopted LLM application framework in enterprise |
| ChromaDB | Embedded vector store for production RAG — no external service required |

---

## Requirements

- Python 3.10+
- OpenAI API key

---

## License

Copyright (c) 2026 Fabricio Puliafico Artur. Released under the MIT License. See [LICENSE](LICENSE) for details.
