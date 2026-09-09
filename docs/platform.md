# Backend Platform Guide

This document covers the application plumbing shared by web requests and background work. For the product-level view and data flows, see [`architecture/overview.md`](architecture/overview.md).

Blunder-Tutor is one FastAPI process with process-local scheduling, jobs, events, cache, WebSockets, and Stockfish coordination. The platform code optimizes for a self-hosted deployment, not horizontal scaling.

## Startup and shutdown

`blunder_tutor/web/app.py` is the public app factory. Construction and lifecycle wiring live in `web/app_lifecycle.py`.

At construction, the app creates shared state, templates, static-file serving, middleware, and routes. During lifespan startup it:

1. initializes optional observability;
2. starts the Stockfish `WorkCoordinator`;
3. initializes credentials-mode authentication when enabled;
4. wires and starts the job executor and scheduler;
5. starts WebSocket broadcasting and cache invalidation.

Shutdown reverses ownership: background consumers stop, the scheduler and engine pool shut down, database resources close, and observability flushes.

Resources started by lifespan must also be stopped there. Do not start process-lifetime tasks from route modules.

## Configuration

`web/config.py` builds one validated `AppConfig` from CLI arguments and environment variables. Related values are grouped into Pydantic models for data, engine, auth, throttling, analytics, cache, and observability.

Add configuration only when deployment needs to vary a value:

1. add it to the relevant config model;
2. parse its environment value in `config_factory` or the existing sub-builder;
3. validate unsafe combinations in the model;
4. pass the config object through DI or `app.state` rather than reading `os.environ` in feature code;
5. document operator-facing variables in [`environment.md`](environment.md).

## Request context and middleware

Middleware establishes security and per-request state before handlers run:

- credentials auth or the local-user bypass sets `request.state.user_ctx`;
- `UserDbPathMiddleware` resolves that user to an application database;
- `LocaleMiddleware` supplies locale, translations, and feature flags;
- setup and demo middleware gate access;
- CSRF origin, trusted-host, and security-header middleware protect the HTTP boundary.

Middleware registration order is reverse execution order in Starlette. Change `_register_middleware()` only with tests for early returns as well as successful requests; authentication, CSRF, user database selection, and response headers depend on ordering.

`AUTH_MODE=none` uses one local database. `AUTH_MODE=credentials` uses `auth.sqlite3` for identities and sessions plus one application database per user. Code that handles application data must use the resolved request path, never the configured legacy path directly.

## Dependency injection

The application has two adapters over the same repositories and services:

| Caller | Module | Context source |
|---|---|---|
| FastAPI route | `web/dependencies.py` | `Request`, `app.state`, and `request.state.user_db_path` |
| Background runner | `core/dependencies.py` | task-local `DependencyContext` stored in a `ContextVar` |

Repository factories use `async with` so connections close after the request or runner. Route annotations such as `SettingsRepoDep` keep handlers readable. Background `@inject` runners provide the same cleanup outside FastAPI.

When adding a dependency, expose it only in the adapter that needs it. Add it to both modules only when both request and job code use it.

## SQLite and repositories

`repositories/base.py` provides:

- a lazily opened aiosqlite connection;
- one in-process write lock per resolved database path;
- commit/rollback through `write_transaction()`;
- async context-manager cleanup.

Application SQL belongs in repositories. Expected exceptions are Alembic migrations and the isolated auth storage package.

The write lock coordinates tasks in one process; it does not coordinate multiple Uvicorn workers. SQLite plus process-local jobs and events are why production runs one application worker.

### Schema changes

Application migrations live in `alembic/versions/` and run through `blunder_tutor/migrations.py`. A legacy database containing `game_index_cache` but no Alembic version is stamped at revision `001` before upgrading. Credentials storage has a separate schema in `auth/storage_sqlite/schema.py`.

No-auth startup migrates the configured application database, and registration migrates a new credentials-mode user database. Startup does not currently walk and upgrade existing `users/<id>/main.sqlite3` files; credentials-mode deployments need an explicit migration step for those databases when the schema changes.

For a new persisted feature, update:

1. the migration;
2. its repository;
3. account deletion and any relevant data-wipe path;
4. cache invalidation, if reads are cached;
5. migration and repository tests.

## Background work

The execution path is:

```text
API or scheduler
  → job.execution_requested event
  → JobExecutor
  → task-local DependencyContext
  → @inject runner in background/runners.py
  → job class
```

`JobExecutor` is process-wide and resolves the target user's database before dispatch. Most user-triggered work creates a persisted row through `JobService` before publishing; scheduled rating-stat sync uses a synthetic ID and no job row. Jobs own use-case sequencing; runners own dependency construction.

To add a job:

1. add its stable type constant in `constants.py`;
2. implement the job under `background/jobs/`;
3. add an injected runner and `JOB_RUNNERS` entry in `background/runners.py`;
4. create the job through `JobService` before publishing its execution request;
5. test lifecycle, user isolation, cancellation, and failure behavior that applies.

The decorator registry in `background/registry.py` is not the executor dispatch table; `JOB_RUNNERS` is.

`BackgroundScheduler` is a single interval-driven fan-out scheduler backed by APScheduler's memory store. Each tick enumerates users and checks per-user profile settings before publishing game or rating-stat sync work. Schedules and queued/running tasks do not survive restart.

## Events, WebSockets, and cache

`EventBus` is in-memory pub/sub with one unbounded `asyncio.Queue` per subscriber. `ConnectionManager` forwards subscribed events to WebSockets and coalesces noisy updates. `CacheInvalidator` maps data-change events to user-scoped cache tags, then publishes a cache-invalidated event so clients can refresh.

Use events for same-process coordination and UI refresh, not durable delivery. Events published before subscription are lost, subscriber queues are unbounded, and a restart clears them. Consumers must recover from persisted database state. Tenant-specific events must carry scope; job lifecycle events are currently unscoped.

The response cache has in-memory and null backends. `@cached` routes require `set_request_scope`, and keys include the user scope and an explicit version. Setup, locale, and feature snapshots use separate per-user caches.

When adding a cached aggregate:

1. use `@cached` with a registered logical tag, TTL, and version;
2. publish a bounded event type when its source data changes;
3. carry the user scope on data-change events;
4. add the event-to-tag mapping in `cache/invalidation.py`;
5. test that one user's mutation cannot clear or broadcast another user's data.

Do not put user IDs, job IDs, or other unbounded values in metric tags. See [`conventions/observability.md`](conventions/observability.md).

## Authentication and security boundaries

`blunder_tutor/auth/` owns credentials, password hashing, sessions, invite policy, and auth persistence. Application-specific filesystem behavior stays in `web/auth_hooks.py`: creating a user's database, removing their directory, and clearing per-user caches.

Keep validation and protection at trust boundaries:

- validate host, origin, cookies, request payloads, usernames, PGN, and FEN;
- require an explicit host allowlist, secure-cookie posture, and strong secret for exposed credentials-mode deployments;
- trust proxy headers only behind a proxy that overwrites them;
- keep in-memory login/signup rate limits separate from demo-mode engine throttling;
- avoid logging secrets, cookies, PGN content, email addresses, or raw user input to Sentry.

## Routes and frontend

`web/routes.py::configure_router` is the HTTP composition point; do not mirror its router list in documentation. Jinja2 renders page shells and Vite builds TypeScript/Preact entry points. Production asset lookup uses the generated manifest through `web/vite.py`; a new entry point must be added to `ENTRY_MAP` and included in a successful `npm run build`.

## Testing

`tests/conftest.py` supplies migrated temporary databases, a default `AppConfig`, repository fixtures, and a full `TestClient`. `tests/helpers/engine.py` isolates tests from a real Stockfish process. Credentials-mode tests use dedicated auth fixtures under `tests/auth/`.

Use the narrowest check that covers the change, then run the full suite before completion:

```bash
uv run pytest tests/path/to/test_file.py -v
uv run pytest tests/ -v
make fix
```

Tests run with event coalescing disabled by default for deterministic delivery and with Sentry disabled. Tests for those facilities opt in explicitly.

## Deployment limits

The Docker image builds the TypeScript frontend and Stockfish, installs the Python application, runs migrations, and starts one Uvicorn worker as a non-root user. Compose persists `/app/data` through a bind mount.

Do not add multiple workers without first replacing or coordinating all process-local state: scheduler leadership, job execution, event delivery, cache, write locks, and the engine pool.

## What does not belong here

Chess analysis, fetchers, trainer behavior, concrete jobs, and product APIs are domain code, not reusable platform infrastructure. Avoid maintaining a hypothetical cookiecutter file tree in this repository; extract a template only when a second application proves which pieces are actually reusable.
