from __future__ import annotations

import hashlib
from pathlib import Path

from blunder_tutor.index import append_index, build_metadata


def _normalize_pgn(pgn_text: str) -> str:
    return pgn_text.strip().replace("\r\n", "\n").replace("\r", "\n") + "\n"


def store_pgn(
    source: str, username: str, pgn_text: str, data_dir: Path
) -> tuple[Path, dict[str, object]] | None:
    """Store a PGN file and return path + metadata (but don't update index)."""
    normalized = _normalize_pgn(pgn_text)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    target_dir = data_dir / "pgn" / source / username
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{digest}.pgn"

    if target_path.exists():
        return None

    target_path.write_text(normalized, encoding="utf-8")

    # Build metadata but DON'T update index
    metadata = build_metadata(normalized)
    metadata["id"] = digest
    metadata["source"] = source
    metadata["username"] = username
    metadata["pgn_path"] = str(target_path)

    return target_path, metadata


def index_stored_games(data_dir: Path, game_metadata: list[dict[str, object]]) -> int:
    for metadata in game_metadata:
        append_index(data_dir, metadata)

    return len(game_metadata)
