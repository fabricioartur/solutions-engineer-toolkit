"""RFP Analyzer — OpenAI Agents SDK with function calling / tool use.

Analyzes RFP, RFI, and tender documents using the OpenAI Responses API
with tool use. The agent calls specialized tools to extract requirements,
identify risks, and generate a go/no-go recommendation.
"""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI

from tools.config import Config

try:
    import pypdf
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False


_TOOLS = [
    {
        "type": "function",
        "name": "extract_requirements",
        "description": (
            "Extract and categorize all requirements from the RFP text. "
            "Returns a structured list of requirements with category, "
            "mandatory/optional flag, and fit assessment."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The full RFP document text to analyze.",
                }
            },
            "required": ["document_text"],
        },
    },
    {
        "type": "function",
        "name": "identify_risks",
        "description": (
            "Identify commercial, legal, technical, and delivery risks in the RFP. "
            "Returns a risk register with impact, probability, and mitigation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "The full RFP document text to analyze.",
                }
            },
            "required": ["document_text"],
        },
    },
    {
        "type": "function",
        "name": "generate_go_no_go",
        "description": (
            "Generate a GO / CONDITIONAL GO / NO-GO recommendation based on "
            "requirements, risks, and strategic fit."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "requirements_summary": {
                    "type": "string",
                    "description": "JSON string of extracted requirements.",
                },
                "risks_summary": {
                    "type": "string",
                    "description": "JSON string of identified risks.",
                },
            },
            "required": ["requirements_summary", "risks_summary"],
        },
    },
]

_SYSTEM_PROMPT = """You are a senior Solutions Engineer analyzing a procurement document.
Use the available tools in sequence:
1. First call extract_requirements to get all requirements
2. Then call identify_risks to build the risk register
3. Finally call generate_go_no_go with the outputs from steps 1 and 2

After all tool calls are complete, return a final JSON summary with keys:
requirements, risks, go_no_go, clarification_questions, executive_summary."""


def _extract_pdf_text(path: Path) -> str:
    if not _PYPDF_AVAILABLE:
        raise RuntimeError("pypdf is not installed. Run: pip install -r requirements.txt")
    reader = pypdf.PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _call_tool(tool_name: str, tool_args: dict, document_text: str, client: OpenAI, model: str) -> str:
    """Execute a tool call by running a focused sub-prompt."""
    if tool_name == "extract_requirements":
        prompt = f"""Extract all requirements from this document. Return JSON array:
[{{"id":"REQ-001","category":"Technical|Commercial|Security|Legal|Compliance",
"description":"","mandatory":true,"fit":"Good fit|Partial fit|Gap|Needs review","notes":""}}]

Document:
{document_text[:60000]}"""
    elif tool_name == "identify_risks":
        prompt = f"""Identify all risks in this document. Return JSON array:
[{{"id":"RISK-001","description":"","category":"Commercial|Legal|Technical|Delivery",
"impact":"High|Medium|Low","probability":"High|Medium|Low","mitigation":"","owner":"SE|Legal|Product"}}]

Document:
{document_text[:60000]}"""
    else:  # generate_go_no_go
        prompt = f"""Based on these requirements and risks, generate a go/no-go recommendation.
Return JSON: {{"recommendation":"GO|CONDITIONAL GO|NO-GO","rationale":"",
"key_strengths":[],"key_concerns":[],"next_actions":[],"clarification_questions":[]}}

Requirements: {tool_args.get('requirements_summary','')[:3000]}
Risks: {tool_args.get('risks_summary','')[:3000]}"""

    response = client.responses.create(
        model=model,
        input=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.output_text.strip()


def run(pdf_path: str, config: Config) -> dict:
    """Analyze an RFP document using the OpenAI Agents SDK with tool use."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {pdf_path}")

    document_text = _extract_pdf_text(path)
    client = OpenAI(api_key=config.openai_api_key, timeout=120.0)

    response = client.responses.create(
        model=config.model,
        input=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this RFP document ({len(document_text)} chars). Call the tools in sequence to produce the full analysis."},
        ],
        tools=_TOOLS,
        temperature=0.1,
    )

    tool_results: dict[str, str] = {}

    while response.stop_reason == "tool_calls" or (
        hasattr(response, "output") and any(
            getattr(item, "type", None) == "function_call" for item in (response.output or [])
        )
    ):
        tool_calls = [
            item for item in (response.output or [])
            if getattr(item, "type", None) == "function_call"
        ]
        if not tool_calls:
            break

        tool_outputs = []
        for tc in tool_calls:
            args = json.loads(tc.arguments) if isinstance(tc.arguments, str) else tc.arguments
            result = _call_tool(tc.name, args, document_text, client, config.model)
            tool_results[tc.name] = result
            tool_outputs.append({
                "type": "function_call_output",
                "call_id": tc.call_id,
                "output": result,
            })

        previous_input = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this RFP document. Call tools in sequence."},
        ] + [item for item in (response.output or [])] + tool_outputs

        response = client.responses.create(
            model=config.model,
            input=previous_input,
            tools=_TOOLS,
            temperature=0.1,
        )

    final_text = response.output_text.strip() if hasattr(response, "output_text") else ""

    if final_text.startswith("```"):
        final_text = final_text.split("```")[1]
        if final_text.startswith("json"):
            final_text = final_text[4:]

    try:
        return json.loads(final_text)
    except (json.JSONDecodeError, ValueError):
        return {
            "requirements": json.loads(tool_results.get("extract_requirements", "[]")),
            "risks": json.loads(tool_results.get("identify_risks", "[]")),
            "go_no_go": json.loads(tool_results.get("generate_go_no_go", "{}")),
            "executive_summary": final_text,
        }
