from __future__ import annotations

from types import MappingProxyType

from pydantic import BaseModel, Field

# Settings request validation bounds.
SYNC_INTERVAL_MAX_HOURS = 168  # 1 week
MAX_GAMES_CEILING = 10_000  # safety cap on sync size
SPACED_REPETITION_DAYS_DEFAULT = 30
SPACED_REPETITION_DAYS_MAX = 365


class ThemeColors(BaseModel):
    primary: str = Field(default="#4f6d7a", description="Primary accent color")
    success: str = Field(default="#3d8b6e", description="Success/positive color")
    error: str = Field(default="#c25450", description="Error/danger color")
    warning: str = Field(default="#b8860b", description="Warning color")
    phase_opening: str = Field(default="#5b8a9a", description="Opening phase color")
    phase_middlegame: str = Field(
        default="#9a7b5b", description="Middlegame phase color"
    )
    phase_endgame: str = Field(default="#7a5b9a", description="Endgame phase color")
    bg: str = Field(default="#f1f5f9", description="Page background color")
    bg_card: str = Field(default="#ffffff", description="Card background color")
    text: str = Field(default="#1e293b", description="Primary text color")
    text_muted: str = Field(default="#64748b", description="Muted/secondary text color")
    heatmap_empty: str = Field(default="#ebedf0", description="Heatmap empty cell")
    heatmap_l1: str = Field(default="#9be9a8", description="Heatmap level 1 (low)")
    heatmap_l2: str = Field(default="#40c463", description="Heatmap level 2")
    heatmap_l3: str = Field(default="#30a14e", description="Heatmap level 3")
    heatmap_l4: str = Field(default="#216e39", description="Heatmap level 4 (high)")


class SettingsRequest(BaseModel):
    auto_sync: bool = Field(default=False, description="Enable automatic game sync")
    sync_interval: int = Field(
        default=24,
        ge=1,
        le=SYNC_INTERVAL_MAX_HOURS,
        description="Sync interval in hours",
    )
    max_games: int = Field(
        default=100, ge=1, le=MAX_GAMES_CEILING, description="Maximum games to sync"
    )
    auto_analyze: bool = Field(
        default=True, description="Automatically analyze new games"
    )
    spaced_repetition_days: int = Field(
        default=SPACED_REPETITION_DAYS_DEFAULT,
        ge=1,
        le=SPACED_REPETITION_DAYS_MAX,
        description="Days before repeating solved puzzles",
    )
    theme: ThemeColors | None = Field(default=None, description="Theme color settings")


class SettingsResponse(BaseModel):
    lichess_username: str | None = Field(None, description="Lichess username")
    chesscom_username: str | None = Field(None, description="Chess.com username")
    auto_sync: bool = Field(default=False, description="Auto sync enabled")
    sync_interval: int = Field(default=24, description="Sync interval in hours")
    max_games: int = Field(default=100, description="Max games to sync")
    auto_analyze: bool = Field(default=True, description="Auto analyze new games")
    spaced_repetition_days: int = Field(
        default=SPACED_REPETITION_DAYS_DEFAULT, description="Spaced repetition days"
    )


class ThemePreset(BaseModel):
    id: str = Field(description="Preset identifier")
    name: str = Field(description="Display name")
    description: str = Field(description="Short description")
    colors: ThemeColors = Field(description="Theme colors")


class ThemePresetsResponse(BaseModel):
    presets: list[ThemePreset] = Field(description="Available theme presets")


class PieceSetInfo(BaseModel):
    id: str = Field(description="Piece set identifier")
    name: str = Field(description="Display name")
    format: str = Field(description="Image format (png or svg)")


class BoardColorPreset(BaseModel):
    id: str = Field(description="Preset identifier")
    name: str = Field(description="Display name")
    light: str = Field(description="Light square color")
    dark: str = Field(description="Dark square color")


class BoardSettingsResponse(BaseModel):
    piece_set: str = Field(description="Current piece set ID")
    board_light: str = Field(description="Light square color")
    board_dark: str = Field(description="Dark square color")


class BoardSettingsRequest(BaseModel):
    piece_set: str | None = Field(default=None, description="Piece set ID")
    board_light: str | None = Field(default=None, description="Light square color")
    board_dark: str | None = Field(default=None, description="Dark square color")


class PieceSetsResponse(BaseModel):
    piece_sets: list[PieceSetInfo] = Field(description="Available piece sets")


class BoardColorPresetsResponse(BaseModel):
    presets: list[BoardColorPreset] = Field(description="Available board color presets")


class FeatureFlagsResponse(BaseModel):
    features: dict[str, bool] = Field(description="Feature visibility flags")


class FeatureFlagsRequest(BaseModel):
    features: dict[str, bool] = Field(description="Feature flags to update")


class LocaleRequest(BaseModel):
    locale: str = Field(description="Locale code (e.g., 'en', 'ru')")


class DeleteAllResponse(BaseModel):
    job_id: str = Field(description="Job ID for tracking the delete operation")


DEFAULT_THEME = MappingProxyType(
    {
        "primary": "#1A3A8F",
        "success": "#2D8F3E",
        "error": "#D42828",
        "warning": "#F2C12E",
        "phase_opening": "#1A3A8F",
        "phase_middlegame": "#F2C12E",
        "phase_endgame": "#3A3A3A",
        "bg": "#F5F2EB",
        "bg_card": "#F5F2EB",
        "text": "#1A1A1A",
        "text_muted": "#3A3A3A",
        "heatmap_empty": "#E8E4DB",
        "heatmap_l1": "#B8D9CA",
        "heatmap_l2": "#5BAA7D",
        "heatmap_l3": "#2D8F3E",
        "heatmap_l4": "#1A6B2A",
    }
)

THEME_PRESETS = MappingProxyType(
    {
        "default": {
            "name": "Default",
            "description": "Muted slate tones for a calm, professional look",
            "colors": DEFAULT_THEME,
        },
        "ocean": {
            "name": "Ocean",
            "description": "Deep blue Bauhaus with cool undertones",
            "colors": {
                "primary": "#0B4F6C",
                "success": "#2A9D8F",
                "error": "#C43A31",
                "warning": "#E9C46A",
                "phase_opening": "#0B4F6C",
                "phase_middlegame": "#E9C46A",
                "phase_endgame": "#264653",
                "bg": "#EFF6F2",
                "bg_card": "#EFF6F2",
                "text": "#0A1628",
                "text_muted": "#3A5060",
                "heatmap_empty": "#D6E8E0",
                "heatmap_l1": "#7DD3C0",
                "heatmap_l2": "#2A9D8F",
                "heatmap_l3": "#1A7A6E",
                "heatmap_l4": "#0F5A52",
            },
        },
        "forest": {
            "name": "Forest",
            "description": "Earth tones with structural warmth",
            "colors": {
                "primary": "#2D6A4F",
                "success": "#40916C",
                "error": "#9B2226",
                "warning": "#BC6C25",
                "phase_opening": "#2D6A4F",
                "phase_middlegame": "#BC6C25",
                "phase_endgame": "#4A3728",
                "bg": "#F5F2ED",
                "bg_card": "#F5F2ED",
                "text": "#1B2E20",
                "text_muted": "#4A5E4A",
                "heatmap_empty": "#D8E8DC",
                "heatmap_l1": "#95D5B2",
                "heatmap_l2": "#52B788",
                "heatmap_l3": "#2D6A4F",
                "heatmap_l4": "#1B4332",
            },
        },
        "sunset": {
            "name": "Sunset",
            "description": "Warm reds and amber accents",
            "colors": {
                "primary": "#B83B1D",
                "success": "#2D8040",
                "error": "#8B1A1A",
                "warning": "#D4920A",
                "phase_opening": "#B83B1D",
                "phase_middlegame": "#D4920A",
                "phase_endgame": "#5C2E10",
                "bg": "#FBF5ED",
                "bg_card": "#FBF5ED",
                "text": "#2C1810",
                "text_muted": "#6B4E3A",
                "heatmap_empty": "#F5E6D0",
                "heatmap_l1": "#F0C888",
                "heatmap_l2": "#E0A050",
                "heatmap_l3": "#C07820",
                "heatmap_l4": "#8B5510",
            },
        },
        "lavender": {
            "name": "Lavender",
            "description": "Muted purples with geometric clarity",
            "colors": {
                "primary": "#5B2D8E",
                "success": "#2D7A50",
                "error": "#A82828",
                "warning": "#C4960A",
                "phase_opening": "#5B2D8E",
                "phase_middlegame": "#C4960A",
                "phase_endgame": "#3A2060",
                "bg": "#F5F2F8",
                "bg_card": "#F5F2F8",
                "text": "#1E1830",
                "text_muted": "#5A4E6A",
                "heatmap_empty": "#E8E0F0",
                "heatmap_l1": "#C4B0E0",
                "heatmap_l2": "#9A78C8",
                "heatmap_l3": "#5B2D8E",
                "heatmap_l4": "#3A1860",
            },
        },
        "monochrome": {
            "name": "Monochrome",
            "description": "Pure black and white, maximum structure",
            "colors": {
                "primary": "#1A1A1A",
                "success": "#3A3A3A",
                "error": "#1A1A1A",
                "warning": "#5A5A5A",
                "phase_opening": "#5A5A5A",
                "phase_middlegame": "#3A3A3A",
                "phase_endgame": "#1A1A1A",
                "bg": "#F0F0F0",
                "bg_card": "#F0F0F0",
                "text": "#0A0A0A",
                "text_muted": "#4A4A4A",
                "heatmap_empty": "#E0E0E0",
                "heatmap_l1": "#A0A0A0",
                "heatmap_l2": "#707070",
                "heatmap_l3": "#404040",
                "heatmap_l4": "#1A1A1A",
            },
        },
        "dark": {
            "name": "Dark",
            "description": "Inverted Bauhaus for low light",
            "colors": {
                "primary": "#5B8FD4",
                "success": "#4AAF6A",
                "error": "#E05050",
                "warning": "#F2C12E",
                "phase_opening": "#5B8FD4",
                "phase_middlegame": "#F2C12E",
                "phase_endgame": "#8A8A8A",
                "bg": "#1A1A1A",
                "bg_card": "#2A2A2A",
                "text": "#F0EDE6",
                "text_muted": "#8A8A80",
                "heatmap_empty": "#2A2A2A",
                "heatmap_l1": "#1A4A2A",
                "heatmap_l2": "#2A6A3A",
                "heatmap_l3": "#3A8A4A",
                "heatmap_l4": "#4AAF6A",
            },
        },
        "high_contrast": {
            "name": "High Contrast",
            "description": "Maximum readability with Bauhaus colors",
            "colors": {
                "primary": "#0000CC",
                "success": "#006B00",
                "error": "#CC0000",
                "warning": "#CC8800",
                "phase_opening": "#0000CC",
                "phase_middlegame": "#CC8800",
                "phase_endgame": "#333333",
                "bg": "#FFFFFF",
                "bg_card": "#FFFFFF",
                "text": "#000000",
                "text_muted": "#333333",
                "heatmap_empty": "#D0D0D0",
                "heatmap_l1": "#80CC80",
                "heatmap_l2": "#40AA40",
                "heatmap_l3": "#208020",
                "heatmap_l4": "#005500",
            },
        },
    }
)

THEME_KEYS = tuple(DEFAULT_THEME.keys())


PIECE_SETS = (
    {"id": "alpha", "name": "Alpha", "format": "svg"},
    {"id": "california", "name": "California", "format": "svg"},
    {"id": "cardinal", "name": "Cardinal", "format": "svg"},
    {"id": "cburnett", "name": "CBurnett", "format": "svg"},
    {"id": "chessnut", "name": "Chessnut", "format": "svg"},
    {"id": "companion", "name": "Companion", "format": "svg"},
    {"id": "fresca", "name": "Fresca", "format": "svg"},
    {"id": "gioco", "name": "Gioco", "format": "svg"},
    {"id": "kosal", "name": "Kosal", "format": "svg"},
    {"id": "leipzig", "name": "Leipzig", "format": "svg"},
    {"id": "letter", "name": "Letter", "format": "svg"},
    {"id": "maestro", "name": "Maestro", "format": "svg"},
    {"id": "merida", "name": "Merida", "format": "svg"},
    {"id": "shapes", "name": "Shapes", "format": "svg"},
    {"id": "staunty", "name": "Staunty", "format": "svg"},
    {"id": "tatiana", "name": "Tatiana", "format": "svg"},
)

DEFAULT_PIECE_SET = "gioco"
DEFAULT_BOARD_LIGHT = "#E0E0E0"
DEFAULT_BOARD_DARK = "#A0A0A0"

BOARD_COLOR_PRESETS = MappingProxyType(
    {
        "brown": {"name": "Brown", "light": "#f0d9b5", "dark": "#b58863"},
        "blue": {"name": "Blue", "light": "#dee3e6", "dark": "#8ca2ad"},
        "green": {"name": "Green", "light": "#ffffdd", "dark": "#86a666"},
        "purple": {"name": "Purple", "light": "#e8e0f0", "dark": "#9070a0"},
        "gray": {"name": "Gray", "light": "#e0e0e0", "dark": "#a0a0a0"},
        "wood": {"name": "Wood", "light": "#e6d3ac", "dark": "#b88b4a"},
    }
)
