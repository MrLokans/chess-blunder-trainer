# Architecture

Blunder-Tutor imports a player's games from Lichess, Chess.com, or PGN files, analyzes them with Stockfish, and turns mistakes into training puzzles. It is a self-hosted FastAPI application designed to run as one process.

## Runtime view

```text
Browser
  │ HTTP + WebSocket
  ▼
FastAPI ── routes ── services/jobs ── repositories ── SQLite
  │                         │
  │ HTTPS                   └── WorkCoordinator ── UCI ── Stockfish
  ▼
Lichess / Chess.com
```

The process also owns an APScheduler instance, an in-memory event bus, a tagged response cache, a WebSocket broadcaster, and the Stockfish process pool. These are not separate services.

This single-process boundary matters: the scheduler, job executor, event bus, cache, and engine coordinator are process-local. Running multiple web workers would duplicate scheduled work and split events and cache state between workers.

## Technology

| Area | Implementation |
|---|---|
| Backend | Python 3.14+, FastAPI, Uvicorn |
| Frontend | TypeScript, Preact islands, Vite, Jinja2 page shells |
| Data | SQLite, aiosqlite, Alembic |
| Chess | python-chess, Stockfish over UCI |
| Background work | APScheduler and asyncio tasks in the web process |
| Dependency injection | FastAPI `Depends` for requests; FastDepends plus `ContextVar` for jobs |
| Observability | Optional Sentry traces, metrics, and logs |

The application starts through `main.py` → `blunder_tutor/cli/main.py`. The `train-ui` command builds the app in `blunder_tutor/web/app_lifecycle.py` and starts Uvicorn.

## Storage and users

There are two deployment modes:

- `AUTH_MODE=none`: one local user and one database, `data/main.sqlite3` by default.
- `AUTH_MODE=credentials`: accounts and sessions live in `data/auth.sqlite3`; each user gets `data/users/<user-id>/main.sqlite3`.

`UserDbPathMiddleware` selects the user database for each request. `JobExecutor` uses the same resolver for background work. The Stockfish pool, event bus, and cache remain shared process resources; database content is per user.

Application schema changes belong in `alembic/versions/`. Authentication has its own schema in `blunder_tutor/auth/storage_sqlite/schema.py`. Those files, not a table list in this document, are the schema source of truth.

## Code map

| Path | Owns |
|---|---|
| `blunder_tutor/web/` | App lifecycle, middleware, HTML routes, REST API, WebSocket endpoint |
| `frontend/src/` | Preact islands and shared browser code; Vite emits assets served by FastAPI |
| `templates/` | Jinja2 page shells and non-island markup |
| `blunder_tutor/auth/` | Credentials, sessions, invite setup, auth middleware, auth SQLite storage |
| `blunder_tutor/services/` | Use-case orchestration for puzzles, jobs, SRS, backfills, and ratings |
| `blunder_tutor/background/` | Scheduler, executor, runner registry, and job implementations |
| `blunder_tutor/fetchers/` | Lichess, Chess.com, and filesystem PGN ingestion |
| `blunder_tutor/analysis/` | Engine pool, analysis pipeline, move classification, phases, tactics, traps, and ECO |
| `blunder_tutor/repositories/` | Per-user SQLite queries and transactions |
| `blunder_tutor/events/` | In-process pub/sub, event types, coalescing, and WebSocket fan-out |
| `blunder_tutor/cache/` | In-memory tagged cache and event-driven invalidation |
| `blunder_tutor/observability/` | Optional Sentry integration and its privacy/cardinality rules |
| `blunder_tutor/i18n/` and `locales/` | Translation lookup and locale data |
| `blunder_tutor/trainer.py` | Puzzle selection and filtering |
| `blunder_tutor/srs.py` | Pure Leitner scheduling rules |

For frontend conventions see [`docs/development/frontend.md`](../development/frontend.md). For observability conventions see [`docs/conventions/observability.md`](../conventions/observability.md).

## Main flows

### Import and sync

1. A request or scheduler tick creates a job and publishes `job.execution_requested`.
2. `JobExecutor` resolves the target user's database and runs the matching function from `background/runners.py`.
3. The job fetches or parses PGN, builds game metadata, assigns a game ID, and writes through repositories. Platform fetches hash normalized PGN; manual imports and filesystem manifests have their own ID paths.
4. If automatic analysis is enabled, the sync job publishes an analysis request.
5. Job and data-change events update WebSocket clients and invalidate tagged cache entries.

Profiles, rather than global usernames, are the current unit of platform tracking. A profile stores platform identity and sync preferences; rating snapshots are stored separately.

### Analysis

1. `AnalyzeGamesJob` finds unanalyzed games and submits one callable per game to the shared `WorkCoordinator`.
2. `GameAnalyzer` runs `AnalysisPipeline` for each game.
3. The full preset requests `eco`, `stockfish`, `move_quality`, `phase`, `traps`, and `write`. Dependencies add `tactics` because `write` requires it; only declared dependencies determine order.
4. The shared job path injects an engine from `EnginePool`; the Stockfish step can start and close one engine when run standalone.
5. Completed step IDs are recorded so backfills can skip existing work or rerun selected steps.

### Training

1. `GET /api/puzzle` asks `PuzzleService` for a filtered blunder from `Trainer`.
2. The API returns the position, played move, best move, evaluation, and explanation data.
3. `POST /api/submit` validates the move, optionally evaluates it with Stockfish, records the attempt, and updates SRS state.
4. Failed discovery attempts enroll a card. Due reviews follow the fixed `1/3/7/16/35`-day Leitner ladder; eight lifetime failures suspend a card.
5. A training event invalidates affected aggregates and prompts subscribed clients to refresh.

### Browser-side game review

The game review island loads the vendored single-threaded Stockfish WASM worker when `review.engine` is enabled. It does not use the server engine or persist explored variations.

## Rules worth preserving

- Treat external usernames, PGN, FEN, cookies, and request payloads as untrusted input.
- Route per-user work through the request/job database-path resolver; never fall back to the shared local database in credentials mode.
- Use repositories for application-data SQL. Migration code and the isolated auth storage package are the expected exceptions.
- Use the shared `WorkCoordinator` for concurrent server-side engine work. Keep standalone engine ownership inside the Stockfish pipeline step.
- Publish bounded event types from `events/event_types.py`; user-specific data-change events must carry a user scope. Job lifecycle events are currently unscoped and can reach every subscribed credentials-mode connection.
- Keep the app single-process unless scheduler leadership, jobs, pub/sub, cache, and engine coordination are moved to shared infrastructure.
- Add user-visible text through the translation files, not inline in templates or browser code.
- When adding persisted user data, update account deletion, any relevant data-wipe path, and cache cleanup.

These are runtime constraints, not a claim that package imports form a perfectly layered graph. For example, repositories currently use web configuration in `BaseDbRepository.from_config`, and events use shared time and observability helpers.

## Where to make a change

| Change | Start here |
|---|---|
| New API or page | `blunder_tutor/web/routes.py`, then the relevant `web/api/` or `web/ui/` module |
| New frontend island | `frontend/src/`, its Jinja2 mount point, and Vite entries |
| New stored data | Alembic migration, repository, deletion path, and tests |
| New job | `background/jobs/`, `background/runners.py`, and job-type constants |
| New analysis enrichment | Pipeline step, preset/backfill wiring, persistence, and step-status handling |
| New event-backed aggregate | Event type, publisher, cache tag/invalidation, and WebSocket scope |
| New auth behavior | `blunder_tutor/auth/`; filesystem and app-specific hooks stay in `web/auth_hooks.py` |

## Maintenance

Update this overview only when a system boundary, storage topology, primary flow, or hard runtime constraint changes. Do not copy endpoint, module, table, feature-flag, or environment-variable inventories here; they go stale faster than their source files.

When changing architecture diagrams, follow [`docs/diagrams/how-to-diagram.md`](../diagrams/how-to-diagram.md).
