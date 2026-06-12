"""Account Intelligence — RAG + ChromaDB + OpenAI.

Researches a company and generates a structured pre-meeting account brief
for Solutions Engineers. Uses a local ChromaDB vector store seeded with
industry knowledge to enrich the analysis with relevant context.
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

from tools.config import Config

_KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent.parent / "knowledge_base"
_COLLECTION_NAME = "industry_knowledge"

SYSTEM_PROMPT = """You are a senior Solutions Engineer preparing for a customer meeting.
Your job is to produce a structured, actionable account brief that helps the SE walk into
the meeting fully prepared.

Use the industry context provided to enrich your analysis. Be specific, concise, and
focused on what matters for an enterprise AI pre-sales conversation.

Return only valid JSON matching the schema requested."""


def _get_chroma_collection(config: Config) -> chromadb.Collection:
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=config.openai_api_key,
        model_name="text-embedding-3-small",
    )
    client = chromadb.Client()
    collection = client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=ef,
    )
    if collection.count() == 0:
        _seed_knowledge_base(collection)
    return collection


def _seed_knowledge_base(collection: chromadb.Collection) -> None:
    """Seed the vector store with industry knowledge documents."""
    docs_dir = _KNOWLEDGE_BASE_DIR
    if not docs_dir.exists():
        return
    documents, ids = [], []
    for i, path in enumerate(sorted(docs_dir.glob("*.md"))):
        documents.append(path.read_text(encoding="utf-8"))
        ids.append(f"doc_{i}")
    if documents:
        collection.add(documents=documents, ids=ids)


def _retrieve_context(collection: chromadb.Collection, company: str, industry: str) -> str:
    query = f"{company} {industry} AI transformation enterprise challenges"
    results = collection.query(query_texts=[query], n_results=3)
    docs = results.get("documents", [[]])[0]
    return "\n\n---\n\n".join(docs) if docs else ""


def run(company: str, industry: str, config: Config) -> dict:
    """Generate an account brief for a given company."""
    collection = _get_chroma_collection(config)
    context = _retrieve_context(collection, company, industry)

    client = OpenAI(api_key=config.openai_api_key, timeout=60.0)

    user_prompt = f"""Research the company below and generate a complete account brief.

Company: {company}
Industry: {industry}

Industry knowledge context (retrieved via RAG):
{context if context else "No additional context available — rely on your training knowledge."}

Return a JSON object with this exact schema:
{{
  "company": "{company}",
  "industry": "{industry}",
  "company_overview": "",
  "business_challenges": [""],
  "ai_maturity": "Early / Developing / Advanced / Leading",
  "ai_opportunities": [
    {{
      "use_case": "",
      "business_impact": "",
      "complexity": "Low / Medium / High",
      "time_to_value": ""
    }}
  ],
  "key_stakeholders": [
    {{
      "title": "",
      "likely_priorities": "",
      "engagement_tip": ""
    }}
  ],
  "recommended_opening_questions": [""],
  "competitive_landscape": "",
  "recommended_solution_approach": "",
  "risks_and_objections": [""]
}}"""

    response = client.responses.create(
        model=config.model,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    content = response.output_text.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return json.loads(content)
