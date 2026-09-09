# Observability Conventions

Use this guide when adding backend telemetry. Operator configuration lives in [`../environment.md`](../environment.md); the decision to use Sentry is recorded in [`../agents/decisions/003-opt-in-sentry-observability.md`](../agents/decisions/003-opt-in-sentry-observability.md).

Observability is off by default. When disabled, the facade skips SDK calls and network activity.

## Use the facade

Application code imports only from `blunder_tutor.observability`:

```python
from blunder_tutor.observability import count, distribution, gauge, start_span
```

Do not import `sentry_sdk` directly. `background/scheduler.py` is the one application-level exception because Sentry Crons has no facade primitive. `tests/test_observability_boundaries.py` enforces the allowlist.

Do not add `if observability_enabled` checks at call sites. The facade handles disabled mode.

## Pick one signal

| Need | Signal |
|---|---|
| Timing and context for one operation | Span |
| Aggregate count, latency, or current value | Metric |
| Operator-readable event or failure | Log |

Instrument shared chokepoints, not every helper. Avoid recording the same fact in several layers.

Unhandled errors should normally propagate to an instrumented boundary. Log or raise unless duplicate reporting is intentional; doing both can create duplicate Sentry events.

## Metrics

Metric names use `<area>.<event>` and optional unit suffixes:

```python
count("job.started", tags={"kind": job_kind})
distribution("job.duration_ms", elapsed_ms, tags={"kind": job_kind})
gauge("ws.connections.active", len(connections))
```

`count` defaults to `1.0`. Pass a value only when one call represents several events.

### Tags must be bounded

A metric tag is allowed only when its possible values form a small, reviewable set.

| Good metric tag | Not a metric tag |
|---|---|
| job kind from the runner registry | user ID |
| `ok`, `error`, `timeout`, `cancelled` | job or request ID |
| `EventType` value | FEN, PGN, path, username, or error message |
| fixed disconnect reason | timestamps or arbitrary input |

Unbounded values create one time series per value and may leak user data into long-retention storage. Put useful operation-specific context on a span with `set_data`; omit sensitive values entirely.

When a tag accepts a string from a caller, validate or map it to a fixed set before emission.

## Spans

```python
with start_span("engine.analyse", op="chess.engine") as span:
    span.set_tag("depth", limit.depth)
    span.set_data("job_id", job_id)
    result = await run_analysis()
```

The public span API is limited to `set_tag` and `set_data`. Extend the facade if another operation is needed; do not reach through it to Sentry.

Span attributes may be high-cardinality, but they are still transmitted. Do not attach passwords, tokens, cookies, invite codes, request bodies, PGN, FEN, email addresses, or other content that is unnecessary to debug the operation.

## Logging

Use module loggers and Python's lazy formatting:

```python
logger.info("Job %s started", job_id)
logger.exception("Game sync failed for job %s", job_id)
```

Never log secrets or rely on the scrubber to make an unsafe message safe. Scrubbing is key-based and cannot reliably remove sensitive values embedded in formatted text.

Use `extra={...}` only when a log consumer needs structured fields. Field names are part of the telemetry contract; do not add arbitrary request data or duplicate values already present on the active span.

## Privacy

Sentry's default denylist is extended in `observability/scrubbing.py` for the session cookie, secret key, invite code, and CSRF token. `SENTRY_SEND_DEFAULT_PII` is false by default.

These are backstops, not permission to send user data. Before adding telemetry, ask:

1. Is this value required to diagnose the failure?
2. Is it bounded enough for a metric tag?
3. Could it contain credentials, identity, or chess-game content?
4. Can a less specific value answer the same question?

## Current instrumentation

| Chokepoint | Signals |
|---|---|
| `EnginePool._handle_task` | `engine.analyse` span; completion and duration metrics |
| `JobExecutor._execute_job` | job transaction; started, completed, and duration metrics |
| `_fanout_tick` | Sentry Cron check-in |
| `ConnectionManager` | connection, active gauge, broadcast, and broadcast-error metrics |

The implementation is the source of truth for exact names and tags:

- `analysis/engine_pool.py::_emit_engine_telemetry`
- `background/executor.py::_emit_job_completion`
- `events/websocket_manager.py`

Do not maintain a second exhaustive metric registry in this document.

## Tests

Facade and lifecycle behavior:

```bash
uv run pytest tests/test_observability_facade.py \
  tests/test_observability_init.py \
  tests/test_observability_lifecycle.py \
  tests/test_observability_boundaries.py -v
```

Instrumentation tests use `tests/helpers/observability.py::patch_facade` to patch the primitives imported by the target module. Test the contract at the call site; do not test Sentry internals.

For a new chokepoint, leave one smoke test that checks:

- span name and operation, if any;
- metric names;
- the complete bounded tag set;
- success and relevant failure outcomes;
- absence of user IDs and job IDs in metric tags.

Run the focused instrumentation test and then the full suite.

## Review checklist

- Imports go through the facade.
- Instrumentation is at one shared chokepoint.
- Metric names follow the existing area.
- Every tag has a finite set of values.
- Sensitive content is not emitted, even on spans or logs.
- Exceptions are not reported twice accidentally.
- Disabled mode remains safe.
- A smoke test pins the telemetry contract.
