# Vendored Stockfish WASM Engine

## Source

- **Upstream**: [nmrugg/stockfish.js](https://github.com/nmrugg/stockfish.js)
- **Variant**: `stockfish-18-lite-single` — single-threaded Stockfish 18 with a smaller NNUE.
  Weaker than the full build but does not require `SharedArrayBuffer` / cross-origin
  isolation, so no COOP/COEP headers are needed on the review route.
- **License**: GPL-3.0-or-later

## Files

| File | Role |
|------|------|
| `stockfish-18-lite-single.js` | Single-threaded entry — loaded by `frontend/src/shared/engine/stockfish.ts` |
| `stockfish-18-lite-single.wasm` | WASM payload (embedded smaller NNUE — no separate `.nnue` file) |

`stockfish-18-lite-single.wasm` is intentionally excluded from the prek
`check-added-large-files` hook (see `prek.toml`) — the file is ~7 MB and is
the only artifact in this directory that exceeds the 500 KB cap.

## Why same-origin

Files are served at `/static/vendor/stockfish/` (mounted from
`blunder_tutor/web/static/`). Serving the worker entry from the same origin
keeps the `Worker(...)` construction simple — a CDN URL would require a
worker-shim and complicate CSP. There is **no COOP/COEP requirement** on
this variant: it does not use `SharedArrayBuffer`.

## How to update

1. Fetch the two files for the desired version from the upstream `src/` directory:
   - <https://github.com/nmrugg/stockfish.js/tree/master/src>
2. Replace both files in this directory.
3. If the filename changes (e.g. a future `stockfish-19-lite-single`), update:
   - `ENGINE_URL` in `frontend/src/shared/engine/stockfish.ts`
   - The `exclude` regex on the `check-added-large-files` hook in `prek.toml`
   - This README
