## Test Conventions

- Use classes to group tests by feature/method under test.
- Use module-level functions only for trivial one-off checks.
- Prefer `pytest.mark.parametrize` over copy-paste test methods that vary only in input/output.
- Use shared helpers and factories from `tests/helpers/` instead of local copies:
  - `tests/helpers/engine.py` — `make_test_client`, `mock_engine_context`, `create_mock_engine`
  - `tests/helpers/pipeline.py` — `make_pov_score`, `make_move_eval`, `make_mock_context`
  - `tests/helpers/stats_db.py` — `insert_test_game`, `insert_test_move`
  - `tests/helpers/factories.py` — `make_blunder`, `make_mock_game`
  - `tests/helpers/seeding.py` — `insert_game_index_row`, `make_pgn` (canonical `game_index_cache` row seeder; use instead of hand-writing raw `INSERT`s — schema-version-specific migration tests excepted)
- No docstrings that restate the test method name.
