# Use QueryMind with your PostgreSQL database

The sample interface works without setup. This guide is for live queries against existing tables.

## Configure a local backend

Use Python 3.11 or newer. Create a virtual environment in the repository, activate it, and install `backend/requirements.txt`. Copy `.env.example` to `.env` and set:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
DATABASE_URL=postgresql://readonly_user:password@localhost:5432/your_database
CHROMA_URL=http://localhost:8001
```

Use a read-only database role with access only to the intended tables. For Groq, select `LLM_PROVIDER=groq` and configure `GROQ_API_KEY` and an available model. Credentials stay in `.env` or your deployment's secret settings.

Start the Chroma service with `docker compose up -d chromadb`, or set `CHROMA_PERSIST_DIR` to a local directory to use embedded persistence.

## Register and index the schema

From the backend directory:

```bash
cd backend
python scripts/setup_schema.py --schema-name my_database --pg-schema public
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The registration helper verifies table access, saves a profile to `app/schema_profiles.json`, and builds its Chroma collection. Embedding weights download on first use. Re-index after changing table definitions. Avoid indexing sensitive fields that should not be sent to the model provider.

Open http://localhost:8000, select **Live database**, and choose **My_database** in the data source selector. Available profile names come from `/health`. You can also POST to `/query` with `schema_name: "my_database"`.

## Docker backend with an external database

Set `DATABASE_URL` to a host reachable from the backend container. On Docker Desktop, `host.docker.internal` can address a database on the host; `localhost` inside a container refers to that container. Register the profile before starting the backend, and keep its `collection_name` unique. The Compose backend sets `CHROMA_URL=http://chromadb:8000`.

The PostgreSQL schema must already contain your tables. Sample seed scripts are for the bundled demo database only and should not be run against your existing database.
