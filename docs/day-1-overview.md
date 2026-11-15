# QueryMind – Day 1 Progress Overview

**Date:**  
**Milestone:** ✅ Schema Intelligence & Infrastructure

---

## 🎯 What Is QueryMind?

QueryMind is a **production-grade Text-to-SQL system** that:
- Lets users ask questions in natural language
- Generates SQL queries automatically
- Executes them against a PostgreSQL database
- Will **self-correct** when queries fail (in later milestones)

The end goal is a **multi-agent system** (Schema Linker, SQL Generator, Critic, Executor, Corrector) with ~85%+ execution success rate.

---

## ✅ Day 1 Objectives

**Focus:** Infrastructure + Schema Intelligence

Today’s goals:
- Set up Postgres + Chroma DB via Docker **with persistence**
- Implement a **Schema Metadata Extractor**
- Implement a **Schema Embedder** (local embeddings, no API cost)
- Integrate **Chroma DB** for vector storage
- Build a **Schema Linker Agent** that:
  - Takes a natural language question
  - Returns relevant tables + columns from the database

---

## 🧱 What We Built Today

### 1. Dockerized Data Layer

- **PostgreSQL 16**
  - Database: `ecommerce`
  - 7 tables: `customers`, `categories`, `products`, `orders`, `order_items`, `reviews`, `payments`
  - Volume-mounted for **data persistence** across restarts

- **Chroma DB 1.4.1**
  - Runs as a separate container
  - Stores vector embeddings of schema elements

We also ran a **persistence test** to confirm that Postgres data survives container restarts.

---

### 2. Schema Intelligence Layer

Key files:
- `app/schema/extractor.py`
- `app/schema/embedder.py`
- `app/schema/chroma_manager.py`
- `app/agents/schema_linker.py`

**Components:**

1. **SchemaMetadataExtractor**
   - Uses SQLAlchemy to introspect PostgreSQL
   - Extracts table names, columns, data types, primary keys, and foreign keys

2. **SchemaEmbedder**
   - Uses `sentence-transformers` (`all-MiniLM-L6-v2`)
   - Creates text descriptions for tables and columns
   - Generates local embeddings (no external API calls)

3. **ChromaManager**
   - Manages the `querymind_schema` collection in Chroma DB
   - Stores documents, embeddings, and metadata
   - Supports similarity search over schema elements

4. **SchemaLinker Agent**
   - Pipeline:
     - PostgreSQL schema → Extractor → Embedder → Chroma
     - Question → embed → query Chroma → relevant tables/columns
   - Example:
     - Question: “What are the top 10 products by revenue?”
     - Returns something like:
       ```python
       {
         "products": [...],
         "order_items": [...]
       }
       ```

This layer is the **“schema brain”** of QueryMind and will be used by the SQL Generator from Day 2 onward.

---

## 📊 Day 1 Results

A small test suite of 5 questions was used to evaluate schema retrieval:

- Example questions:
  - “What are the top 10 products by revenue?”
  - “Show me customer information”
  - “Find orders from last month”
  - “Which products have low stock?”
  - “Show customer reviews and ratings”

**Metrics:**

| Metric                     | Target  | Actual    |
|----------------------------|---------|-----------|
| Tables Indexed             | 7       | 7         |
| Schema Embeddings Created  | 60+     | 45        |
| **Schema Recall**          | ≥ 85%   | **90%** ✅ |
| Schema Precision           | ≥ 70%   | 38.33% ⚠️ |
| Retrieval Latency          | < 500ms | ~50ms ✅  |

**Interpretation:**
- **High recall** means the system almost always includes the correct tables.
- **Lower precision** mainly reflects extra but related tables being included.
- For Day 1, this is acceptable: later agents (SQL Generator + Critic) will decide which tables to actually use.

---

## 🧠 LLM & Cost Strategy

Configured (but not yet used in Day 1 logic):

- **Primary LLM:** Groq (Llama 3.1 70B) via `langchain_groq`
- **Backup LLM:** OpenAI GPT-4o-mini via `langchain_openai`

Embeddings are computed **locally** using `sentence-transformers`, which keeps API costs effectively at zero for Day 1.

---

## 🔭 What’s Next (Day 2 Preview)

Tomorrow’s focus:

- Design SQL generation prompts
- Implement the **SQL Generator Agent** using Groq as the default LLM
- Wire it to Schema Linker:
  - Question → Schema Linker → SQL Generator → SQL
- Create an initial evaluation set (20 questions)
- Measure baseline SQL execution success (before adding any self-correction)

---

## 📂 Current Repo Snapshot (High-Level)

```text
querymind/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   └── schema_linker.py
│   │   ├── schema/
│   │   │   ├── extractor.py
│   │   │   ├── embedder.py
│   │   │   └── chroma_manager.py
│   │   └── config.py
│   ├── tests/
│   │   └── test_schema_retrieval.py
│   └── requirements.txt
├── database/
│   └── schemas/
│       └── ecommerce.sql
├── docker-compose.yml
├── .env (local, not committed)
└── docs/
    ├── day-1-overview.md
    └── daily-docs/
        └── day-1.md
```

---

**Day 1 Status:** ✅ Shipped  
**Core Achievement:** A working, vector-based schema intelligence layer with 90% recall, ready to support SQL generation from Day 2 onward.
