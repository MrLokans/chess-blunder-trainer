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

    TRAINER_FILTER_DIFFICULTY = "trainer.filter.difficulty"

    AUTO_SYNC = "auto.sync"
    AUTO_ANALYZE = "auto.analyze"

    @classmethod
    def is_valid(cls, value: str) -> bool:
        return value in cls._value2member_map_


DEFAULTS: dict[Feature, bool] = dict.fromkeys(Feature, True)

FEATURE_GROUPS: list[tuple[str, list[Feature]]] = [
    (
        "settings.features.group.pages",
        [
            Feature.PAGE_DASHBOARD,
            Feature.PAGE_MANAGEMENT,
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
        ],
    ),
    (
        "settings.features.group.automation",
        [
            Feature.AUTO_SYNC,
            Feature.AUTO_ANALYZE,
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
    Feature.TRAINER_FILTER_DIFFICULTY: "settings.features.trainer_filter_difficulty",
    Feature.AUTO_SYNC: "settings.features.auto_sync",
    Feature.AUTO_ANALYZE: "settings.features.auto_analyze",
}
