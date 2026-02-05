# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
