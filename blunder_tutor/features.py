from __future__ import annotations

from enum import StrEnum


class Feature(StrEnum):
    PAGE_DASHBOARD = "page.dashboard"
    PAGE_MANAGEMENT = "page.management"

    TRAINER_THREATS = "trainer.threats"
    TRAINER_TACTICS = "trainer.tactics"
    TRAINER_FILTER_PHASE = "trainer.filter.phase"
    TRAINER_FILTER_TACTICAL = "trainer.filter.tactical"

    DASHBOARD_HEATMAP = "dashboard.heatmap"
    DASHBOARD_PHASE_BREAKDOWN = "dashboard.phase_breakdown"
    DASHBOARD_OPENING_BREAKDOWN = "dashboard.opening_breakdown"
    DASHBOARD_TACTICAL_BREAKDOWN = "dashboard.tactical_breakdown"
    DASHBOARD_ACCURACY = "dashboard.accuracy"
    DASHBOARD_DIFFICULTY_BREAKDOWN = "dashboard.difficulty_breakdown"
    DASHBOARD_CONVERSION_RESILIENCE = "dashboard.conversion_resilience"
    DASHBOARD_COLLAPSE_POINT = "dashboard.collapse_point"
    DASHBOARD_TRAPS = "dashboard.traps"
    DASHBOARD_GROWTH = "dashboard.growth"

    TRAINER_FILTER_DIFFICULTY = "trainer.filter.difficulty"

    PAGE_IMPORT = "page.import"

    AUTO_SYNC = "auto.sync"
    AUTO_ANALYZE = "auto.analyze"

    STARRED_PUZZLES = "starred.puzzles"

    DEBUG_COPY = "debug.copy"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._value2member_map_


DEFAULTS: dict[Feature, bool] = {
    **dict.fromkeys(Feature, True),
    Feature.DASHBOARD_TRAPS: False,
    Feature.PAGE_IMPORT: False,
    Feature.STARRED_PUZZLES: False,
    Feature.DEBUG_COPY: False,
}

FEATURE_GROUPS: list[tuple[str, list[Feature]]] = [
    (
        "settings.features.group.pages",
        [
            Feature.PAGE_DASHBOARD,
            Feature.PAGE_MANAGEMENT,
            Feature.PAGE_IMPORT,
        ],
    ),
    (
        "settings.features.group.trainer",
        [
            Feature.TRAINER_THREATS,
            Feature.TRAINER_TACTICS,
            Feature.TRAINER_FILTER_PHASE,
            Feature.TRAINER_FILTER_TACTICAL,
            Feature.TRAINER_FILTER_DIFFICULTY,
            Feature.STARRED_PUZZLES,
        ],
    ),
    (
        "settings.features.group.dashboard",
        [
            Feature.DASHBOARD_HEATMAP,
            Feature.DASHBOARD_PHASE_BREAKDOWN,
            Feature.DASHBOARD_OPENING_BREAKDOWN,
            Feature.DASHBOARD_TACTICAL_BREAKDOWN,
            Feature.DASHBOARD_ACCURACY,
            Feature.DASHBOARD_DIFFICULTY_BREAKDOWN,
            Feature.DASHBOARD_CONVERSION_RESILIENCE,
            Feature.DASHBOARD_COLLAPSE_POINT,
            Feature.DASHBOARD_TRAPS,
            Feature.DASHBOARD_GROWTH,
        ],
    ),
    (
        "settings.features.group.automation",
        [
            Feature.AUTO_SYNC,
            Feature.AUTO_ANALYZE,
        ],
    ),
    (
        "settings.features.group.developer",
        [
            Feature.DEBUG_COPY,
        ],
    ),
]

FEATURE_LABELS: dict[Feature, str] = {
    Feature.PAGE_DASHBOARD: "settings.features.page_dashboard",
    Feature.PAGE_MANAGEMENT: "settings.features.page_management",
    Feature.TRAINER_THREATS: "settings.features.trainer_threats",
    Feature.TRAINER_TACTICS: "settings.features.trainer_tactics",
    Feature.TRAINER_FILTER_PHASE: "settings.features.trainer_filter_phase",
    Feature.TRAINER_FILTER_TACTICAL: "settings.features.trainer_filter_tactical",
    Feature.DASHBOARD_HEATMAP: "settings.features.dashboard_heatmap",
    Feature.DASHBOARD_PHASE_BREAKDOWN: "settings.features.dashboard_phase_breakdown",
    Feature.DASHBOARD_OPENING_BREAKDOWN: "settings.features.dashboard_opening_breakdown",
    Feature.DASHBOARD_TACTICAL_BREAKDOWN: "settings.features.dashboard_tactical_breakdown",
    Feature.DASHBOARD_ACCURACY: "settings.features.dashboard_accuracy",
    Feature.DASHBOARD_DIFFICULTY_BREAKDOWN: "settings.features.dashboard_difficulty_breakdown",
    Feature.DASHBOARD_CONVERSION_RESILIENCE: "settings.features.dashboard_conversion_resilience",
    Feature.DASHBOARD_COLLAPSE_POINT: "settings.features.dashboard_collapse_point",
    Feature.DASHBOARD_TRAPS: "settings.features.dashboard_traps",
    Feature.DASHBOARD_GROWTH: "settings.features.dashboard_growth",
    Feature.TRAINER_FILTER_DIFFICULTY: "settings.features.trainer_filter_difficulty",
    Feature.PAGE_IMPORT: "settings.features.page_import",
    Feature.AUTO_SYNC: "settings.features.auto_sync",
    Feature.AUTO_ANALYZE: "settings.features.auto_analyze",
    Feature.STARRED_PUZZLES: "settings.features.starred_puzzles",
    Feature.DEBUG_COPY: "settings.features.debug_copy",
}
