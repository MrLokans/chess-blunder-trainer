# Debugging Game Analysis

When investigating a specific blunder or analysis issue, use the debug info feature to get a full game snapshot.

## Getting debug info

1. **Via the web UI**: Enable the `debug.copy` feature flag in Settings → Developer, then click the 📋 **Debug** button next to any puzzle in the trainer. This copies a markdown-formatted snapshot to clipboard.
2. **Via the API**: `curl http://localhost:8000/api/games/<game_id>/debug` — returns plain text with PGN, metadata, and move-by-move analysis.
3. **Finding the game_id**: Game IDs are SHA-256 hashes of normalized PGN content. You can find them in:
   - The puzzle API response (`game_id` field)
   - The `game_index_cache` table:

     **Default mode** (`AUTH_MODE=none`):
     ```bash
     sqlite3 data/main.sqlite3 "SELECT game_id, white, black, date FROM game_index_cache ORDER BY end_time_utc DESC LIMIT 10;"
     ```

     **Credentials mode** (`AUTH_MODE=credentials`):
     ```bash
     sqlite3 users_dir/<user_id>/main.sqlite3 "SELECT game_id, white, black, date FROM game_index_cache ORDER BY end_time_utc DESC LIMIT 10;"
     ```

## What the debug output contains

- Game metadata (source, players, result, date, time control, ECO opening)
- Link to the original game on Lichess/Chess.com
- Full PGN
- Move-by-move analysis table (ply, eval before/after, cp_loss, classification, game phase)
- Blunders summary with eval swings

## Useful DB queries for investigation

Connect to the correct DB path for your auth mode (see above). These queries work identically in both modes.

```sql
-- Find all blunders for a game
SELECT ply, san, eval_before, eval_after, cp_loss, best_move_san, game_phase, tactical_pattern
FROM analysis_moves WHERE game_id = '<id>' AND classification = 3;

-- Check if a game has been analyzed
SELECT game_id, analyzed FROM game_index_cache WHERE game_id = '<id>';

-- Find analysis metadata (engine settings, thresholds)
SELECT * FROM analysis_games WHERE game_id = '<id>';

-- Find games by player name
SELECT game_id, white, black, date, result FROM game_index_cache
WHERE white LIKE '%name%' OR black LIKE '%name%' ORDER BY end_time_utc DESC LIMIT 10;
```
