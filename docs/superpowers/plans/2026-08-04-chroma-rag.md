# Chroma RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a configurable, persistent Chroma retrieval path and reliable JSON/PDF/DOCX knowledge ingestion while preserving the existing local-keyword path and all safety/work-order/report API contracts.

**Architecture:** Normalize every imported clause into a typed `KnowledgeClause` record. SQLite remains the source of record for clause metadata and the existing `local_keyword` provider continues reading the configured JSON file; Chroma is an independently persisted projection under `CHROMA_DIR`. `KnowledgeService` owns API-facing search/status/reindex orchestration, while parsers and the Chroma index are testable components. Chroma uses a deterministic local character n-gram embedding so the default Docker and local workflows require no external API or model download.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy/Alembic, ChromaDB 1.5.x, pypdf, python-docx, Vue 3 + TypeScript, pytest, Vitest, Docker Compose named volumes.

---

### Task 1: Define normalized knowledge records and parser contracts

**Files:**
- Create: `backend/app/knowledge/__init__.py`
- Create: `backend/app/knowledge/types.py`
- Create: `backend/app/knowledge/parsers.py`
- Create: `backend/tests/test_knowledge_ingest.py`
- Modify: `backend/pyproject.toml`
- Modify: `backend/requirements-docker.txt`

- [ ] **Step 1: Write failing parser tests**

Create JSON, DOCX, and text-extraction fixtures in temporary paths. Assert every returned `KnowledgeClause` preserves `document_id`, `source`, `title`, `article`, `category`, `content`, `version`, `effective_date`, and metadata. Assert unsupported extensions and article-less PDF/DOCX text raise `KnowledgeParseError` rather than inventing an article.

- [ ] **Step 2: Run the parser tests and confirm the expected failure**

Run:

```powershell
cd E:\cc项目\buildwise-agent\backend
.\venv\Scripts\python.exe -m pytest tests/test_knowledge_ingest.py -q
```

Expected: FAIL because `app.knowledge.parsers` and `KnowledgeClause` do not exist.

- [ ] **Step 3: Add the typed clause and parser implementation**

Implement:

```python
def parse_knowledge_file(
    path: Path,
    *,
    source: str | None = None,
    title: str | None = None,
    category: str | None = None,
    version: str = "",
    effective_date: str | None = None,
) -> list[KnowledgeClause]: ...
```

JSON accepts a list or an object containing `clauses`, `articles`, `documents`, or `items`; explicit IDs and fields win, and a missing ID uses a stable SHA-256-derived ID. PDF uses `pypdf.PdfReader`; DOCX uses `python_docx.Document`. Both split only on explicit headings such as `第12条` or `4.3.1`, and reject text with no recognizable article heading. Dates are normalized to ISO strings; unknown source metadata remains in `metadata`.

- [ ] **Step 4: Run parser tests and verify green**

Run the targeted test command again and require all parser, field-preservation, JSON/PDF/DOCX, and rejection tests to pass.

- [ ] **Step 5: Add pinned runtime dependencies and rerun targeted tests**

Add `chromadb>=1.5.9,<1.6`, `pypdf>=6.14,<7`, and `python-docx>=1.2,<2` to both runtime manifests, install `backend[dev]`, and rerun `tests/test_knowledge_ingest.py`.

### Task 2: Implement the persistent Chroma index and provider

**Files:**
- Create: `backend/app/knowledge/embeddings.py`
- Create: `backend/app/knowledge/index.py`
- Modify: `backend/app/providers/retrieval/base.py`
- Modify: `backend/app/providers/retrieval/local_keyword.py`
- Modify: `backend/app/providers/retrieval/chroma.py`
- Modify: `backend/app/providers/retrieval/__init__.py`
- Create: `backend/tests/test_chroma_retrieval.py`
- Modify: `backend/tests/test_providers.py`

- [ ] **Step 1: Write failing Chroma tests**

Use a real `chromadb.PersistentClient` under `tmp_path`. Test metadata preservation, Chinese `安全帽` retrieval, a nonsense query returning `[]`, reopening the same directory with the same result, and `clear()` removing the collection. Add a factory test for `Settings(retrieval_provider="chroma", chroma_dir=tmp_path)`.

- [ ] **Step 2: Run Chroma tests and confirm the expected failure**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_chroma_retrieval.py tests/test_providers.py -q
```

Expected: FAIL because the index methods and complete provider behavior are not implemented.

- [ ] **Step 3: Implement deterministic local embeddings and the index projection**

Implement a fixed-dimension character 2/3-gram hash vector normalized for cosine distance. `KnowledgeIndex` owns the `buildwise-standards` collection, calls `upsert` with stable clause IDs, stores scalar metadata for all required fields plus hazard types/keywords, and exposes `upsert`, `delete_all`, `query`, `count`, `metadata_snapshot`, and `stats`.

- [ ] **Step 4: Implement the provider and normalize local-provider output**

`ChromaRetrievalProvider` delegates to `KnowledgeIndex`, filters `hazard_type` after retrieval, clamps scores to `[0, 1]`, and returns empty evidence for blank/low-confidence queries. `LocalKeywordRetrievalProvider` returns the same result keys (`document_id`, `id`, `title`, `source`, `article`, `category`, `content`, `version`, `effective_date`, `score`, `metadata`).

- [ ] **Step 5: Run targeted provider and existing workflow tests**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_chroma_retrieval.py tests/test_providers.py tests/test_safety_workflow.py -q
```

### Task 3: Persist clause metadata and expose index/search service APIs

**Files:**
- Modify: `backend/app/models/entities.py`
- Create: `backend/alembic/versions/0003_knowledge_clause_metadata.py`
- Modify: `backend/app/schemas/knowledge.py`
- Modify: `backend/app/repositories/knowledge_repository.py`
- Modify: `backend/app/services/knowledge_service.py`
- Modify: `backend/app/api/v1/endpoints/knowledge.py`
- Modify: `backend/app/db/seed.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/tests/test_knowledge_api.py`

- [ ] **Step 1: Write failing API and persistence tests**

Test migration-backed `article` and `effective_date`, response fields `document_id`, `source`, `title`, `article`, `category`, `content`, `version`, `effective_date`, and `metadata`, `GET /knowledge/index/status`, provider-backed search, and `POST /knowledge/reindex`. Assert local no-hit remains `[]` and missing Chroma dependency returns a typed configuration error.

- [ ] **Step 2: Run the API tests and confirm the expected failure**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_knowledge_api.py -q
```

Expected: FAIL because the new schema fields, migration, status endpoint, and provider-backed search are missing.

- [ ] **Step 3: Add migration and repository mappings**

Add non-null `article` with an empty-string server default and nullable `effective_date` to `knowledge_documents`; keep existing `id` as stable `document_id`. Extend seed and repository upsert mapping without changing existing demo IDs.

- [ ] **Step 4: Implement provider-backed `KnowledgeService` operations**

Add `search_with_provider`, `index_status`, `reindex`, and `clear_index`. The service constructs the configured provider through `build_retrieval_provider(settings)`; endpoints only validate dependencies and serialize envelopes. Local mode remains JSON-backed; Chroma mode reads the persistent projection.

- [ ] **Step 5: Add status and reindex endpoints without changing existing paths**

Keep existing documents/search/create paths. Replace the placeholder `POST /knowledge/reindex` with the service call and add `GET /knowledge/index/status`; return additive fields in the existing envelope.

- [ ] **Step 6: Run migration, API, and existing backend tests**

Run:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m pytest tests/test_knowledge_api.py tests/test_reports.py tests/test_safety_persistence.py -q
```

### Task 4: Build the ingestion command and Docker persistence path

**Files:**
- Modify: `scripts/ingest_knowledge.py`
- Modify: `backend/Dockerfile`
- Modify: `docker-compose.yml`
- Modify: `backend/.env.example`
- Create: `backend/tests/test_ingest_command.py`

- [ ] **Step 1: Write a failing command test**

Invoke ingestion against a temporary JSON file twice and assert stable IDs do not increase clause count; invoke `--clear --rebuild` and assert the Chroma collection is rebuilt with the same count.

- [ ] **Step 2: Run the command test and confirm the expected failure**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_ingest_command.py -q
```

Expected: FAIL because the current script only runs seed and has no parser/index arguments.

- [ ] **Step 3: Implement the CLI**

Support these commands:

```powershell
python scripts/ingest_knowledge.py --input data_demo/standards/safety_standards.json
python scripts/ingest_knowledge.py --input path\to\standard.pdf --source "已授权来源" --title "文档标题" --category "施工安全" --version "2026" --effective-date 2026-01-01
python scripts/ingest_knowledge.py --rebuild
python scripts/ingest_knowledge.py --clear --rebuild
```

Print parsed, created, updated, skipped, parse-failure, provider, and collection-count results. Require `--rebuild` with `--clear`; never target SQLite or Docker volumes for deletion.

- [ ] **Step 4: Make Docker configuration explicit and persistent**

Pass `RETRIEVAL_PROVIDER=${RETRIEVAL_PROVIDER:-local_keyword}`, `CHROMA_DIR=${CHROMA_DIR:-storage/chroma}`, and `CHROMA_MIN_SCORE=${CHROMA_MIN_SCORE:-0.42}` to backend. Add a named `buildwise-chroma` volume at `/app/storage/chroma`, retain `buildwise-storage`, copy the ingestion script into the image, and keep local-keyword as default.

- [ ] **Step 5: Run command tests and local persistence check**

Run:

```powershell
.\venv\Scripts\python.exe -m pytest tests/test_ingest_command.py tests/test_chroma_retrieval.py -q
.\venv\Scripts\python.exe scripts\ingest_knowledge.py --input ..\data_demo\standards\safety_standards.json --rebuild
```

### Task 5: Update the knowledge page and frontend tests

**Files:**
- Modify: `frontend/src/api/knowledge.ts`
- Modify: `frontend/src/views/knowledge/KnowledgeBaseView.vue`
- Modify: `frontend/src/assets/main.css`
- Create: `frontend/src/views/__tests__/knowledgeBaseView.spec.ts`

- [ ] **Step 1: Write failing UI/API type tests**

Test the typed index-status contract and that the view renders provider, indexed state, document/clause counts, source/article, score, metadata, and the existing no-result message.

- [ ] **Step 2: Run the targeted frontend test and confirm the expected failure**

Run:

```powershell
cd E:\cc项目\buildwise-agent\frontend
npm run test:unit -- --run src/views/__tests__/knowledgeBaseView.spec.ts
```

Expected: FAIL because the API type and status UI do not exist.

- [ ] **Step 3: Implement the typed API and view**

Add `KnowledgeIndexStatus`, `KnowledgeSearchResult`, `knowledgeApi.indexStatus()`, and `knowledgeApi.reindex()`. Load status and search separately, display `local_keyword` or `chroma`, indexed state, counts, article numbers, scores, and a no-evidence message. Keep upload disabled because this phase adds the command, not browser upload.

- [ ] **Step 4: Run targeted and full frontend tests/build**

Run:

```powershell
npm run test:unit -- --run
npm run typecheck
npm run build
```

### Task 6: Documentation, Docker Chroma E2E, and final regression

**Files:**
- Modify: `README.md`
- Modify: `docs/algorithms.md`
- Modify: `docs/api.md`
- Modify: `docs/database.md`
- Modify: `scripts/e2e_docker.py`

- [ ] **Step 1: Document configuration and operations**

Document default local-keyword mode, Chroma variables, JSON/PDF/DOCX preparation rules, explicit source/title/category requirements for non-JSON files, incremental import, clear/rebuild, index status, Docker volumes, and the rule that only authorized documents may be imported. State that YOLO, external text, and voice remain unchanged.

- [ ] **Step 2: Run the default local regression**

Run:

```powershell
cd E:\cc项目\buildwise-agent
.\backend\venv\Scripts\python.exe -m pytest .\backend\tests -q
```

Expected: all tests pass and default provider remains local-keyword.

- [ ] **Step 3: Build and run the Chroma Docker configuration**

Use the existing SQLite volume and named Chroma volume:

```powershell
$env:RETRIEVAL_PROVIDER = "chroma"
docker compose build --no-cache
docker compose up -d
docker compose exec -T backend python scripts/ingest_knowledge.py --input data_demo/standards/safety_standards.json --rebuild
```

Verify health, index status, Chinese query results, no-hit empty evidence, container restart persistence, and the existing Docker E2E flow. Reset `$env:RETRIEVAL_PROVIDER` and restore local-keyword after the Chroma checks.

- [ ] **Step 4: Run the complete quality gate**

Run:

```powershell
cd E:\cc项目\buildwise-agent\backend
.\venv\Scripts\python.exe -m pytest -q
cd ..\frontend
npm run typecheck
npm run build
cd ..
docker compose config
python scripts/e2e_docker.py
```

Expected: backend tests, frontend checks, Compose config, local-keyword E2E, Chroma query/persistence checks, and Docker container checks all pass.

- [ ] **Step 5: Review the requirement checklist and report boundaries**

Confirm no YOLO, external LLM, voice, QualityAgent, or GreenAgent behavior changed; report exact files, commands, index counts, query samples, persistence evidence, and current provider boundaries.
