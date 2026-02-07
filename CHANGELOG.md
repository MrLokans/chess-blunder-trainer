# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

