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
DEFAULT_ENGINE_TIME_LIMIT = 3.0

ROOT_DIR = pathlib.Path(__file__).parent.parent
DEFAULT_DATA_PATH = ROOT_DIR / "data"
TEMPLATES_PATH = ROOT_DIR / "templates"
DEFAULT_DB_PATH = DEFAULT_DATA_PATH / "main.sqlite3"
