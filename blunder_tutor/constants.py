# Mate score values
import pathlib

MATE_SCORE_ANALYSIS = 100000  # Used in analysis engine
MATE_SCORE_WEB = 10000  # Used in web interface (lower for display)

# Blunder detection thresholds (centipawns)
MATE_THRESHOLD = 90000  # Positions with eval >= this are considered mate-in-X

# Move classification values (used in database)
CLASSIFICATION_BLUNDER = 3
CLASSIFICATION_MISTAKE = 2
CLASSIFICATION_INACCURACY = 1
CLASSIFICATION_NORMAL = 0

# Ply calculation constants
PLY_WHITE_OFFSET = 2
PLY_BLACK_OFFSET = 1

DEFAULT_ENGINE_DEPTH = 14
DEFAULT_ENGINE_TIME_LIMIT = 2.0
DEFAULT_ENGINE_CONCURRENCY = 4

# Game phase constants
PHASE_OPENING = 0
PHASE_MIDDLEGAME = 1
PHASE_ENDGAME = 2

PHASE_LABELS = {0: "opening", 1: "middlegame", 2: "endgame"}
PHASE_FROM_STRING = {"opening": 0, "middlegame": 1, "endgame": 2}

# Player color constants (as stored in analysis_moves.player)
COLOR_WHITE = 0
COLOR_BLACK = 1

COLOR_LABELS = {0: "white", 1: "black"}
COLOR_FROM_STRING = {"white": 0, "black": 1}

ROOT_DIR = pathlib.Path(__file__).parent.parent
DEFAULT_DATA_PATH = ROOT_DIR / "data"
DEFAULT_FIXTURES_PATH = ROOT_DIR / "fixtures"
TEMPLATES_PATH = ROOT_DIR / "templates"
DEFAULT_DB_PATH = DEFAULT_DATA_PATH / "main.sqlite3"
