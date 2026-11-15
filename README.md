# QueryMind

### Ask PostgreSQL questions in plain English.

A workspace for turning natural-language questions into SQL, inspecting the query, and exploring the result. Try the built-in examples immediately, or connect your own database.

**[Quick start](#quick-start)** &nbsp; / &nbsp; **[Live setup](#live-setup)** &nbsp; / &nbsp; **[API reference](docs/query_pilot_api.md)** &nbsp; / &nbsp; **[Architecture](docs/ARCHITECTURE.MD)** &nbsp; / &nbsp; **[Build status](https://github.com/Saksham-Palmia/querymind/actions/workflows/ci.yml)**

---

## The workspace

| Capability | What you get |
| :--- | :--- |
| Natural-language queries | Ask a question against a selected PostgreSQL schema. |
| SQL inspection | View highlighted SQL and copy the executed query. |
| Result exploration | Named columns, row filtering, and CSV export. |
| Query correction | Schema retrieval, validation, and retries through LangGraph. |
| Execution details | Attempts, latency, relevant tables, and correction status. |
| Everyday controls | Session history, Ctrl/Cmd + Enter, and a responsive layout. |

## Quick start

Preview the interface with Python's standard library. No API key, database, or package installation is needed.

~~~bash
git clone https://github.com/Saksham-Palmia/querymind.git
cd querymind
python backend/scripts/preview.py
~~~

Open **http://127.0.0.1:8080** and choose a suggested question. Add `--port 8081` if needed.

| Mode | Data source | Requirements |
| :--- | :--- | :--- |
| **Sample** | Six curated examples across ecommerce and library data | Python for the preview server |
| **Live database** | Your configured PostgreSQL database | Backend, schema index, and an OpenAI or Groq API key |

Sample results are illustrative fixtures. Custom questions run through **Live database** mode.

## Live setup

Requires Docker with Compose and an API key for your chosen provider.

**1. Create your configuration.**

Copy [.env.example](.env.example) to `.env`.

~~~bash
# macOS / Linux
cp .env.example .env
~~~

~~~powershell
# Windows PowerShell
Copy-Item .env.example .env
~~~

Set `OPENAI_API_KEY`, or select `LLM_PROVIDER=groq` and set `GROQ_API_KEY`. The template includes the local Docker database and Chroma connection settings.

**2. Start the services.**

~~~bash
docker compose up --build
~~~

The first build installs dependencies and downloads the embedding model. A fresh PostgreSQL volume receives the sample schemas and seed data; existing volumes retain their data.

**3. Open the workspace.**

Visit **http://localhost:8000**, select **Live database**, choose a schema, and ask a question. Interactive API documentation is at **/docs**.

For existing tables or a backend running without Docker, use the [database guide](query_mind_use_with_your_own_database.md) and [deployment guide](docs/DEPLOYMENT.md).

## Inside a query

~~~text
Question → Retrieve schema → Generate SQL → Validate → Execute → Results
                                  ↑            │          │
                                  └──── Correct and retry ┘
~~~

The schema linker retrieves relevant tables from ChromaDB. An OpenAI or Groq model generates SQL, the critic validates it, and the executor runs it in a read-only transaction. Recoverable failures feed back into the correction loop.

The pipeline accepts **1–5 total attempts** per request, defaults to **3**, and returns up to **1,000 rows**. Responses include the executed SQL and column metadata. Each schema has an isolated agent graph; requests within one cached schema are serialized.

<details>
<summary><strong>Make a request directly</strong></summary>

~~~bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Which products have low stock?","schema_name":"ecommerce","max_attempts":3}'
~~~

Check both the HTTP status and the response's `success` field. Responses also include `sql`, `columns`, `rows`, `row_count`, `attempts`, `latency_ms`, `schema_tables_used`, `correction_applied`, and error information.

See the [API reference](docs/query_pilot_api.md) for validation and error behavior.

</details>

## Technology

| Layer | Implementation |
| :--- | :--- |
| Interface | HTML, CSS, vanilla JavaScript |
| API | FastAPI, Pydantic, Uvicorn |
| Query workflow | LangGraph, LangChain, OpenAI / Groq |
| Schema retrieval | ChromaDB, sentence-transformers |
| Database | PostgreSQL 16, SQLAlchemy, psycopg2 |
| Tooling | Docker Compose, pytest, GitHub Actions |

## Development

Run the lightweight tests without a database, provider keys, or embedding downloads:

~~~bash
python -m pip install -r backend/requirements-test.txt
cd backend
python -m pytest tests/unit -q
~~~

The suite covers request validation, API routing, result metadata, retry limits, graph isolation, and read-only execution. [Optional browser checks](backend/scripts/check_ui.py) use the `playwright` Python package with an already installed Chrome or Edge executable.

<details>
<summary><strong>Repository map</strong></summary>

~~~text
backend/app/web/       Interface
backend/app/api/       Endpoints and response models
backend/app/agents/    SQL generation, validation, execution, correction
backend/app/schema/    Metadata extraction and vector storage
backend/tests/unit/    Tests without external services
backend/scripts/      Preview, indexing, evaluation, browser checks
database/             Sample schemas and seed data
docs/                 Architecture, deployment, evaluation reports
~~~

</details>

<details>
<summary><strong>Evaluation and practical limits</strong></summary>

Historical [evaluation artifacts](backend/evaluation_results) record **67/70 execution successes** on the core ecommerce set. This is an earlier run, not a new benchmark of the current edition. SQL executing successfully does not establish that the result answers the question correctly.

The [verification notes](docs/VERIFICATION.md) describe the current checks and their scope. Live PostgreSQL/Chroma/LLM integration and a full Docker build have not been verified for this edition.

- The bundled stack is for local development and has no application login. A public live deployment needs authentication, request limits, HTTPS, and a restricted database account.
- SQL validation uses heuristics. Review generated queries and results.
- The browser stops waiting after two minutes; this does not cancel server-side work.
- CSV export includes all returned rows, including rows hidden by the current filter.
- Session history stays in memory and clears on reload. Provider calls may incur charges.
- Keep credentials in the ignored `.env` file or your hosting platform's secret settings.

</details>

---

**[Saksham Palmia](https://github.com/Saksham-Palmia)** &nbsp; · &nbsp; [MIT License](LICENSE) &nbsp; · &nbsp; Copyright © 2026 Saksham Palmia
