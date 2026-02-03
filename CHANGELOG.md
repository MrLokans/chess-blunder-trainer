# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
