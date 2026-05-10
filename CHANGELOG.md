# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.6]

### Fixed

- **Trainer keyboard shortcuts no longer break after toggling Show Threats**: Clicking a checkbox in Board Settings (Show Threats, Show Arrows, etc.) used to leave focus on the input, which silently swallowed every trainer shortcut — `B` for Show Best Move, `N` for Next, `R` for Reset, and so on — until you clicked elsewhere. Shortcuts now stay active when focus is on a checkbox or radio.

### Changed

- **"Play Full Engine Line" is now always on**: Removed the toggle from Board Settings. Revealing the best move always replays the full engine line so you can see the follow-up plan, not just the single best reply.

---

## [3.1.3]

### Added

- **Opt-in Sentry observability**: New `SENTRY_ENABLED=true` + `SENTRY_DSN=...` config wires the app to Sentry for error capture, request traces, and lightweight metrics covering background jobs, the chess engine pool, the WebSocket layer, and the periodic scheduler. Off by default, zero overhead when disabled. See `docs/environment.md` for the full env-var surface and metric/tag contract.

### Changed

- **Stricter `SECRET_KEY` validation**: The auth secret is now checked at startup with explicit failure on missing or trivially-weak values, replacing the previous silent fallback. `.env.example` documents the expected entropy.

---

## [3.1.0]

### Added

- **Multi-user authentication (opt-in)**: New `AUTH_MODE=credentials` mode turns Blunder Tutor into a multi-user instance. Adds sign-in, sign-up, and first-time-setup pages with invite-code bootstrapping, session cookies, and a per-user SQLite database so each account's games, settings, and progress stay fully isolated. Default `AUTH_MODE=none` preserves the existing single-user behaviour. All auth strings are localized across English, Russian, Ukrainian, Spanish, Polish, Belarusian, and Chinese.
- **Auth admin CLI**: `uv run python main.py auth <command>` for operators running a multi-user instance — `list-users`, `reset-password`, `revoke-sessions`, `delete-user`, `regenerate-invite`, and `prune-orphans`.
- **Tracked profiles**: New Profiles page lets you manage multiple Lichess and Chess.com accounts per user, mark a primary profile per platform, and view per-profile stats (games imported, ratings, last sync). Username validation hits the platform API live before saving, and deletion offers a choice between detaching the profile or removing its imported games.
- **Per-profile bulk import**: The Management page's bulk-import flow now targets a selected profile instead of a single global username, so games from each tracked account land under the right profile.
- **Periodic background sync**: New scheduler ticks every five minutes and pulls fresh games and rating snapshots for each tracked profile in the background — no manual import needed to stay up to date.

### Changed

- **Setup flow replaced by profiles**: The old single-username `/setup` onboarding step is gone. New users go straight to the Profiles page to add their first tracked account, and the legacy `username` field has been removed from settings.

---

## [3.0.0]

### Changed

- **Frontend rewritten to TypeScript and Preact**: Migrated the entire frontend from vanilla JavaScript to TypeScript with Preact islands architecture. Covers the trainer, dashboard, and settings pages.
- **Trainer page overhaul**: Major rewrite of the trainer page as Preact components with improved structure and interactivity.
- **Pre-move animations**: Puzzle transitions now play smooth piece animations before the user's turn, making the training flow feel more natural.

### Fixed

- **Settings persistence and panel stickiness**: Resolved issues with settings not saving correctly and side panels losing their sticky positioning.
- **Vim mode**: Fixed broken keyboard-driven navigation in the trainer.
- **Tactical puzzles empty state**: Corrected handling when no tactical puzzles are available.
- **Docker image vendored libs**: Fixed missing vendored libraries in the Docker build.

### Added

- **End-to-end test suite**: Introduced Playwright-based e2e tests with click interaction coverage, now required to pass before release.

---

## [2.2.1]

### Changed

- **Smarter trap detection with transposition support**: The trap detection engine now recognizes traps reached via move transpositions, not just exact move order. Expanded the trap catalog with significantly more pattern variations. Localized new labels across all seven languages.

### Fixed

- **README link layout**: Fixed link formatting and added blog post link in README.

---

## [2.2.0]

### Added

- **Game review page (experimental)**: Browse any analyzed game move-by-move with an interactive board, evaluation chart, and move classification highlights. Accessible from the trainer and starred puzzles via a "Review Game" link. Gated behind the `page.game_review` feature flag.

### Changed

- **Shared board layout CSS**: Extracted common board, context-tag, and layout styles from the trainer into a reusable `board-layout.css` stylesheet shared by both the trainer and game review pages.

---

## [2.1.6]

### Changed

- **Trap section game links**: Traps now link directly to the original game on Lichess or Chess.com.

---

## [2.1.5]

### Fixed

- **Dashboard style fixes**: Corrected visual issues in the dashboard layout.

---

## [2.1.4]

### Changed

- **Smarter blunder explanations for ignored threats**: The explanation engine now detects when a blunder ignores a piece that is already under profitable attack, and when the best move retreats a threatened piece to safety. Localized across all seven languages.

---

## [2.1.3]

### Changed

- **Draggable best-move panel**: The result card that shows after submitting a move is now a floating panel you can drag around the board area. Position is remembered across puzzles via localStorage.
- **Move submission feedback**: Submit button now pulses and the move prompt shows a spinner while the engine evaluates your move.

---

## [2.1.2]

### Changed

- **Chessground upgraded to 10.0.2**: Updated the vendored chessground library from 9.1.1 to 10.0.2, bringing rendering improvements and bug fixes.
- **Board coordinates toggle**: Added a trainer option to show or hide board coordinates (a–h, 1–8), with the preference saved across sessions.

---

## [2.1.1]

### Added

- **Trap move previews**: Traps page now shows an interactive sequence player that animates the key moves for each trap, making it easier to understand the pattern at a glance.
- **Growth tracking analytics**: New dashboard section with period-over-period comparisons for games played, blunders per game, and accuracy — helping you see improvement trends over time.

### Changed

- **Dashboard layout reordered**: Reorganized dashboard sections for a more logical flow, with growth metrics prominently placed.

---

## [2.1.0]

### Added

- **Vim-like move input**: Type moves in algebraic notation (e.g., `Nf3`, `e4`) directly from the keyboard in the trainer — no need to drag pieces. Includes auto-completion, disambiguation prompts, and full localization across all languages.
- **Custom dropdown component**: New reusable dropdown with dividers and improved styling, replacing native selects on management and settings pages.

### Changed

- **Dashboard filters redesigned**: Rebuilt the dashboard filter section from scratch with a cleaner layout, better date range controls, and improved responsive behavior. Changed default font.
- **Heatmap reworked**: Improved heatmap rendering and styling on the dashboard.
- **Design token consolidation**: Migrated hardcoded colors, spacing, and typography values across all pages to CSS custom properties for better theme consistency.
- **CSS class cleanup**: Replaced inline styles and ad-hoc classes across all pages (trainer, dashboard, settings, management, setup, starred, traps) with shared utility classes.
- **Chessboard always visible**: Fixed trainer layout so the board stays in the viewport without being clipped.

---

## [2.0.4]

### Changed

- **Trainer layout overhaul**: Improved vertical fit so the board and controls sit within the viewport without scrolling. Removed the session subheader, reorganized action buttons, and made the top header sticky for a cleaner, more consistent experience.
- **Landing page polish**: Visual tweaks to the public landing page for better readability and appeal.

### Internal

- **Test suite refactor**: Large-scale restructuring of the test suite — consolidated shared helpers/factories, expanded coverage for the database layer and puzzle services.

---

## [2.0.3]

### Added

- **Game-phase filtering on dashboard**: Filter blunder statistics by game phase (opening, middlegame, endgame) directly from the dashboard.
- **Sponsor links**: Added GitHub sponsorship info for supporting the project.
- **Demo links**: Added direct links to the live demo from the README and landing page.

### Changed

- **Dashboard filter refactor**: Simplified and cleaned up the stats repository and API layer, reducing code duplication across filter handling.
- **Landing page refresh**: Streamlined the landing page markup and styles.

---

## [2.0.2]

### Added

- **Demo mode database**: Ship a pre-built SQLite database so the hosted demo starts with real games and blunders out of the box, no setup required.
- **Plausible analytics**: Optional, privacy-friendly analytics via Plausible for the demo server — configured through `PLAUSIBLE_DOMAIN` / `PLAUSIBLE_SCRIPT_URL` env vars.
- **Pre-commit hooks**: Added prek pre-commit configuration to enforce linting and formatting on commit.

---

## [2.0.1]

### Added

- **Play full engine line**: In the trainer, you can now step through the entire best engine continuation instead of seeing only the first move.

### Changed

- **Smoother onboarding**: Platform usernames are validated before saving, and game download + analysis starts automatically after setup — no extra clicks needed.
- **Frontend modularization**: Split large trainer and dashboard scripts into focused modules (state, filters, UI, charts, etc.) with a shared event bus. Added comprehensive frontend tests.

---

## [2.0.0]

### Changed

- Complete redesign of the application. Punchy, not-looking like an AI blob. It has its ups and downs, provides better UX and clarity, still has several stylistic issues, but I'll fix them along the way.

## [1.7.4]

### Changed

- **PV-first blunder explanations**: Reworked the explanation engine to lead with the principal variation (PV) line and use static templating, producing clearer and more understandable descriptions of why a move was a blunder.
- **Board images reworked**: Updated all screenshot assets in the README. Disabled board coordinates display due to unreliable rendering across browsers.

---

## [1.7.3]

### Changed

- Minor adjustments to blunder explanation wording and formatting.

---

## [1.7.2]

### Fixed

- **Dashboard stats consistency**: Proper filtering by game types and date ranges across all dashboard widgets — previously some charts ignored active filters.

---

## [1.7.1]

### Fixed

- **localStorage not cleared on data wipe**: Clicking "Remove all data" left stale filter state in localStorage, causing phantom filters on next use.
- **Incorrect gameType filtering in dashboards**: Dashboard charts applied game type filters incorrectly, showing data from unselected time controls.

---

## [1.7.0]

### Added

- **Manual PGN import** (experimental): Import games by pasting PGN text directly, without needing a Lichess/Chess.com account. Feature-flagged and switched off by default.
- **Favourite puzzles** (experimental): Star/unstar blunder puzzles during training to build a personal collection of positions worth revisiting. Dedicated `/starred` page with list view. Feature-flagged under `trainer.starred`.
- **Debug info for game analysis** (experimental): New `GET /api/games/<game_id>/debug` endpoint and optional 📋 Debug button in the trainer (behind `debug.copy` feature flag) that copies a full diagnostic snapshot — metadata, PGN, move-by-move analysis table, and blunder summary.
- **Improved blunder descriptions**: Detect hanging-piece missed captures and mate-in-1 misses in explanations.

### Changed

- **Blunder classification aligned with Lichess**: Dead-end positions where mate was already predicted are no longer classified as blunders, reducing false positives.
- **Dropped legacy username resolution**: Removed old username-resolving code path that was superseded by the Setup/Management page flow.

---

## [1.6.1]

### Fixed

- **False blunder classification in mate-predicted positions**: Positions where Stockfish already predicted a forced mate were incorrectly marking every subsequent move as a blunder. Adopted Lichess-style logic to handle these dead-end positions correctly, significantly reducing inflated blunder counts.

---

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
