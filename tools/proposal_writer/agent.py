"""Proposal Writer — LangChain with structured prompt chaining.

Consolidates outputs from all previous toolkit modules into a polished,
customer-ready proposal document. Uses LangChain's prompt chaining to
produce each section in sequence, maintaining context across sections.
"""

from __future__ import annotations

import json
from pathlib import Path

from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from tools.config import Config

_SECTION_PROMPTS: dict[str, str] = {
    "executive_summary": """You are a senior Solutions Engineer writing a customer proposal.

Account Brief: {account_brief}
Discovery Summary: {discovery_summary}

Write a compelling executive summary (3-4 paragraphs) that:
1. Acknowledges the customer's specific business challenges
2. States clearly how the proposed solution addresses them
3. Highlights the expected business outcomes
4. Ends with a clear call to action

Write in professional business English. Be specific, not generic.""",

    "solution_overview": """You are writing the Solution Overview section of an enterprise proposal.

Architecture Recommendation: {architecture}
Customer Requirements: {requirements}

Write a clear, non-technical solution overview (4-5 paragraphs) that:
1. Describes the proposed solution in business terms
2. Explains the key components and how they work together
3. Highlights why this approach fits the customer's context
4. Describes the implementation approach at a high level

Avoid deep technical jargon. The audience is a business decision-maker.""",

    "business_value": """You are writing the Business Value section of an enterprise proposal.

Account Context: {account_brief}
Solution: {architecture}

Write the Business Value section including:
1. Quantified benefits where possible (time saved, cost reduced, risk mitigated)
2. ROI narrative (qualitative if numbers not available)
3. Strategic value beyond immediate ROI
4. Competitive advantage the customer gains

Be specific to the customer's industry and challenges.""",

    "implementation_roadmap": """You are writing the Implementation Roadmap section.

Architecture Phases: {architecture}
Discovery Gaps: {discovery_gaps}

Write a clear implementation roadmap with:
1. Phase 1 — MVP / Proof of Concept (weeks 1-6)
2. Phase 2 — Production Deployment (weeks 7-16)
3. Phase 3 — Scale & Optimize (weeks 17-24)

For each phase: objectives, deliverables, success criteria, dependencies.""",

    "next_steps": """You are writing the Next Steps section of a proposal.

Go/No-Go: {go_no_go}
Clarification Questions: {clarification_questions}

Write a concise Next Steps section with:
1. Immediate next actions (this week)
2. Outstanding questions that need customer input
3. Decision timeline recommendation
4. How to engage for the next stage

Keep it action-oriented and easy to follow.""",
}


def _render_section(
    section_name: str,
    llm: ChatOpenAI,
    **kwargs: str,
) -> str:
    template = _SECTION_PROMPTS[section_name]
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke(kwargs)


def run(
    account_brief: dict,
    discovery_summary: dict,
    architecture: dict,
    go_no_go: dict,
    config: Config,
) -> dict:
    """Generate a full proposal by chaining LangChain prompts for each section."""
    llm = ChatOpenAI(
        model=config.model,
        api_key=config.openai_api_key,
        temperature=0.3,
    )

    brief_str = json.dumps(account_brief, indent=2)
    discovery_str = json.dumps(discovery_summary, indent=2)
    arch_str = json.dumps(architecture, indent=2)
    go_no_go_str = json.dumps(go_no_go, indent=2)
    gaps_str = json.dumps(discovery_summary.get("gaps", []), indent=2)
    questions_str = json.dumps(
        go_no_go.get("clarification_questions", discovery_summary.get("recommended_next_questions", [])),
        indent=2,
    )
    requirements_str = json.dumps(account_brief.get("ai_opportunities", []), indent=2)

    sections = {
        "executive_summary": _render_section(
            "executive_summary", llm,
            account_brief=brief_str,
            discovery_summary=discovery_str,
        ),
        "solution_overview": _render_section(
            "solution_overview", llm,
            architecture=arch_str,
            requirements=requirements_str,
        ),
        "business_value": _render_section(
            "business_value", llm,
            account_brief=brief_str,
            architecture=arch_str,
        ),
        "implementation_roadmap": _render_section(
            "implementation_roadmap", llm,
            architecture=arch_str,
            discovery_gaps=gaps_str,
        ),
        "next_steps": _render_section(
            "next_steps", llm,
            go_no_go=go_no_go_str,
            clarification_questions=questions_str,
        ),
    }

    return {
        "company": account_brief.get("company", ""),
        "proposal": sections,
    }


def to_markdown(proposal: dict) -> str:
    """Render the proposal dict as a formatted Markdown document."""
    company = proposal.get("company", "Customer")
    sections = proposal.get("proposal", {})

    lines = [
        f"# Enterprise AI Proposal — {company}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        sections.get("executive_summary", ""),
        "",
        "---",
        "",
        "## Solution Overview",
        "",
        sections.get("solution_overview", ""),
        "",
        "---",
        "",
        "## Business Value",
        "",
        sections.get("business_value", ""),
        "",
        "---",
        "",
        "## Implementation Roadmap",
        "",
        sections.get("implementation_roadmap", ""),
        "",
        "---",
        "",
        "## Next Steps",
        "",
        sections.get("next_steps", ""),
    ]
    return "\n".join(lines)
