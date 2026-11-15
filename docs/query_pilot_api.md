# QueryMind API

The workspace is served at `/`. Open `/docs` for the generated OpenAPI interface.

## GET /health

Returns `status`, `schemas_available`, and `live_configured`. Configuration presence does not verify connectivity to PostgreSQL, Chroma, or the LLM provider.

## POST /query

| Field | Default | Validation |
| --- | --- | --- |
| `question` | required | Trimmed text, 1–2,000 characters |
| `schema_name` | `ecommerce` | A key in `backend/app/schema_profiles.json` |
| `max_attempts` | `3` | 1–5 total attempts, applied per request |

```json
{"question":"List five products","schema_name":"ecommerce","max_attempts":3}
```

Responses provide the executed `sql` (including the applied row limit), `success`, `attempts`, `first_attempt_success`, `latency_ms`, `schema_tables_used`, `correction_applied`, `columns`, `rows`, `row_count`, `error_type`, and `error_message`. SQLAlchemy rows are serialized to objects keyed by column name; legacy tuple results are also supported. Column metadata is preserved when no rows are returned.

| Status | Meaning |
| --- | --- |
| 200 | Completed pipeline response; inspect `success` and error fields |
| 400 | Unknown schema |
| 422 | Invalid or missing request fields |
| 503 | Missing configuration or an unavailable pipeline dependency |

Sensitive questions can return a blocked response with `success: false` before model calls. An execution failure is not necessarily an HTTP failure. Client code must check both HTTP status and `success`.

The executor applies a read-only transaction, statement timeout, and a 1,000-row fetch cap. Requests for one schema are serialized; different schemas have isolated graphs. No streaming or server-side cancellation endpoint is provided. The API has no built-in authentication; protect a live public deployment before exposing it.
