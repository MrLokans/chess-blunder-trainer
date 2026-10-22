# Docker Deployment

## Quick Start

Requires [Docker](https://docs.docker.com/get-docker/) (check with `docker --version`). Stockfish is bundled in the image; nothing else needs installing.

### Docker Run

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data ghcr.io/mrlokans/blunder-tutor:latest
```

On Windows PowerShell use `-v ${PWD}/data:/app/data` instead.

### Docker Compose

`docker-compose.yml` builds the image from source (including compiling Stockfish), so the first `up` takes several minutes. Use Docker Run above if you just want the published image.

```bash
git clone https://github.com/MrLokans/chess-blunder-trainer.git
cd chess-blunder-trainer
docker compose up -d
```

Check it's up with `curl http://localhost:8000/health`, then open http://localhost:8000 and enter your username. Games are imported and analyzed in the background — the first run takes a while. Puzzles appear in the trainer as analysis finishes; job progress is on the **Management** page.

Supports `linux/amd64` and `linux/arm64` (Apple Silicon, Raspberry Pi).

## Configuration

Optionally create a `.env` file next to `docker-compose.yml`:

```bash
cp .env.example .env
```

Commonly set variables (the full list is in [`environment.md`](environment.md)):

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

**Host ownership:** the image runs as UID/GID 1000 (`appuser`). If your host `./data` directory is owned by a different UID, either `chown -R 1000:1000 data/` once, override `user:` in `docker-compose.yml`, or run `docker run --user $(id -u):$(id -g) ...`.

## Updating

Docker Run — pull the new image, then remove and re-run the container (data in `./data` is kept):

```bash
docker pull ghcr.io/mrlokans/blunder-tutor:latest
docker rm -f <container>
docker run -p 8000:8000 -v $(pwd)/data:/app/data ghcr.io/mrlokans/blunder-tutor:latest
```

Docker Compose — it builds from source, so update the checkout and rebuild:

```bash
git pull
docker compose up -d --build
```

Database migrations run automatically on startup.

## Troubleshooting

**Container won't start** — check logs with `docker compose logs blunder-tutor`

**Analysis is slow** — lower `STOCKFISH_DEPTH` to 10–12 in `.env`

**Port conflict** — change the host port: `-p 8080:8000`

**Permission denied writing to `/app/data`** — the host `./data` directory isn't writable by UID 1000; see **Host ownership** above.

**Trainer says "No puzzles available"** — import games first, or wait for analysis to finish (progress on the Management page).
