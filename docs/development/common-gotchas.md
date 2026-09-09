## Cross-Cutting Concerns (Platform Checklist)

When adding or modifying features, check each of these dimensions:

### Localization (i18n)
- Every user-visible string goes through `t()` — in templates (`{{ t('key') }}`), in JS (`t('key')`).
- Add keys to `locales/en.json` first, then **all** other locale files (`ru`, `uk`, `es`, `pl`, `be`, `zh`).
- Non-English translations must be real translations, not English fallbacks.
- Key namespaces: `common.*`, `nav.*`, `chess.*`, `trainer.*`, `dashboard.*`, `management.*`, `settings.*`, `setup.*`, `heatmap.*`, `demo.*`.
- See [`docs/i18n.md`](docs/i18n.md) for full rules (ICU plurals, no HTML in values, etc.).

### Feature Flags (Entitlements)
- Toggleable UI sections use the feature flag system (`blunder_tutor/features.py`).
- In templates: `{% if has_feature('feature.key') %}`. In JS: `window.__features`.
- When adding a new toggleable feature: add to `Feature` enum, `DEFAULTS`, `FEATURE_GROUPS`, `FEATURE_LABELS`, and add a `settings.features.*` i18n key.

### Demo Mode
- Hosted demo runs with `DEMO_MODE=true` — `DemoModeMiddleware` is **deny-by-default**: every mutation method (POST/PUT/PATCH/DELETE) returns 403 unless its path matches the `DEMO_ALLOWED_MUTATIONS` allowlist in `blunder_tutor/web/middleware.py`.
- When adding a new POST/DELETE/PUT endpoint: it is blocked automatically. Only if it must work in demo do you add a `(METHOD, regex)` entry to `DEMO_ALLOWED_MUTATIONS` (and justify why it is demo-safe).
- In templates: use `{% if not demo_mode %}` to hide buttons/forms for blocked actions.
- Templates that override `{% block body %}` must include `{% include '_demo_banner.html' %}` at the top.

### Avoiding Duplication
- **Templates**: reusable partials go in `templates/_*.html` (e.g., `_nav.html`, `_demo_banner.html`). Don't duplicate markup across pages.
- **JS**: shared utilities go in `frontend/src/shared/*.ts` (e.g., `debounce.ts`, `api.ts`, `features.ts`). Page-specific modules go in `src/<page>/` (`trainer/`, `dashboard/`, etc.). Don't inline logic that exists in a shared module.
  - `blunder_tutor/web/static/js/` is **legacy** — still served for the two scripts `templates/base.html` loads directly (`i18n.js`, `srs-badge.js`). Do NOT add new modules to this tree.
  - Remaining unported legacy modules: `i18n.js`, `filter-persistence.js`. Everything else has a `.ts` equivalent in `frontend/src/shared/`.
- **CSS**: design tokens and shared styles live in `base.css`. Page-specific styles go in `static/css/<page>.css`. Don't duplicate color values or component styles.
- **Python**: business logic belongs in services/repositories, not in API route handlers. Route handlers should be thin wrappers.

### Theme Integration
- New visual components must use CSS custom properties from `base.css` (e.g., `var(--primary)`, `var(--error)`, `var(--text-muted)`), not hardcoded colors.
- Preview any new component in the settings theme preview if applicable.

### Database Changes
- New columns require a migration in `blunder_tutor/migrations.py`.
- Consider whether data should be cleared when the user wipes all data (`DELETE /api/data/all`).

### Auth Mode
- `AUTH_MODE=none` (default) uses a single legacy DB at `config.data.db_path`. `AUTH_MODE=credentials` materializes a per-user DB at `users_dir/<user_id>/main.sqlite3` on signup.
- Route handlers must resolve the DB path via the `get_db_path` / `DbPathDep` dependency (see `blunder_tutor/web/dependencies.py`). Never import `config.data.db_path` in a handler — that's the none-mode legacy path and opening it under credentials mode silently bypasses isolation.
- `app.state.job_executor` and `app.state.scheduler` are non-None in both auth modes. The executor routes events by `user_id` via `db_path_resolver`; the scheduler ticks every 5 min and dispatches sync jobs per-user. `app.state.settings_repo` is still `None` in credentials mode — settings live in each user's DB and are resolved per-request.
- `JobExecutionRequestEvent.create(...)` requires `user_id=ctx.user_id` (from `UserContextDep` in handlers, or from `DependencyContext` inside background runners). Events without `user_id` cannot be routed.
- Middleware path exemptions (login, signup, auth API) live in `blunder_tutor/web/paths.py` (`AUTH_UI_PATHS`, `AUTH_API_PREFIX`). Add new auth-adjacent paths there, not in a middleware-local constant — three copies will drift.
- Operator CLI: `uv run python main.py auth <sub>` with subcommands `list-users`, `reset-password`, `revoke-sessions`, `delete-user`, `regenerate-invite`, `prune-orphans`. Gated behind `AUTH_MODE=credentials`.
