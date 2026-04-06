import { useState, useEffect } from 'preact/hooks';
import type { DatePreset } from './types';

const DATE_PRESETS: { key: DatePreset; label: string }[] = [
  { key: '7d', label: 'dashboard.filter.last_7d' },
  { key: '30d', label: 'dashboard.filter.last_30d' },
  { key: '90d', label: 'dashboard.filter.last_90d' },
  { key: '1y', label: 'dashboard.filter.last_1y' },
  { key: 'all', label: 'dashboard.filter.all_time' },
];

const GAME_TYPES = ['bullet', 'blitz', 'rapid', 'classical'] as const;
const GAME_PHASES = ['opening', 'middlegame', 'endgame'] as const;

export interface DashboardFiltersProps {
  datePreset: DatePreset | null;
  dateFrom: string | null;
  dateTo: string | null;
  gameTypes: string[];
  gamePhases: string[];
  onDatePreset: (preset: DatePreset) => void;
  onCustomDateRange: (from: string | null, to: string | null) => void;
  onClearDate: () => void;
  onGameTypesChange: (types: string[]) => void;
  onGamePhasesChange: (phases: string[]) => void;
}

export function DashboardFilters({
  datePreset,
  dateFrom,
  dateTo,
  gameTypes,
  gamePhases,
  onDatePreset,
  onCustomDateRange,
  onClearDate,
  onGameTypesChange,
  onGamePhasesChange,
}: DashboardFiltersProps) {
  const [collapsed, setCollapsed] = useState(true);
  const [customDateOpen, setCustomDateOpen] = useState(false);
  const [localFrom, setLocalFrom] = useState(dateFrom ?? '');
  const [localTo, setLocalTo] = useState(dateTo ?? '');

  useEffect(() => { setLocalFrom(dateFrom ?? ''); }, [dateFrom]);
  useEffect(() => { setLocalTo(dateTo ?? ''); }, [dateTo]);

  function toggleCollapsed() {
    setCollapsed(c => !c);
  }

  function toggleCustomDate() {
    setCustomDateOpen(o => !o);
  }

  function handlePresetClick(preset: DatePreset) {
    onDatePreset(preset);
  }

  function handleApplyDate() {
    onCustomDateRange(localFrom || null, localTo || null);
  }

  function handleClearDate() {
    setLocalFrom('');
    setLocalTo('');
    onClearDate();
  }

  function handleGameTypeChange(type: string, checked: boolean) {
    const next = checked
      ? [...gameTypes, type]
      : gameTypes.filter(t => t !== type);
    onGameTypesChange(next);
  }

  function handleGamePhaseChange(phase: string, checked: boolean) {
    const next = checked
      ? [...gamePhases, phase]
      : gamePhases.filter(p => p !== phase);
    onGamePhasesChange(next);
  }

  return (
    <div class="dashboard-filter-bar">
      <div class="filter-bar-header" onClick={toggleCollapsed}>
        <span class="filter-bar-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
          </svg>
          {t('dashboard.filter.title')}
        </span>
        <svg
          class={`chevron-icon${collapsed ? ' collapsed' : ''}`}
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>

      <div class={`filter-bar-body${collapsed ? ' collapsed' : ''}`}>
        <div class="filter-bar-row filter-bar-presets">
          <div class="filter-presets">
            {DATE_PRESETS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                data-preset={key}
                class={datePreset === key ? 'active' : undefined}
                onClick={() => { handlePresetClick(key); }}
              >
                {t(label)}
              </button>
            ))}
          </div>
          <button type="button" class="filter-bar-custom-toggle" onClick={toggleCustomDate}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="4" width="18" height="18" rx="0" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            {t('dashboard.filter.custom_range')}
          </button>
        </div>

        <div class={`filter-bar-row filter-bar-dates${customDateOpen ? '' : ' collapsed'}`}>
          <div class="filter-group">
            <label for="dateFrom">{t('dashboard.filter.from')}</label>
            <input
              type="date"
              id="dateFrom"
              name="date_from"
              value={localFrom}
              onInput={(e) => { setLocalFrom(e.currentTarget.value); }}
            />
          </div>
          <div class="filter-group">
            <label for="dateTo">{t('dashboard.filter.to')}</label>
            <input
              type="date"
              id="dateTo"
              name="date_to"
              value={localTo}
              onInput={(e) => { setLocalTo(e.currentTarget.value); }}
            />
          </div>
          <div class="filter-group">
            <button type="button" class="btn btn-primary btn-sm" onClick={handleApplyDate}>
              {t('common.apply')}
            </button>
            <button type="button" class="btn btn-sm" onClick={handleClearDate}>
              {t('common.clear')}
            </button>
          </div>
        </div>

        <div class="filter-bar-row filter-bar-chips">
          <div class="filter-chip-group">
            <span class="filter-chip-label">{t('dashboard.filter.time_control')}</span>
            {GAME_TYPES.map(type => (
              <label key={type} class="filter-checkbox-label">
                <input
                  type="checkbox"
                  class="game-type-filter"
                  value={type}
                  checked={gameTypes.includes(type)}
                  onChange={(e) => { handleGameTypeChange(type, e.currentTarget.checked); }}
                />
                {t(`trainer.game_type.${type}`)}
              </label>
            ))}
          </div>
          <div class="filter-chip-divider" />
          <div class="filter-chip-group">
            <span class="filter-chip-label">{t('dashboard.filter.game_phase')}</span>
            {GAME_PHASES.map(phase => (
              <label key={phase} class="filter-checkbox-label">
                <input
                  type="checkbox"
                  class="game-phase-filter"
                  value={phase}
                  checked={gamePhases.includes(phase)}
                  onChange={(e) => { handleGamePhaseChange(phase, e.currentTarget.checked); }}
                />
                {t(`chess.phase.${phase}`)}
              </label>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
