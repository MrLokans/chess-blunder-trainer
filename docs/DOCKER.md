# Docker Deployment

## Quick Start

### Docker Run

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data ghcr.io/mrlokans/blunder-tutor:latest
```

### Docker Compose

```bash
git clone https://github.com/MrLokans/chess-blunder-trainer.git
cd chess-blunder-trainer
docker compose up -d
```

Open http://localhost:8000 and enter your username.

Supports `linux/amd64` and `linux/arm64` (Apple Silicon, Raspberry Pi).

## Configuration

Optionally create a `.env` file (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `LICHESS_USERNAME` | — | Your Lichess username |
| `CHESSCOM_USERNAME` | — | Your Chess.com username |
| `STOCKFISH_DEPTH` | `14` | Engine search depth (10–20). Higher = more accurate, slower |
| `PORT` | `8000` | Server port |

Usernames can also be set through the web UI on first launch.

## Data Persistence

All data lives in `/app/data` inside the container. The `-v $(pwd)/data:/app/data` mount keeps it across restarts.

**Backup:**

```bash
tar -czf blunder-tutor-backup-$(date +%Y%m%d).tar.gz data/
```

## Updating

```bash
docker pull ghcr.io/mrlokans/blunder-tutor:latest
docker compose down && docker compose up -d
```

Database migrations run automatically on startup.

## Troubleshooting

**Container won't start** — check logs with `docker compose logs blunder-tutor`

**Analysis is slow** — lower `STOCKFISH_DEPTH` to 10–12 in `.env`

**Port conflict** — change the host port: `-p 8080:8000`
