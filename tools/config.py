"""Shared configuration for all SE Toolkit modules."""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class ToolkitError(RuntimeError):
    """Base exception for all SE Toolkit errors."""


@dataclass(frozen=True)
class Config:
    openai_api_key: str
    model: str

    @classmethod
    def load(cls) -> "Config":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ToolkitError(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
            )
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini").strip() or "gpt-5.4-mini"
        return cls(openai_api_key=api_key, model=model)
