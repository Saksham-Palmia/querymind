from fastapi import APIRouter, HTTPException
from app.api.models import QueryRequest, QueryResponse
from app.config import SCHEMA_PROFILES, settings

router = APIRouter()


def live_configured():
    key = settings.GROQ_API_KEY if settings.LLM_PROVIDER == "groq" else settings.OPENAI_API_KEY
    return bool(settings.DATABASE_URL and key)


def run_query(**kwargs):
    # Keep the workspace and health endpoint available without loading ML models.
    from app.agents.orchestrator import run_query as run_pipeline
    return run_pipeline(**kwargs)


@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    if request.schema_name not in SCHEMA_PROFILES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown schema '{request.schema_name}'. "
                f"Available: {list(SCHEMA_PROFILES.keys())}"
            ),
        )
    
    # Block sensitive queries before they enter the pipeline.
    SENSITIVE_KEYWORDS = [
        "password", "passwd", "secret", "credential", "credentials",
        "api_key", "apikey", "token", "private_key",
        "pg_shadow", "pg_authid", "information_schema.tables",
    ]
    question_lower = request.question.lower()
    if any(kw in question_lower for kw in SENSITIVE_KEYWORDS):
        return {
            "sql": "",
            "success": False,
            "attempts": 0,
            "first_attempt_success": False,
            "latency_ms": 0.0,
            "schema_tables_used": [],
            "correction_applied": False,
            "rows": [],
            "row_count": 0,
            "error_type": "blocked",
            "error_message": "This query was blocked for safety reasons.",
        }

    if not live_configured():
        raise HTTPException(status_code=503, detail="Live queries are not configured. Set DATABASE_URL and the API key for your selected LLM provider.")
    try:
        return run_query(
            question=request.question,
            schema_name=request.schema_name,
            max_attempts=request.max_attempts,
        )
    except Exception:
        # Avoid returning provider credentials or connection strings in errors.
        raise HTTPException(status_code=503, detail="The query pipeline is unavailable. Check the database, schema index, and LLM configuration, then try again.") from None


@router.get("/health")
def health():
    return {
        "status": "ok",
        "schemas_available": list(SCHEMA_PROFILES.keys()),
        "live_configured": live_configured(),
    }
