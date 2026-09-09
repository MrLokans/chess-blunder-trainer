# IMPORTANT, MUST FOLLOW

DO NOT create meaningless comments, i.e. comments that duplicate the function name. Percentage of methods covered with comments should generally be lower than 10%.
DO NOT provide typing info, return type info and exceptions in docstrings, use typing for that.

## Project Overview

Blunder-Tutor is a chess training application that fetches games from Lichess and Chess.com, analyzes them with Stockfish to identify blunders, and provides a training interface to practice those positions. For system context, components, data flows, boundaries, and architectural decisions see [`docs/architecture/overview.md`](docs/architecture/overview.md). For creating or updating architecture diagrams see [`docs/diagrams/how-to-diagram.md`](docs/diagrams/how-to-diagram.md).

## Issue Tracking

This project uses **Trekker** for issue tracking. CLI commands work for any LLM agent.

**Quick reference:** `trekker ready` (find work), `trekker search "<keyword>"`, `trekker task show <id>`, `trekker task update <id> --status in-progress|completed`.

**Workflow:** `trekker ready` → find issue → `update --status in-progress` → follow steps, `uv run pytest tests/ -v` after each, `make fix` → `update --status completed`. When adding new work: analyze codebase first, break into verifiable steps, consider localStorage/DB persistence and data-wipe cleanup.


## Guides

- Browser automation and screenshots: [`docs/development/agent-browser.md`](docs/development/agent-browser.md)
- Debugging game analysis, classifications, and eval swings: [`docs/development/debugging-game-analysis.md`](docs/development/debugging-game-analysis.md)
- Writing tests: [`docs/development/writing-tests.md`](docs/development/writing-tests.md)
- Cross-cutting feature gotchas: [`docs/development/common-gotchas.md`](docs/development/common-gotchas.md)
- Frontend development: [`docs/development/frontend.md`](docs/development/frontend.md)
- Backend lifecycle, DI, jobs, storage, and runtime limits: [`docs/platform.md`](docs/platform.md)
- Translations and locale handling: [`docs/i18n.md`](docs/i18n.md)
- Metrics, spans, logging, and telemetry privacy: [`docs/conventions/observability.md`](docs/conventions/observability.md)


## Common Commands

For the full target list run `make help`. Beyond that, these are the gotchas not derivable from the Makefile:

```bash
# Run a single test
uv run pytest tests/test_file.py::test_name -v

# Start the app (default localhost:8000)
uv run python main.py

# Credentials-mode E2E auth flow — the built-in webServer rebuilds the Vite
# manifest AND wipes the tmp DB on each run (surprising side effects):
cd e2e && npx playwright test --config playwright.auth.config.ts
```
