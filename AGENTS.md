# AGENTS.md

KGBERS (Knowledge Graph based Education Recommendation System) — a research-project Flask scaffold for a Chinese grant. The app runs, pages render, and `pytest` is green (48 passed, 1 skipped). All modules from `prompts.txt` (knowledge graph, learner modeling, course analysis, hybrid recommendation, UI, A/B evaluation) have working implementations.

## Setup & commands

Python 3.9 (pins in `requirements.txt` target it).

```bash
pip install -r requirements.txt          # runtime deps (includes heavy ML packages)
FLASK_APP=run.py flask db upgrade        # create/upgrade schema via Alembic (dev/prod)
python run.py                            # dev server on 0.0.0.0:5000
FLASK_APP=run.py flask seed-db           # sample courses, prerequisites, demo user (demo/demo1234)
FLASK_APP=run.py flask import-courses    # import from COURSE_DATA_URLS or bundled sample
FLASK_CONFIG=testing pytest tests        # 48 pass, 1 skip (LDA skip without requirements-ml)
```

- Entrypoint is `run.py`, which loads `.env` (`load_dotenv()`) and calls `create_app(FLASK_CONFIG or "default")`. Config in `config.py`.
- `create_app()` runs `db.create_all()` **only when `TESTING`**; dev/prod schema comes from `flask db upgrade`. It also registers `login_manager.user_loader` and the CLI commands in `app/commands.py`.
- CI (`.github/workflows/ci.yml`) installs `requirements-dev.txt` (not full `requirements.txt`, which fails to build on some platforms), runs `compileall`, `flask db upgrade`, then `pytest`.
- No linter/formatter/typecheck config. `compileall` is the only static check.
- `Dockerfile` uses `FLASK_APP=run.py` + `CMD gunicorn run:app`. There is no `wsgi.py`.

## External services & data

- Neo4j is optional. `get_neo4j_db()` in `app/utils/neo4j_utils.py` reads `NEO4J_URI`/`NEO4J_USER`/`NEO4J_PASSWORD` (defaults `bolt://localhost:7687` / `neo4j` / `password`). `config.py`'s `NEO4J_*` values are not used by services. KG features degrade when Neo4j is down (empty graph / zero KG score); the knowledge-graph route catches connection errors.
- `CourseAnalysisService` initializes the Neo4j graph **lazily** (`_get_knowledge_graph`) so constructing the service does not connect. Keep it that way — eager connection breaks tests.
- SQLite DB path is `data/sqlite/app.db` (test: `data/sqlite/test.db` via `TEST_DATABASE_URL`); `data/` is gitignored and the dir is auto-created.
- Pagination uses Flask-SQLAlchemy 2.5.1's `Query.paginate`; a newer Flask-SQLAlchemy (3.x) removes it and breaks the course list route.
- Tests never touch real Neo4j: `tests/conftest.py` monkeypatches `recommendation_service.get_neo4j_db` to raise. LDA tests are skipped without `requirements-ml.txt`.

## Layout

- `app/__init__.py` — `create_app()` + shared `db`, `migrate`, `login_manager`, `bootstrap` singletons.
- `app/commands.py` — CLI: `seed-db` (idempotent sample data; KG seeding skipped if Neo4j unreachable), `import-courses`, `experiment-report`.
- `app/models/` — Flask-SQLAlchemy models (`User`, `Course` with self-referential `prerequisites`, `Recommendation`, `ExperimentAssignment`/`Feedback`/`RecommendationEvent`, all with `save()`/`delete()` where applicable) plus `KnowledgeGraph` (a py2neo wrapper; serializes nodes/links for d3). Import models via `app/models/__init__.py`.
- `app/routes/` — blueprints: `main` (no prefix), `user` (`/user`), `course` (`/course`), `recommendation` (`/recommendation`), `knowledge_graph` (`/knowledge-graph`).
- `app/services/` — `recommendation_service.py` (hybrid recommender), `learning_path_service.py` (prereq topo-sort), `experiment_service.py` (A/B + feedback + report), `topic_modeling_service.py` (LDA/fallback), `course_import_service.py`, `course_analysis_service.py`, `user_modeling_service.py` (`UserService`, alias `UserModelingService`).
- `app/samples/mooc_courses.json` — bundled offline course data used as the import fallback.
- `app/utils/` — `neo4j_utils.py`, `sqlite_utils.py`; `app/templates/` + `app/static/`; `migrations/` — Alembic baseline.

## Known gaps (verify before trusting)

- `CourseAnalysisService.fetch_course_data` reads `COURSE_DATA_URLS` and falls back to the bundled sample; `_perform_topic_modeling` uses `TopicModelService` (gensim LDA if installed, else frequency keywords).
- The hybrid recommender is pure Python and Neo4j-optional; numpy/pandas/scikit-learn/gensim/nltk are declared deps but only gensim/nltk are used, and only when `requirements-ml.txt` is installed.
- A/B testing: `for_you` assigns a deterministic `control`/`treatment` variant (server-side; feedback ignores any client-supplied variant) and records deduped impressions; clicks are reported via `POST /recommendation/recommendations/click/<id>`; feedback is submitted via the `for_you` form.
- CSRF is enforced by Flask-WTF `CSRFProtect` in non-testing configs (`WTF_CSRF_ENABLED=False` under `TESTING`). New POST/PUT/DELETE forms and JS fetches must send the token (`base.html` exposes it via a `csrf-token` meta tag; `scripts.js` reads it).
- `app/templates/user_profile.html` is unused (route renders `profile.html`); `scripts.js` `addRecommendation` has no triggering button.
- `app/utils/sqlite_utils.py` builds SQL via f-strings (unused by routes, but unsafe if wired up).

## Docs to distrust

- `prompts.txt` is the original grant brief (Chinese) describing intended modules.
- `README.md`, `TODO.md`, `file_structure.md`, and this file are the current, accurate project docs.
