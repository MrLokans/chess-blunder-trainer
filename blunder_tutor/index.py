from __future__ import annotations

import io
import json
from collections.abc import Iterable
from pathlib import Path

import chess.pgn

from blunder_tutor.utils.date_utils import parse_pgn_datetime_iso


def build_metadata(pgn_text: str) -> dict[str, str | None]:
    stream = io.StringIO(pgn_text)
    game = chess.pgn.read_game(stream)
    if game is None:
        return {}

    headers = dict(game.headers)
    date = headers.get("UTCDate") or headers.get("Date")
    time = headers.get("UTCTime") or headers.get("Time")
    end_time = parse_pgn_datetime_iso(date, time)
    return {
        "event": headers.get("Event"),
        "site": headers.get("Site"),
        "date": headers.get("Date"),
        "utc_date": headers.get("UTCDate"),
        "utc_time": headers.get("UTCTime"),
        "end_time_utc": end_time,
        "white": headers.get("White"),
        "black": headers.get("Black"),
        "result": headers.get("Result"),
        "time_control": headers.get("TimeControl"),
        "termination": headers.get("Termination"),
    }


def append_index(data_dir: Path, record: dict[str, object]) -> None:
    index_dir = data_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "games.jsonl"

    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True))
        handle.write("\n")


def read_index(
    data_dir: Path,
    source: str | None = None,
    username: str | None = None,
) -> Iterable[dict[str, object]]:
    index_path = data_dir / "index" / "games.jsonl"
    if not index_path.exists():
        return []

    def _iter() -> Iterable[dict[str, object]]:
        with index_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                if source and record.get("source") != source:
                    continue
                if username and record.get("username") != username:
                    continue
                yield record

    return _iter()


def _load_existing_ids(data_dir: Path) -> set[str]:
    existing = set()
    for record in read_index(data_dir):
        game_id = record.get("id")
        if isinstance(game_id, str):
            existing.add(game_id)
    return existing


def rebuild_index(
    data_dir: Path,
    source: str | None = None,
    username: str | None = None,
    reset: bool = False,
) -> int:
    index_dir = data_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_path = index_dir / "games.jsonl"

    if reset and index_path.exists():
        index_path.write_text("", encoding="utf-8")

    existing_ids = set() if reset else _load_existing_ids(data_dir)
    pgn_root = data_dir / "pgn"
    if not pgn_root.exists():
        return 0

    count = 0
    for pgn_path in pgn_root.rglob("*.pgn"):
        parts = pgn_path.parts
        try:
            source_part = parts[parts.index("pgn") + 1]
            user_part = parts[parts.index("pgn") + 2]
        except (ValueError, IndexError):
            continue

        if source and source != source_part:
            continue
        if username and username != user_part:
            continue

        game_id = pgn_path.stem
        if game_id in existing_ids:
            continue

        pgn_text = pgn_path.read_text(encoding="utf-8")
        metadata = build_metadata(pgn_text)
        append_index(
            data_dir,
            {
                "id": game_id,
                "source": source_part,
                "username": user_part,
                "pgn_path": str(pgn_path),
                **metadata,
            },
        )
        existing_ids.add(game_id)
        count += 1

    return count
