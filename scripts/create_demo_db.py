#!/usr/bin/env python3
"""Create a sanitized demo database by obfuscating usernames and game links."""

import hashlib
import re
import shutil
import sqlite3
import sys
from pathlib import Path

SOURCE_DB = Path("data/main.sqlite3")
DEST_DB = Path("demo/demo.sqlite3")

DEMO_PLAYER = "DemoPlayer"

OPPONENT_NAMES = [
    "AlphaKnight",
    "BishopStorm",
    "CastleMaster",
    "DarkPawn",
    "EagleRook",
    "FierceQueen",
    "GrandTactic",
    "HiddenCheck",
    "IronBishop",
    "JadePawn",
    "KingSlayer",
    "LunarRook",
    "MidnightKing",
    "NobleKnight",
    "OnyxQueen",
    "PhoenixPawn",
    "QuietMove",
    "RapidStrike",
    "SilentFork",
    "TidalKnight",
    "UltraCheck",
    "VelvetBishop",
    "WildRook",
    "XenonKing",
    "YellowPawn",
    "ZephyrQueen",
    "ArcticBishop",
    "BlazeKnight",
    "CosmicRook",
    "DawnPawn",
    "EchoQueen",
    "FlintKing",
    "GlacierPawn",
    "HazeKnight",
    "IndigoRook",
    "JetBishop",
    "KryptonKing",
    "LavaQueen",
    "MistPawn",
    "NeonKnight",
    "OrbitRook",
    "PrismBishop",
    "QuasarKing",
    "RadiantPawn",
    "SolarQueen",
    "ThunderKnight",
    "UmbraRook",
    "VortexBishop",
    "WarpKing",
    "ZenithPawn",
]


def build_username_map(conn: sqlite3.Connection) -> dict[str, str]:
    cursor = conn.execute("SELECT DISTINCT username FROM game_index_cache")
    main_usernames = {row[0] for row in cursor.fetchall()}

    cursor = conn.execute(
        "SELECT DISTINCT white FROM game_index_cache UNION SELECT DISTINCT black FROM game_index_cache"
    )
    all_players = {row[0] for row in cursor.fetchall()}

    mapping: dict[str, str] = {}
    for u in main_usernames:
        mapping[u] = DEMO_PLAYER

    for opponent_idx, player in enumerate(sorted(all_players - main_usernames)):
        if opponent_idx < len(OPPONENT_NAMES):
            mapping[player] = OPPONENT_NAMES[opponent_idx]
        else:
            h = hashlib.md5(player.encode()).hexdigest()[:6]
            mapping[player] = f"Player_{h}"

    return mapping


def sanitize_pgn(pgn: str, username_map: dict[str, str]) -> str:
    def replace_header(match: re.Match) -> str:
        key = match.group(1)
        value = match.group(2)

        if key in ("White", "Black"):
            return f'[{key} "{username_map.get(value, value)}"]'

        if key == "Termination":
            new_value = value
            for real, fake in username_map.items():
                new_value = new_value.replace(real, fake)
            return f'[{key} "{new_value}"]'

        if key == "Link":
            return f'[{key} "https://example.com/game/demo"]'

        if key == "Site" and (
            "chess.com/game" in value.lower() or "lichess.org/" in value.lower()
        ):
            return f'[{key} "https://example.com/game/demo"]'

        return match.group(0)

    return re.sub(r'\[(\w+)\s+"([^"]*)"\]', replace_header, pgn)


def create_demo_db() -> None:
    if not SOURCE_DB.exists():
        print(f"Error: source database {SOURCE_DB} not found", file=sys.stderr)
        sys.exit(1)

    DEST_DB.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE_DB, DEST_DB)

    conn = sqlite3.connect(DEST_DB)
    username_map = build_username_map(conn)

    print(f"Built username map: {len(username_map)} players")
    print(f"  Main user(s) → {DEMO_PLAYER}")
    print(f"  Opponents: {len(username_map) - 1}")

    cursor = conn.execute(
        "SELECT game_id, username, white, black, pgn_content FROM game_index_cache"
    )
    rows = cursor.fetchall()
    for game_id, username, white, black, pgn_content in rows:
        new_username = username_map.get(username, username)
        new_white = username_map.get(white, white)
        new_black = username_map.get(black, black)
        new_pgn = sanitize_pgn(pgn_content, username_map)

        conn.execute(
            "UPDATE game_index_cache SET username=?, white=?, black=?, pgn_content=? WHERE game_id=?",
            (new_username, new_white, new_black, new_pgn, game_id),
        )
    print(f"  Sanitized {len(rows)} games in game_index_cache")

    conn.execute(
        "UPDATE analysis_games SET pgn_path = 'demo.pgn', engine_path = 'stockfish'"
    )
    print("  Cleared pgn_path and engine_path in analysis_games")

    cursor = conn.execute("SELECT attempt_id, username FROM puzzle_attempts")
    rows = cursor.fetchall()
    for attempt_id, username in rows:
        new_username = username_map.get(username, "local")
        conn.execute(
            "UPDATE puzzle_attempts SET username=? WHERE attempt_id=?",
            (new_username, attempt_id),
        )
    print(f"  Sanitized {len(rows)} puzzle_attempts")

    conn.execute("DELETE FROM background_jobs")
    print("  Cleared background_jobs")

    conn.execute("UPDATE app_settings SET value='' WHERE key='chesscom_username'")
    conn.execute("UPDATE app_settings SET value='' WHERE key='lichess_username'")
    conn.execute("UPDATE app_settings SET value='' WHERE key='last_sync_timestamp'")
    print("  Cleared usernames from app_settings")

    conn.commit()
    conn.execute("VACUUM")
    conn.close()

    size_kb = DEST_DB.stat().st_size / 1024
    print(f"\nDemo database created: {DEST_DB} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    create_demo_db()
