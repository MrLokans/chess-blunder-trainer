#!/usr/bin/env python3
"""
Download chess piece sets from Lichess assets (MIT licensed).

Lichess serves SVGs at: https://lichess.org/assets/piece/{set}/{piece}.svg
Modern browsers and chessboard.js fully support SVG pieces.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

PIECE_SETS = [
    # Classic/Traditional styles
    "alpha",  # Clean traditional
    "california",  # Popular on chess.com
    "cardinal",  # Classic red accents
    "cburnett",  # Lichess default, very popular
    "merida",  # Traditional tournament style
    "staunty",  # Classic Staunton design
    "tatiana",  # Elegant traditional
    "leipzig",  # German classical style
    "dubrovny",  # Classic wooden look
    # Modern/Clean styles
    "maestro",  # Professional modern
    "chessnut",  # Clean wooden style
    "companion",  # Modern companion pieces
    "kosal",  # Elegant modern
    "fresca",  # Fresh modern look
    "gioco",  # Italian modern style
    # Artistic/Unique styles
    "horsey",  # Fun distinctive knight
    "pirouetti",  # Artistic ballet style
    "spatial",  # 3D-like appearance
    "mono",  # Minimalist monochrome
    "pixel",  # Retro pixel art
    "letter",  # Letter-based pieces (K, Q, R, B, N, P)
    "shapes",  # Geometric shapes
]

PIECES = ["wK", "wQ", "wR", "wB", "wN", "wP", "bK", "bQ", "bR", "bB", "bN", "bP"]

LICHESS_BASE_URL = "https://lichess.org/assets/piece"


async def download_piece(client: httpx.AsyncClient, set_name: str, piece: str) -> bytes:
    url = f"{LICHESS_BASE_URL}/{set_name}/{piece}.svg"
    response = await client.get(url, follow_redirects=True)
    response.raise_for_status()
    return response.content


async def download_piece_set(
    client: httpx.AsyncClient, set_name: str, output_dir: Path
) -> None:
    set_dir = output_dir / set_name
    set_dir.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {set_name}...")

    for piece in PIECES:
        try:
            svg_data = await download_piece(client, set_name, piece)
            output_path = set_dir / f"{piece}.svg"
            output_path.write_bytes(svg_data)
            print(f"  ✓ {piece}")
        except Exception as e:
            print(f"  ✗ {piece}: {e}")


async def main() -> None:
    script_dir = Path(__file__).parent
    output_dir = script_dir.parent / "web" / "static" / "pieces"

    print(f"Output directory: {output_dir}")
    print(f"Downloading {len(PIECE_SETS)} piece sets...\n")

    async with httpx.AsyncClient(timeout=5.0) as client:
        for set_name in PIECE_SETS:
            await download_piece_set(client, set_name, output_dir)
            print()

    print("Done!")
    print("\nAvailable piece sets:")
    for set_name in ["wikipedia"] + PIECE_SETS:
        set_path = output_dir / set_name
        if set_path.exists():
            piece_count = len(list(set_path.glob("*.svg"))) + len(
                list(set_path.glob("*.png"))
            )
            print(f"  - {set_name} ({piece_count} pieces)")


if __name__ == "__main__":
    asyncio.run(main())
