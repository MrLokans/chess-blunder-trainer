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

## E2E (Playwright) Conventions

- Locate elements by `data-testid` (kebab-case, e.g. `profile-add`), a stable `id`, or a `data-value` holding the code value (`data-value="blitz"`), never by visible text: UI strings are translated and the locale is server-global. `e2e/eslint.config.ts` rejects `getByText`/`getByLabel`/`getByRole({ name })`/`hasText`; disable it per line only when matching user data such as a username.
- Shared primitives take a `testId` prop (`Button`, `Badge`, `Segmented`); `Tabs` emits `tab-<key>`, `ConfirmDialog` emits `confirm-dialog-{confirm,secondary,cancel}`.
- Wait for app state, not time: the trainer board exposes `data-movable` (`white`/`black`/`none`) and `data-orientation`, updated when chessground actually accepts moves.
- Specs that change server-global state (feature flags, locale, direct DB writes) go in `GLOBAL_STATE_SPECS` in `e2e/playwright.config.ts`; they run one at a time after the parallel suite.
