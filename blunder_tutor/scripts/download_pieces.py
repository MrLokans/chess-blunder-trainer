from pathlib import Path

import httpx

PIECES = ["wK", "wQ", "wR", "wB", "wN", "wP", "bK", "bQ", "bR", "bB", "bN", "bP"]
BASE_URL = "https://chessboardjs.com/img/chesspieces/wikipedia"


def download_pieces(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    for piece in PIECES:
        url = f"{BASE_URL}/{piece}.png"
        output_path = output_dir / f"{piece}.png"
        print(f"Downloading {piece}.png...")
        response = httpx.get(url)
        response.raise_for_status()
        output_path.write_bytes(response.content)
    print("All pieces downloaded!")


if __name__ == "__main__":
    pieces_dir = (
        Path(__file__).parent.parent / "web" / "static" / "pieces" / "wikipedia"
    )
    download_pieces(pieces_dir)
