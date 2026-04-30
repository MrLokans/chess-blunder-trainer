# Mate score values
import os
import pathlib
from types import MappingProxyType

MATE_SCORE_ANALYSIS = 100000  # Used in analysis engine
MATE_SCORE_WEB = 10000  # Used in web interface (lower for display)

# Blunder detection thresholds (centipawns)
MATE_THRESHOLD = 90000  # Positions with eval >= this are considered mate-in-X
ALREADY_LOST_THRESHOLD = (
    -300
)  # Player's POV: positions worse than this are "already lost"
STILL_WINNING_THRESHOLD = (
    300  # Player's POV: if eval_after still above this, advantage wasn't lost
)
MAX_CP_LOSS = (
    1500  # Cap for cp_loss: prevents mate scores (±100k) from distorting averages
)

# Mate depth classification: mates longer than this are engine-only finds,
# not realistic for beginner/intermediate players to calculate
LONG_MATE_DEPTH_THRESHOLD = 5

# Move classification values (used in database)
CLASSIFICATION_BLUNDER = 3
CLASSIFICATION_MISTAKE = 2
CLASSIFICATION_INACCURACY = 1
CLASSIFICATION_NORMAL = 0

# Ply calculation constants
PLY_WHITE_OFFSET = 2
PLY_BLACK_OFFSET = 1

DEFAULT_ENGINE_DEPTH = 11
DEFAULT_ENGINE_TIME_LIMIT = 2.0
DEFAULT_ENGINE_CONCURRENCY = 4
DEFAULT_CONCURRENCY = min(DEFAULT_ENGINE_CONCURRENCY, os.cpu_count() or 1)
DEFAULT_ENGINE_TASK_TIMEOUT = 300.0
DEFAULT_ENGINE_HASH_MB = 128

# Game phase constants
PHASE_OPENING = 0
PHASE_MIDDLEGAME = 1
PHASE_ENDGAME = 2

PHASE_LABELS = MappingProxyType({0: "opening", 1: "middlegame", 2: "endgame"})
PHASE_FROM_STRING = MappingProxyType({"opening": 0, "middlegame": 1, "endgame": 2})

# Player color constants (as stored in analysis_moves.player)
COLOR_WHITE = 0
COLOR_BLACK = 1

COLOR_LABELS = MappingProxyType({0: "white", 1: "black"})

CLASSIFICATION_LABELS = MappingProxyType(
    {
        CLASSIFICATION_NORMAL: "normal",
        CLASSIFICATION_INACCURACY: "inaccuracy",
        CLASSIFICATION_MISTAKE: "mistake",
        CLASSIFICATION_BLUNDER: "blunder",
    }
)
COLOR_FROM_STRING = MappingProxyType({"white": 0, "black": 1})

ROOT_DIR = pathlib.Path(__file__).parent.parent
DEFAULT_DATA_PATH = ROOT_DIR / "data"
DEFAULT_FIXTURES_PATH = ROOT_DIR / "fixtures"
TEMPLATES_PATH = ROOT_DIR / "templates"
DEFAULT_DB_PATH = DEFAULT_DATA_PATH / "main.sqlite3"

# Background job type identifiers. The wire-format strings stored in
# `background_jobs.job_type` and dispatched via `JOB_RUNNERS`. Centralized
# here so handler/runner/test code never repeats the string literal.
JOB_TYPE_IMPORT = "import"
JOB_TYPE_SYNC = "sync"
JOB_TYPE_ANALYZE = "analyze"
JOB_TYPE_BACKFILL_PHASES = "backfill_phases"
JOB_TYPE_BACKFILL_ECO = "backfill_eco"
JOB_TYPE_BACKFILL_TACTICS = "backfill_tactics"
JOB_TYPE_BACKFILL_TRAPS = "backfill_traps"
JOB_TYPE_DELETE_ALL_DATA = "delete_all_data"
JOB_TYPE_IMPORT_PGN = "import_pgn"

# Background job lifecycle states (stored in `background_jobs.status`).
JOB_STATUS_PENDING = "pending"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_COMPLETED = "completed"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_NO_JOBS = "no_jobs"

# Auth mode identifiers (matches `AuthMode = Literal[...]` in web/config.py).
AUTH_MODE_NONE = "none"
AUTH_MODE_CREDENTIALS = "credentials"

# Chess-platform source identifiers — match `game_index_cache.source` and
# settings keys (`lichess_username`, `chesscom_username`).
PLATFORM_LICHESS = "lichess"
PLATFORM_CHESSCOM = "chesscom"
