"""Discovery Agent — LangGraph stateful multi-turn conversation.

Conducts an AI-powered discovery session with adaptive questioning.
Uses LangGraph to maintain conversation state and decide the next
best question based on what has already been covered.
"""

from __future__ import annotations

import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from tools.config import Config

_DISCOVERY_DIMENSIONS = [
    "Business Challenges",
    "Current Technology Stack",
    "AI Maturity & Previous Initiatives",
    "Security & Compliance Requirements",
    "Budget & Timeline",
    "Decision-Making Process & Stakeholders",
    "Success Metrics",
]

_SYSTEM_PROMPT = """You are an expert Solutions Engineer conducting a discovery session.
Your goal is to uncover the customer's needs across these dimensions:
{dimensions}

Rules:
- Ask ONE focused question at a time
- Adapt your next question based on previous answers
- When you have sufficient coverage (at least 5 dimensions explored), output a JSON
  summary instead of a new question
- To signal you are done, start your response with: DISCOVERY_COMPLETE:
  followed by a JSON object with this schema:
  {{
    "summary": "",
    "covered_dimensions": {{}},
    "gaps": [""],
    "recommended_next_questions": [""],
    "discovery_quality_score": 0
  }}
"""


class DiscoveryState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    dimensions_covered: int
    complete: bool


def _build_graph(llm: ChatOpenAI) -> StateGraph:
    def se_node(state: DiscoveryState) -> dict:
        system = SystemMessage(
            content=_SYSTEM_PROMPT.format(
                dimensions="\n".join(f"- {d}" for d in _DISCOVERY_DIMENSIONS)
            )
        )
        response = llm.invoke([system] + state["messages"])
        content = response.content

        complete = content.startswith("DISCOVERY_COMPLETE:")
        return {
            "messages": [AIMessage(content=content)],
            "dimensions_covered": state["dimensions_covered"] + (1 if not complete else 0),
            "complete": complete,
        }

    def should_continue(state: DiscoveryState) -> str:
        return END if state["complete"] else "human_input"

    def human_input_node(state: DiscoveryState) -> dict:
        last_ai = next(
            (m.content for m in reversed(state["messages"]) if isinstance(m, AIMessage)),
            "",
        )
        print(f"\n\033[96mSE Agent:\033[0m {last_ai}\n")
        answer = input("\033[93mYour answer:\033[0m ").strip()
        return {"messages": [HumanMessage(content=answer)]}

    graph = StateGraph(DiscoveryState)
    graph.add_node("se_agent", se_node)
    graph.add_node("human_input", human_input_node)
    graph.set_entry_point("se_agent")
    graph.add_conditional_edges("se_agent", should_continue)
    graph.add_edge("human_input", "se_agent")
    return graph.compile()


def run(context: str, config: Config) -> dict:
    """Run an interactive discovery session and return the structured summary."""
    llm = ChatOpenAI(
        model=config.model,
        api_key=config.openai_api_key,
        temperature=0.3,
    )

    graph = _build_graph(llm)
    initial_state: DiscoveryState = {
        "messages": [
            HumanMessage(
                content=f"Customer context: {context}\n\nPlease start the discovery session."
            )
        ],
        "dimensions_covered": 0,
        "complete": False,
    }

    final_state = graph.invoke(initial_state, config={"recursion_limit": 50})

    last_message = next(
        (m.content for m in reversed(final_state["messages"]) if isinstance(m, AIMessage)),
        "",
    )

    if "DISCOVERY_COMPLETE:" in last_message:
        json_str = last_message.split("DISCOVERY_COMPLETE:", 1)[1].strip()
        if json_str.startswith("```"):
            json_str = json_str.split("```")[1]
            if json_str.startswith("json"):
                json_str = json_str[4:]
        return json.loads(json_str)

    return {"summary": last_message, "gaps": [], "recommended_next_questions": []}
