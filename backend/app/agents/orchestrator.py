"""Cached, schema-scoped entry point for the QueryMind pipeline."""
from __future__ import annotations
import time
from threading import Lock
from urllib.parse import quote
from app.config import SCHEMA_PROFILES, DEFAULT_SCHEMA

_agent_cache: dict = {}
_cache_lock = Lock()


def _build_db_url_with_schema(base_url: str, pg_schema: str) -> str:
    if pg_schema == "public":
        return base_url
    connector = "&" if "?" in base_url else "?"
    return f"{base_url}{connector}options={quote('-csearch_path=' + pg_schema, safe='')}"


def _build_agents(schema_name: str):
    # Load embedding/provider dependencies only for live queries.
    from app.agents.schema_linker import SchemaLinker
    from app.agents.sql_generator import SQLGenerator
    from app.agents.critic import CriticAgent
    from app.agents.executor import ExecutorAgent
    from app.agents.self_correction import CorrectionAgent
    profile = SCHEMA_PROFILES[schema_name]
    agent = CorrectionAgent(
        schema_linker=SchemaLinker(collection_name=profile["collection_name"], pg_schema=profile["pg_schema"]),
        sql_generator=SQLGenerator(),
        critic=CriticAgent(),
        executor=ExecutorAgent(_build_db_url_with_schema(profile["db_url"], profile["pg_schema"])),
        max_attempts=3,
    )
    _agent_cache[schema_name] = agent
    return agent


def _get_agent(schema_name: str):
    with _cache_lock:
        if schema_name not in _agent_cache:
            return _build_agents(schema_name)
        return _agent_cache[schema_name]


def _serialize_rows(rows):
    """Preserve SQLAlchemy column names and support older tuple results."""
    if rows is None:
        return None
    return [dict(row._mapping) if hasattr(row, "_mapping") else row if isinstance(row, dict) else list(row) for row in rows]


def run_query(question: str, schema_name: str = DEFAULT_SCHEMA, max_attempts: int = 3) -> dict:
    if schema_name not in SCHEMA_PROFILES:
        raise ValueError(f"Unknown schema '{schema_name}'. Available profiles: {list(SCHEMA_PROFILES)}")
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be an integer between 1 and 5")
    start = time.monotonic()
    result = _get_agent(schema_name).execute_with_retry(question, max_attempts=max_attempts)
    execution = result.execution_result or {}
    rows = _serialize_rows(execution.get("data")) if result.success else None
    error_type = execution.get("error_type")
    error_message = execution.get("error_message")
    if not result.success and not error_message:
        error_type = "validation_failed"
        error_message = "The generated SQL did not pass validation. Try a more specific question."
    return {
        "sql": execution.get("sql_executed") or result.final_sql,
        "success": result.success,
        "attempts": result.attempts,
        "first_attempt_success": result.success and result.attempts == 1,
        "latency_ms": round((time.monotonic() - start) * 1000, 2),
        "schema_tables_used": result.schema_tables_used or [],
        "correction_applied": result.attempts > 1,
        "rows": rows,
        "columns": execution.get("columns", []),
        "row_count": len(rows) if rows is not None else 0,
        "error_type": error_type,
        "error_message": error_message,
    }
