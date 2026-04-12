export const STORAGE_KEYS = {
  // Theme
  theme: 'theme',

  // Trainer filters
  trainerPhases: 'blunder-tutor-phase-filters',
  trainerGameTypes: 'blunder-tutor-game-type-filters',
  trainerDifficulties: 'blunder-tutor-difficulty-filters',
  trainerTactical: 'blunder-tutor-tactical-filter',
  trainerColor: 'blunder-tutor-color-filter',
  trainerFiltersCollapsed: 'blunder-tutor-filters-collapsed',
  trainerPlayFullLine: 'blunder-tutor-play-full-line',
  trainerBoardSettingsCollapsed: 'boardSettingsCollapsed',
  trainerShowCoordinates: 'blunder-tutor-show-coordinates',
  trainerResultCardPos: 'blunder-tutor-result-card-pos',

  // Dashboard filters
  dashboardDate: 'dashboard-date-filter',
  dashboardGameTypes: 'dashboard-game-type-filters',
  dashboardGamePhases: 'dashboard-game-phase-filters',

  // Import form
  importSource: 'blunder_import_source',
  importUsername: 'blunder_import_username',
  importMaxGames: 'blunder_import_maxGames',
} as const;

export const ALL_STORAGE_KEYS = Object.values(STORAGE_KEYS);
