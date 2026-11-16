# AGENTS.md

KGBERS (Knowledge Graph based Education Recommendation System) — research-project Flask scaffold for a Chinese grant; UI text and seed data are Chinese ([prompts.txt](prompts.txt) describes intended modules). The app runs, pages render, and `pytest` is green (94 passed, 5 skipped). All grant modules (knowledge graph, learner modeling, course analysis, hybrid recommendation, UI, A/B evaluation) have working implementations, plus a lightweight adaptive-learning experiment (BKT + concept-graph propagation, no PyTorch/TensorFlow).

## Setup & commands

Python 3.9.

```bash
pip install -r requirements.txt          # runtime deps (heavy ML pins; may fail to build on some platforms)
pip install -r requirements-dev.txt      # test/CI deps only, no ML packages
FLASK_APP=run.py flask db upgrade        # create/upgrade schema via Alembic (dev/prod only)
python run.py                            # dev server on 0.0.0.0:5000
FLASK_APP=run.py flask seed-db           # idempotent: sample courses, prerequisites, demo user (demo/demo1234), KT interactions, KG seed if Neo4j up
FLASK_APP=run.py flask import-courses    # from COURSE_DATA_URLS or bundled sample; dedupes by title
FLASK_CONFIG=testing pytest tests        # single file: pytest tests/test_experiment.py -q
```

- Entrypoint is `run.py`, which calls `load_dotenv()` then `create_app(FLASK_CONFIG or "default")`. Valid `FLASK_CONFIG` values (`config.py`): `development` / `testing` / `production` / `default`→development.
- `create_app()` runs `db.create_all()` **only when `TESTING`** (app/__init__.py:61); dev/prod schema requires `flask db upgrade`. Under `TESTING` it also sets `WTF_CSRF_ENABLED=False`.
- CI (`.github/workflows/ci.yml`): installs `requirements-dev.txt` (not full `requirements.txt`, which fails to build on some platforms) → `compileall app run.py config.py` → `flask db upgrade` smoke → `pytest tests -q`.
- No linter/formatter/typecheck config; `compileall` is the only static check.
- Version pins matter: Flask 2.0.1 needs old Werkzeug/Jinja2/click (see `requirements-dev.txt`), and Flask-SQLAlchemy must stay at 2.5.1. Do not bump any of these casually.
- `Dockerfile` runs `gunicorn run:app` with `FLASK_APP=run.py`; there is no `wsgi.py`.

## Gotchas

- **Neo4j is optional but only partially degrades.** `get_neo4j_db()` (`app/utils/neo4j_utils.py`) reads `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` env vars (defaults `bolt://localhost:7687` / `neo4j` / `password`); `config.py` holds its own `NEO4J_*` values that services do not read. The knowledge-graph page route catches connection errors and renders an empty graph, but the concept JSON endpoints (`/knowledge_graph/concept/...`) do not — they 500 without Neo4j. KG score in recommendations is 0 when Neo4j is down.
- **Keep `CourseAnalysisService` lazily connecting** (`_get_knowledge_graph`); constructing the service must not connect to Neo4j, or tests break.
- **Test isolation is narrow**: `tests/conftest.py` monkeypatches `recommendation_service.get_neo4j_db` and `concept_graph_service.get_neo4j_db` to raise. Any new service/module you add that touches Neo4j needs its own mock/patch in tests (KG tests use `MagicMock`).
- The `app` fixture drops and recreates tables per test on `data/sqlite/test.db` (override with `TEST_DATABASE_URL`); dev DB is `data/sqlite/app.db`. `data/` is gitignored and auto-created.
- Flask-SQLAlchemy 2.5.1 API in use: `Query.paginate` (course_routes.py:28). Flask-SQLAlchemy 3.x removes it and breaks the course list route.
- Heavy ML deps are declared in `requirements.txt` but only gensim/nltk/jieba are used, and only when `requirements-ml.txt` is installed (then `TopicModelService` uses gensim LDA → sklearn LDA → frequency keyword fallback; `TOPIC_MODEL_BACKEND` env var forces one backend). The hybrid recommender is pure Python. LDA tests skip when gensim/sklearn are missing.
- **CSRF is enforced by Flask-WTF in all non-testing configs.** New POST/PUT/DELETE forms and JS fetches must send the token (`base.html` exposes it via a `csrf-token` meta tag; `scripts.js` reads it).
- A/B testing: `for_you` assigns a deterministic `control`/`treatment` variant server-side and records deduped impressions; `submit_feedback` ignores any client-supplied `variant`. Clicks report via `POST /recommendation/recommendations/click/<id>`; report page `GET /recommendation/recommendations/experiments/report` or CLI `flask experiment-report`. Reports include impressions/clicks/CTR, ratings, and completion counts/rate from `Interaction(event_type='complete')`. All experiment write/report endpoints accept `?experiment=<name>` (default `recommendation`) — pass it through on every request in a flow, otherwise metrics land in the default experiment.
- Adaptive learning experiment (`?experiment=adaptive_kt`): `control` uses the existing hybrid recommender + the same explanation fields, `treatment` uses `AdaptiveRecommendationService`; it does **not** replace the default recommender. Interactions are written via `POST /recommendation/recommendations/interaction` (`event_type=answer|complete`, plus `experiment`/`variant`). `complete` does not update BKT mastery; completion state is the union of `Recommendation` and `Interaction(event_type='complete')` via `completion_service.completed_course_ids()`, and is used by recommendation exclusion + learning path. Mastery is direct BKT + concept-graph propagation; Neo4j only adds `HAS_TOPIC` nodes (batched, failure → 60s backoff → course/category/prereq/title-token graph only).
- Keep the adaptive stack **pure Python** (`numpy`/`scipy` are available but not required by these services). Do not add PyTorch/TensorFlow for knowledge tracing; the paper-inspired implementations are BKT + iterative label propagation, and tests rely on them running without heavy ML deps.

## Adaptive learning (BKT + concept graph)

- `knowledge_tracing_service.py` — BKT posterior update + learning transition, 30-day half-life decay; `record_interaction()` writes `Interaction` and upserts `KnowledgeState` in one commit. `event_type='complete'` skips BKT.
- `completion_service.py` — `completed_course_ids()` unions legacy `Recommendation` rows with `Interaction(event_type='complete')`; use it instead of querying `Recommendation` directly for completion/exclusion.
- `concept_graph_service.py` — builds course/category/`Topic_*` graph (topics from Neo4j `HAS_TOPIC`, one batched query) plus title-token co-occurrence edges, symmetrizes edges, runs `S ← (1-α)S + α·A_norm·S` for 6 iterations; `course_readiness()` returns mastery/gap/prerequisite readiness. Uses `selectinload(Course.prerequisites)` and a 60s Neo4j failure backoff (`reset_neo4j_backoff()` for tests).
- `adaptive_recommendation_service.py` — `final = 0.6·baseline + 0.4·adaptive`; adaptive = 0.45·mastery_gap + 0.30·prereq_readiness + 0.15·ZPD + 0.10·difficulty_fit. Constant `ADAPTIVE_EXPERIMENT = "adaptive_kt"`; `add_explanations()` keeps control/treatment UI identical.
- `learning_path_service.py` — same-level ordering now prefers lower mastery (`_sort_key`); `path_for_user` attaches `mastery`/`mastery_gap` from `course_readiness()` and completion from `completed_course_ids()`.
- References: Corbett & Anderson (1995) BKT; Nakagawa et al. (2019) Graph-based Knowledge Tracing; Han et al., *Contrastive Cross-Course Knowledge Tracing via Concept Graph Guided Knowledge Transfer* (IJCAI 2025, arXiv:2505.13489) for cross-course transfer.
- Migration head is `e3f4a5b6c7d8` (`interaction.experiment`/`variant`); `d2e3f4a5b6c7` adds `interaction.event_type`; `c1d2e3f4a5b6` adds `interaction` / `knowledge_state`.

## Layout

- `app/__init__.py` — `create_app()` + shared `db`, `migrate`, `csrf`, `login_manager`, `bootstrap` singletons; registers `user_loader` and CLI commands.
- `app/commands.py` — CLI: `seed-db`, `import-courses`, `experiment-report`.
- `app/models/` — Flask-SQLAlchemy models (`User`, `Course` with self-referential `prerequisites`, `Recommendation`, `Interaction`/`KnowledgeState`, `ExperimentAssignment`/`Feedback`/`RecommendationEvent`, all with `save()`/`delete()` where applicable) plus `KnowledgeGraph` (a py2neo wrapper; serializes nodes/links for d3). Import models via `app/models/__init__.py`.
- `app/routes/` — blueprints: `main` (no prefix), `user` (`/user`), `course` (`/course`), `recommendation` (`/recommendation`), `knowledge_graph` (`/knowledge-graph`).
- `app/services/` — `recommendation_service.py` (hybrid: content 0.5 / rating 0.3 / KG 0.2), `completion_service.py` (completion/exclusion union), `knowledge_tracing_service.py` (BKT), `concept_graph_service.py` (course/category/topic graph propagation), `adaptive_recommendation_service.py` (`adaptive_kt` treatment), `learning_path_service.py` (prereq topo-sort + mastery ordering), `experiment_service.py` (A/B + feedback + report, multi-experiment), `topic_modeling_service.py` (LDA/fallback), `course_import_service.py` (JSON + CSV, alias normalization), `course_analysis_service.py`, `user_modeling_service.py` (`UserService`, alias `UserModelingService`).
- `app/samples/mooc_courses.json` — bundled offline course data used as the import fallback.
- `app/utils/` — `neo4j_utils.py`, `sqlite_utils.py`; plus `app/templates/`, `app/static/`; `migrations/` — Alembic (head `d2e3f4a5b6c7`; `c1d2e3f4a5b6` adds adaptive tables).

## Known gaps (verify before trusting)

- `app/templates/user_profile.html` is unused (the profile route renders `profile.html`, user_routes.py:56); `scripts.js` `addRecommendation` has no triggering button.
- `app/utils/sqlite_utils.py` builds SQL via f-strings — unused by routes, but a SQL-injection risk if ever wired up.

## Docs

- `prompts.txt` — original grant brief (Chinese); intent source, not accurate current state.
- `README.md`, `TODO.md`, `file_structure.md`, and this file are the current, accurate project docs.
