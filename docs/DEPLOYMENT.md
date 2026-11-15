# Running QueryMind

## Sample workspace

Run `python backend/scripts/preview.py` from the repository root and open http://127.0.0.1:8080. This uses the standard library and serves only the web assets. It does not expose the repository or `.env`. Live mode is available through FastAPI, not this preview server.

## Local Docker stack

Copy `.env.example` to `.env`, add your selected provider's API key, and run:

```bash
docker compose up --build
```

| Service | Local address |
| --- | --- |
| Workspace and API | http://localhost:8000 |
| OpenAPI documentation | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Chroma | http://localhost:8001 |

The first build installs model dependencies and the startup script indexes the sample schemas. PostgreSQL and Chroma use named volumes. Initialization scripts run only for a fresh PostgreSQL volume; existing data is retained. The bundled passwords are local sample defaults, not production credentials.

Use `docker compose logs backend` for startup diagnostics and `docker compose down` to stop the stack while retaining its volumes.

## Local Python backend

Install `backend/requirements.txt` in a virtual environment. Configure PostgreSQL and Chroma as described in the [database guide](../query_mind_use_with_your_own_database.md), index the schema, and run `uvicorn app.main:app --host 127.0.0.1 --port 8000` from `backend/`.

## Hosting a live instance

The backend Dockerfile can be used by a container host. Supply `DATABASE_URL`, provider settings, and `CHROMA_URL` through its secret configuration. Provide persistent Chroma storage or rebuild the index after replacement. Match the hosting platform's port to Uvicorn's port.

Before exposing the live API, add authentication, request limits, and HTTPS, and use a restricted read-only PostgreSQL account. A model receives the question and retrieved schema; choose the connected data accordingly. The checked-in Compose ports bind to localhost for local development.

There is no verified public live deployment bundled with this repository. The README screenshot uses sample fixtures.
