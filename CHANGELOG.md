# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.0]

### Added

- **Traps & gambits detection** (experimental): Pattern-matching engine that identifies known opening traps (Scholar's Mate, Fried Liver, Fishing Pole, etc.) in your analyzed games. Tracks whether you sprung or fell into each trap. New dedicated `/traps` page with a trap catalog, per-trap stats, and game history. Dashboard summary card shows trap encounter counts.

### Changed

- **Settings page no longer manages usernames**: Lichess/Chess.com usernames are now configured exclusively through the Setup page (initial onboarding) and the Management page (import form). Removes the confusing duplication where usernames appeared in both Settings and Management.

### Fixed

- **Locale and feature flags not applied to navigation**: Switching language or toggling features required a full backend process restart to take effect in the navigation bar and other imported macros. Root cause was Jinja2 caching `env.globals` (including `t()`, `has_feature()`) at macro import time. Fixed by adding `with context` to all `{% from "_nav.html" import ... %}` directives so macros always receive the current request's globals.
- **Saved locale lost on server restart**: The locale preference stored in the database was never loaded into the in-memory cache on application startup. After a process restart, the app fell back to English (or Accept-Language) until the user changed language again. Now `lifespan` seeds `_locale_cache` from the DB, and `_detect_locale` falls back to a DB read when neither cookie nor cache is available.
- **Locale cookie set only client-side**: The `POST /api/settings/locale` endpoint now sets the `locale` cookie via a `Set-Cookie` response header instead of relying on client-side JavaScript, making locale persistence more reliable.

---

## [1.5.0]

### Added

- **Conversion & resilience rates**: New dashboard widget showing how well you convert winning positions into wins and save losing positions. Tracks games with advantage/disadvantage and their outcomes. New API endpoint `GET /api/stats/conversion-resilience` with date range and time control filtering. Feature-flagged under `dashboard.conversion_resilience`.
- **Collapse point analysis**: Dashboard visualization of when you typically make your first blunder in a game. Shows average/median collapse move, distribution chart bucketed by move ranges, and clean game count. New API endpoint `GET /api/stats/collapse-point`. Feature-flagged under `dashboard.collapse_point`.
- **Engine rate limiting in demo mode**: Per-IP throttling on engine-hitting endpoints (`/api/puzzle`, `/api/submit`, `/api/analyze`) using `fastapi-throttle`. Default: 30 requests per 60 seconds. Configurable via `DEMO_THROTTLE_RATE` env var (format: `requests/seconds`, e.g. `10/30`). Responses include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `Retry-After` headers. No-op in normal (non-demo) mode.


### Fixed

- **Hanging piece detection in explanations**: Improved accuracy of hanging piece detection in blunder explanations — no longer misidentifies defended pieces as hanging.

---

## [1.4.0]

### Added

- **Demo mode**: Read-only deployment mode (`DEMO_MODE=true`) for hosting a public demo. `DemoModeMiddleware` blocks all mutation endpoints (setup, jobs, settings, data wipe) with 403 responses. Templates conditionally hide action buttons. Persistent top banner with link to self-hosting instructions. Trainer puzzle solving and all GET endpoints remain fully functional.
- **Beginner-friendly blunder explanations**: Natural-language explanations of why a move was a blunder and what the best move achieves, shown in the trainer after the best move is revealed. Template-based explanation generator using `python-chess` detects: hanging pieces, exposed pieces, bad captures, checkmate, check+capture, tactical patterns (fork/pin/skewer/discovered/back rank/hanging), simple captures, and cp-loss fallback. Null-move threat detection for quiet best moves (e.g., "The best move Nh4 creates a bishop threat" when the knight clears a diagonal). Best-line material analysis for combinations. Two-phase i18n architecture: `generate_explanation()` returns i18n keys with parameters, `resolve_explanation()` formats them via `TranslationManager` for the active locale.
- **Grammatical case support for piece names**: Slavic translations (Russian, Ukrainian, Polish, Belarusian) now use correct noun declensions in explanation templates. Case-specific keys (`.gen`, `.acc`, `.inst` suffixes) for all six chess pieces across all four Slavic locales (18 new keys per locale).


### Changed

- **README restructured** for clarity, Docker quick-start command fixed, GitHub release annotations for Docker images.

### Fixed

- Explanation no longer shows "wins material with a none" when tactical pattern is `None` — the string `"None"` from pattern labels is now filtered out.
- Belarusian declension of "ферзь": oblique cases now correctly use "фярзя"/"фярзём" (яканне rule for unstressed vowels).

---

## [1.3.0]

### Added

- **Position difficulty scoring** (#14): Blunders scored 0–100 based on legal move count and best move type (captures/checks are easier to find). New `difficulty` column in `analysis_moves`, dashboard difficulty breakdown chart, and trainer difficulty filter.
- **Weighted puzzle selection** (#13): Puzzles for frequently-failed tactical patterns appear more often in training. Based on per-pattern failure rates from puzzle attempt history.
- **Grouped opening breakdown** (#16): ECO openings on the dashboard are now grouped by base opening name (e.g., all Sicilian variations collapse under one row) with aggregated stats. Added Lichess and 365chess learning links, and visual hierarchy for variation/sub-variation names.

### Changed

- **Blunder filtering** (#10): Skip blunders in already-lost positions (eval < −300cp) and positions that remain comfortably winning after the blunder (eval > +300cp). These low-value positions no longer appear in training.
- **Dashboard WebSocket performance** (#17): `job.progress_updated` events are now debounced (2s) instead of triggering a full stats reload on every event, reducing backend load and UI jank during analysis.

## [1.2.0]

### Changed

- Introduce EnginePool / WorkCoordinator - a persistent worker-per-engine pool that replaces the previous pattern of spawning a fresh Stockfish process per game. Engines are long-lived, reused across games, and auto-configure Threads and Hash for better hardware utilization.
- Worker-per-engine pattern: N Stockfish processes with N async workers consuming from a shared queue
- WorkCoordinator facade with submit() / drain() / shutdown
- Per-task timeout (default 300s) with automatic engine kill & respawn
- Callers (GameAnalyzer.analyze_bulk, AnalyzeGamesJob, AnalysisService) submit closures instead of managing engine lifecycle themselves- Pass game=game_id to engine.analyse() to preserve transposition table across positions within the same game (previously flushed every call)
- Pre-collect all positions, evaluate each once, and derive both before/after evals from the position array — halves the number of engine.analyse() calls per game
- Keep full move stack in board copies for better Stockfish continuity
- Parse only INFO_SCORE | INFO_PV instead of INFO_ALL- Add write_transaction() context manager with per-db-path asyncio.Lock to serialize writes, fixing "database is locked" errors under parallel analysis
- All repository write methods migrated to use write_transaction()
 Pipeline executor (pipeline/executor.py)
- Batch mark_steps_completed() into a single call after all steps run
 instead of one DB write per step
- AnalyzeGamesJob watches for cancellation via EventBus subscription
- Centralize default depth in constants.DEFAULT_ENGINE_DEPTH

### Fixed

- Blunder stats calculation now respects original player blunders only.

## [1.1.0]

### Added

- **Entitlements engine**: Extensible feature flags system allowing users to enable/disable parts of the application (e.g., dashboard charts, trainer, heatmap) from settings
- **Feature toggles UI**: New settings section with toggleable switches for each application feature, with changes reflected across navigation, dashboard, and trainer

### Fixed

- **Locale application**: Fixed locale not being applied correctly on both backend and frontend after changing language in settings

## [1.0.1]

### Added

- **Polish locale**: Full Polish (Polski) translation with proper chess terminology and ICU plural rules (one/few/many)
- **Ukrainian locale**: Full Ukrainian (Українська) translation with chess terms (дебют, мітельшпіль, вилка, зв'язка) and one/few/many/other plurals
- **Belarusian locale**: Full Belarusian (Беларуская) translation with chess terms (дэбют, мітэльшпіль, відэлец, звязка) and one/few/many/other plurals
- **Spanish locale**: Full Spanish (Español) translation with chess terms (apertura, medio juego, horquilla, clavada, enfilada) and one/other plurals
- **Chinese locale**: Full Simplified Chinese (中文) translation with chess terms (开局, 中局, 残局, 捉双, 牵制, 串打)

## [1.0.0] - 2026-02-06



This release is quite huge, but focuses more on internals, code organization and stability.

### Added

- **Favicon**: Added site favicon
- **Frontend tests and linting**: ESLint configuration and test suite for JavaScript modules (API client, color utils, eval bar, filter persistence, heatmap, job card, progress tracker)
- **Chessground integration**: Switched chessboard rendering to Lichess's Chessground library for a more polished board experience
- **Vendored third-party dependencies**: Bundled Chart.js, chess.js, htmx, and Chessground for offline/self-contained deployments
- **LICENSE and THIRD_PARTY_LICENSES**: Added project license and third-party attribution docs
- **Game links**: Links to the original game on Lichess/Chess.com from trainer and analysis views

### Changed

- **Accuracy metric**: Replaced Centipawn Loss (CPL) with Accuracy percentage across the dashboard and analysis views
- **Frontend modularization**: Split monolithic JS files into focused ES modules (API client, WebSocket client, filter persistence, color input, progress tracker, board adapter, arrows, highlights, threats, eval bar)
- **CSS modularization**: Extracted per-page stylesheets (dashboard, settings, setup) and reworked partial/nav styles
- **Stockfish version bump**: Updated Stockfish version in the local Dockerfile

## [0.9.1] - 2026-02-05

### Added

- Additional board color presets and piece sets

## [0.9.0] - 2026-02-05

### Added

- **Puzzle completion heatmap**: New GitHub-style activity heatmap on the dashboard showing daily puzzle practice
- **Dashboard time control filter**: Filter all dashboard statistics by time control (bullet, blitz, rapid, classical, correspondence)
- **Chessboard styling**: Customize board colors and piece sets in settings
- 6 board color presets (Brown, Blue, Green, Purple, Gray, Wood)
  - 6 piece sets (Wikipedia, Alpha, California, Cardinal, CBurnett, Merida)
  - Custom color picker for light and dark squares
  - Live preview in settings page

### Fixed

- Settings page now correctly saves and loads user preferences

## [0.8.0] - 2026-02-04

### Added

- **Game type filtering**: Filter blunders by time control (bullet, blitz, rapid, classical, correspondence)
- **Color filtering**: Filter blunders by player color (white/black) in trainer
- **Blunders by Game Type chart**: New dashboard visualization showing blunder distribution across time controls
- **Collapsible filter panel**: Reorganized trainer UI with all filters in a clean, collapsible panel

## [0.7.0] - 2026-02-03

### Added

- Add tactics detector and visualizer

## [0.6.0] - 2026-02-03

### Added

- Theme engine for customizable UI styling

## [0.5.0] - 2026-02-03

### Added

- Performance breakdowns by day and hour in statistics
- Engine version info display
- Legal move highlights in the training UI
- Automatic analysis upon game re-import
- "Remove all data" button for complete data cleanup

### Changed

- Updated Stockfish to version 18
- Default move time changed to 2 seconds

### Fixed

- ECO (Encyclopedia of Chess Openings) look-up job
- Periodic sync job reliability

## [0.1.0] - Initial Release

Initial release of Blunder-Tutor with core functionality:

- Fetch games from Lichess and Chess.com
- Analyze games with Stockfish to identify blunders
- Training interface to practice blunder positions
- Web UI and CLI interfaces

