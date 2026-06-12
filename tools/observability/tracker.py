"""Observability — LLM call tracking with latency, tokens, and cost.

Wraps any toolkit module call and logs execution metadata to a local
SQLite database. Provides a CLI dashboard to inspect usage across modules.

This is the observability layer that separates production-grade AI systems
from demos: without it, you cannot answer "how much did this cost?",
"which module is slowest?", or "where did the last failure occur?"
"""

from __future__ import annotations

import functools
import json
import sqlite3
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Generator

_DB_PATH = Path(".se_toolkit_metrics.db")

# Cost per 1M tokens (input / output) — OpenAI GPT-5 family
_MODEL_COSTS: dict[str, tuple[float, float]] = {
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4":      (2.50, 15.00),
    "gpt-5.5":      (5.00, 30.00),
}


@dataclass
class Span:
    module: str
    model: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: str = ""
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    status: str = "ok"
    error: str = ""
    metadata: dict = field(default_factory=dict)


def _get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS spans (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            module      TEXT NOT NULL,
            model       TEXT NOT NULL,
            started_at  TEXT NOT NULL,
            ended_at    TEXT NOT NULL,
            latency_ms  INTEGER NOT NULL,
            input_tokens  INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd    REAL DEFAULT 0.0,
            status      TEXT DEFAULT 'ok',
            error       TEXT DEFAULT '',
            metadata    TEXT DEFAULT '{}'
        )
    """)
    conn.commit()
    return conn


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    costs = _MODEL_COSTS.get(model, (2.50, 15.00))
    return (input_tokens * costs[0] + output_tokens * costs[1]) / 1_000_000


def _save_span(span: Span) -> None:
    with _get_db() as conn:
        conn.execute(
            """INSERT INTO spans
               (module, model, started_at, ended_at, latency_ms,
                input_tokens, output_tokens, cost_usd, status, error, metadata)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                span.module, span.model, span.started_at, span.ended_at,
                span.latency_ms, span.input_tokens, span.output_tokens,
                span.cost_usd, span.status, span.error,
                json.dumps(span.metadata),
            ),
        )


@contextmanager
def trace(module: str, model: str, metadata: dict | None = None) -> Generator[Span, None, None]:
    """Context manager that records a single module execution as a span."""
    span = Span(module=module, model=model, metadata=metadata or {})
    t0 = time.perf_counter()
    try:
        yield span
        span.status = "ok"
    except Exception as exc:
        span.status = "error"
        span.error = traceback.format_exc(limit=5)
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        span.ended_at = datetime.now(timezone.utc).isoformat()
        span.latency_ms = elapsed_ms
        span.cost_usd = _estimate_cost(model, span.input_tokens, span.output_tokens)
        _save_span(span)


def observed(module_name: str) -> Callable:
    """Decorator that wraps a run() function with automatic tracing."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            config = kwargs.get("config") or (args[-1] if args else None)
            model = getattr(config, "model", "unknown") if config else "unknown"
            with trace(module=module_name, model=model) as span:
                result = fn(*args, **kwargs)
                return result
        return wrapper
    return decorator


def get_metrics() -> list[dict]:
    """Return all recorded spans as a list of dicts."""
    with _get_db() as conn:
        rows = conn.execute(
            "SELECT module, model, started_at, latency_ms, input_tokens, "
            "output_tokens, cost_usd, status, error FROM spans ORDER BY id DESC LIMIT 200"
        ).fetchall()
    keys = ["module", "model", "started_at", "latency_ms", "input_tokens",
            "output_tokens", "cost_usd", "status", "error"]
    return [dict(zip(keys, row)) for row in rows]


def get_summary() -> dict:
    """Return aggregate metrics grouped by module."""
    with _get_db() as conn:
        rows = conn.execute("""
            SELECT module,
                   COUNT(*) as runs,
                   ROUND(AVG(latency_ms)) as avg_latency_ms,
                   SUM(input_tokens) as total_input_tokens,
                   SUM(output_tokens) as total_output_tokens,
                   ROUND(SUM(cost_usd), 6) as total_cost_usd,
                   SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as errors
            FROM spans
            GROUP BY module
            ORDER BY total_cost_usd DESC
        """).fetchall()
    keys = ["module", "runs", "avg_latency_ms", "total_input_tokens",
            "total_output_tokens", "total_cost_usd", "errors"]
    return {"by_module": [dict(zip(keys, row)) for row in rows]}
