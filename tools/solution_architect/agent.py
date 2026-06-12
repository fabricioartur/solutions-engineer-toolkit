"""Solution Architect — CrewAI multi-agent crew.

A crew of three specialized AI agents that collaborate to produce
an enterprise solution architecture recommendation:

- Researcher Agent: analyzes requirements and constraints
- Architect Agent: designs the solution architecture
- Reviewer Agent: validates feasibility and identifies gaps
"""

from __future__ import annotations

import json

from crewai import Agent, Crew, Process, Task
from crewai_tools import BaseTool as CrewBaseTool
from langchain_openai import ChatOpenAI

from tools.config import Config


class RequirementsAnalysisTool(CrewBaseTool):
    name: str = "Requirements Analyzer"
    description: str = "Analyzes a requirements document and returns structured constraints."

    def _run(self, requirements: str) -> str:
        return f"Analyzed requirements: {requirements[:500]}..."


def run(requirements: str, account_context: str, config: Config) -> dict:
    """Run the Solution Architect crew and return the architecture recommendation."""

    llm = ChatOpenAI(
        model=config.model,
        api_key=config.openai_api_key,
        temperature=0.2,
    )

    researcher = Agent(
        role="Senior Technical Researcher",
        goal=(
            "Deeply analyze customer requirements and identify the core technical "
            "challenges, constraints, and success criteria."
        ),
        backstory=(
            "You are a Solutions Engineer with 15 years of experience in enterprise AI "
            "deployments. You excel at translating business requirements into technical "
            "constraints and identifying hidden complexity."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    architect = Agent(
        role="Principal Solution Architect",
        goal=(
            "Design a pragmatic, scalable solution architecture that meets the customer's "
            "requirements and can be delivered within their constraints."
        ),
        backstory=(
            "You are a Principal Architect who has designed AI solutions for Fortune 500 "
            "companies. You favor proven patterns, avoid over-engineering, and always "
            "consider operational complexity."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    reviewer = Agent(
        role="Solution Reviewer & Risk Analyst",
        goal=(
            "Review the proposed architecture for feasibility, risks, and gaps. "
            "Provide specific, actionable feedback."
        ),
        backstory=(
            "You are a senior SE who has reviewed hundreds of enterprise AI proposals. "
            "You have a sharp eye for hidden risks, integration complexity, and "
            "unrealistic timelines."
        ),
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    research_task = Task(
        description=f"""Analyze the following customer requirements and account context.
Identify: core technical challenges, key constraints, must-have vs nice-to-have,
integration complexity, and success criteria.

Requirements:
{requirements}

Account Context:
{account_context}

Output a structured analysis in JSON format.""",
        agent=researcher,
        expected_output="JSON with: challenges, constraints, success_criteria, integration_points",
    )

    architecture_task = Task(
        description="""Based on the research analysis, design a complete solution architecture.
Include: recommended approach, component breakdown, data flow, technology choices with
rationale, implementation phases (MVP → Full), and estimated timeline.

Output a comprehensive architecture recommendation in JSON format.""",
        agent=architect,
        expected_output="JSON with: approach, components, technology_choices, phases, timeline",
        context=[research_task],
    )

    review_task = Task(
        description="""Review the proposed architecture. Identify risks, gaps, and
dependencies that could derail the project. Suggest mitigations for each risk.
Provide a final architecture score (0-100) and recommendation.

Output your review in JSON format.""",
        agent=reviewer,
        expected_output="JSON with: risks, gaps, mitigations, score, final_recommendation",
        context=[architecture_task],
    )

    crew = Crew(
        agents=[researcher, architect, reviewer],
        tasks=[research_task, architecture_task, review_task],
        process=Process.sequential,
        verbose=False,
    )

    result = crew.kickoff()

    output_text = str(result)
    if output_text.startswith("```"):
        output_text = output_text.split("```")[1]
        if output_text.startswith("json"):
            output_text = output_text[4:]

    try:
        return json.loads(output_text)
    except (json.JSONDecodeError, ValueError):
        return {
            "architecture_recommendation": output_text,
            "research": str(research_task.output) if research_task.output else "",
            "review": str(review_task.output) if review_task.output else "",
        }
