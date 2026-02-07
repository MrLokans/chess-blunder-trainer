#!/usr/bin/env python3
"""Download missing chess piece sets from Lichess."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

PIECES = ["wK", "wQ", "wR", "wB", "wN", "wP", "bK", "bQ", "bR", "bB", "bN", "bP"]
LICHESS_BASE_URL = "https://lichess.org/assets/piece"

# Sets we want to have
WANTED_SETS = [
    "alpha",
    "california",
    "cardinal",
    "cburnett",
    "merida",
    "staunty",
    "tatiana",
    "leipzig",
    "dubrovny",
    "maestro",
    "chessnut",
    "companion",
    "kosal",
    "fresca",
    "gioco",
    "horsey",
    "pirouetti",
    "spatial",
    "mono",
    "pixel",
    "letter",
    "shapes",
]


async def download_piece(
    client: httpx.AsyncClient, set_name: str, piece: str, output_dir: Path
) -> bool:
    output_path = output_dir / set_name / f"{piece}.svg"
    if output_path.exists():
        return True

    url = f"{LICHESS_BASE_URL}/{set_name}/{piece}.svg"
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)
        return True
    except Exception as e:
        print(f"  ✗ {set_name}/{piece}: {e}")
        return False


async def main() -> None:
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "web" / "static" / "pieces"

    headers = {
        "User-Agent": "BlunderTutor/1.0 (https://github.com/mrlokans/blunder-tutor; Chess training app)"
    }
    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        for set_name in WANTED_SETS:
            set_dir = output_dir / set_name
            existing = len(list(set_dir.glob("*.svg"))) if set_dir.exists() else 0

            if existing == 12:
                print(f"✓ {set_name} (complete)")
                continue

            print(f"Downloading {set_name} ({existing}/12 pieces)...")

            tasks = [
                download_piece(client, set_name, piece, output_dir) for piece in PIECES
            ]
            results = await asyncio.gather(*tasks)
            success = sum(results)
            print(f"  Downloaded {success}/12 pieces")

    print("\nFinal status:")
    for set_name in ["wikipedia"] + WANTED_SETS:
        set_path = output_dir / set_name
        if set_path.exists():
            count = len(list(set_path.glob("*.svg"))) + len(
                list(set_path.glob("*.png"))
            )
            status = "✓" if count == 12 else "✗"
            print(f"  {status} {set_name}: {count}/12 pieces")


if __name__ == "__main__":
    asyncio.run(main())
