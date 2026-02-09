from __future__ import annotations

import json
from pathlib import Path

from blunder_tutor.utils.pgn_utils import build_game_metadata


def load_from_directory(
    directory: Path,
    username: str | None = None,
    source: str = "lichess",
    max_games: int | None = None,
) -> list[dict[str, object]]:
    manifest_path = directory / "manifest.json"
    if manifest_path.exists():
        return _load_from_manifest(manifest_path, directory, max_games)
    return _load_from_pgn_files(directory, username or "unknown", source, max_games)


def _load_from_manifest(
    manifest_path: Path,
    directory: Path,
    max_games: int | None,
) -> list[dict[str, object]]:
    entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    if max_games is not None:
        entries = entries[:max_games]

    games: list[dict[str, object]] = []
    for entry in entries:
        pgn_path = directory / entry["filename"]
        pgn_content = pgn_path.read_text(encoding="utf-8")
        games.append(
            {
                "id": entry["game_id"],
                "source": entry.get("source", "lichess"),
                "username": entry.get("username", "unknown"),
                "pgn_content": pgn_content,
                "date": entry.get("date"),
                "end_time_utc": entry.get("end_time_utc"),
                "white": entry.get("white"),
                "black": entry.get("black"),
                "result": entry.get("result"),
                "time_control": entry.get("time_control"),
            }
        )
    return games


def _load_from_pgn_files(
    directory: Path,
    username: str,
    source: str,
    max_games: int | None,
) -> list[dict[str, object]]:
    pgn_files = sorted(directory.glob("*.pgn"))
    if max_games is not None:
        pgn_files = pgn_files[:max_games]

    games: list[dict[str, object]] = []
    for pgn_path in pgn_files:
        pgn_text = pgn_path.read_text(encoding="utf-8")
        metadata = build_game_metadata(pgn_text, source, username)
        if metadata:
            games.append(metadata)
    return games
