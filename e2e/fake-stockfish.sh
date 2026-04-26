#!/bin/bash
# Minimal UCI-protocol fake used by the auth e2e suite. The app boots
# its engine pool eagerly during lifespan startup, so we need
# SOMETHING at STOCKFISH_BINARY that speaks the handshake. The auth
# test never triggers analysis, so `bestmove` / `go` / `setoption`
# can stay no-ops.
#
# Why a shell script and not a real Stockfish: CI should not depend
# on a ~100 MB binary installed out-of-band, and this suite exercises
# auth/routing, not the engine.
while IFS= read -r line; do
  case "$line" in
    uci)
      echo "id name fake-stockfish"
      echo "id author blunder-tutor-e2e"
      echo "uciok"
      ;;
    isready)
      echo "readyok"
      ;;
    quit)
      exit 0
      ;;
    *)
      # Swallow `position`, `go`, `setoption`, `ucinewgame`, `stop`,
      # etc. — the auth suite never exercises them, but hanging is
      # worse than being silently ignored.
      ;;
  esac
done
