import type { FiltersAPI } from '../hooks/useFilters';
import { useFeature } from '../../hooks/useFeature';
import { GAME_TYPES, GAME_PHASES, DIFFICULTIES } from '../../shared/constants';

interface FiltersPanelProps {
  filters: FiltersAPI;
}
const TACTICAL_PATTERNS = [
  { value: 'fork', key: 'trainer.filters.tactical_fork' },
  { value: 'pin', key: 'trainer.filters.tactical_pin' },
  { value: 'hanging_piece', key: 'trainer.filters.tactical_hanging' },
  { value: 'skewer', key: 'trainer.filters.tactical_skewer' },
  { value: 'discovered_attack', key: 'trainer.filters.tactical_discovery' },
] as const;

function CheckboxGroup({ items, selected, onChange, labelPrefix }: {
  items: readonly string[];
  selected: string[];
  onChange: (values: string[]) => void;
  labelPrefix: string;
}): preact.JSX.Element {
  const toggle = (item: string) => {
    const next = selected.includes(item)
      ? selected.filter(v => v !== item)
      : [...selected, item];
    onChange(next);
  };

  return (
    <>
      {items.map(item => (
        <label key={item} class="filter-checkbox-label">
          <input
            type="checkbox"
            checked={selected.includes(item)}
            onChange={() => { toggle(item); }}
          />
          {t(`${labelPrefix}.${item}`)}
        </label>
      ))}
    </>
  );
}

const ChevronSvg = ({ collapsed }: { collapsed: boolean }) => (
  <svg class={`chevron-icon ${collapsed ? 'collapsed' : ''}`} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <polyline points="6 9 12 15 18 9" />
  </svg>
);

export function FiltersPanel({ filters }: FiltersPanelProps): preact.JSX.Element {
  const { state } = filters;
  const hasTactics = useFeature('trainer.tactics');
  const hasPhaseFilter = useFeature('trainer.filter.phase');
  const hasDifficultyFilter = useFeature('trainer.filter.difficulty');
  const hasTacticalFilter = useFeature('trainer.filter.tactical');
  const hasThreats = useFeature('trainer.threats');
  const activeCount = filters.activeFilterCount();

  return (
    <>
      {/* Puzzle Filters */}
      <div class="panel-section filters-panel" style="padding: 0;">
        <div class="section-title filters-header" id="filtersHeader" onClick={filters.toggleFiltersCollapsed}>
          <div class="filters-header-left">
            <span>{t('trainer.filters.title')}</span>
            {activeCount > 0 && <span class="filters-count-badge" id="filtersCountBadge">{activeCount} active</span>}
          </div>
          <button class="filters-toggle-btn" id="filtersToggleBtn" title="Toggle filters">
            <ChevronSvg collapsed={state.filtersCollapsed} />
          </button>
        </div>
        {!state.filtersCollapsed && (
          <div class="filters-content">
            <div class="filter-group">
              <div class="filter-label">{t('trainer.filters.game_type')}</div>
              <div class="game-type-filter">
                <CheckboxGroup
                  items={GAME_TYPES}
                  selected={state.gameTypes}
                  onChange={filters.setGameTypes}
                  labelPrefix="trainer.game_type"
                />
              </div>
            </div>

            {hasPhaseFilter && (
              <div class="filter-group">
                <div class="filter-label">{t('trainer.filters.phase')}</div>
                <div class="phase-filter">
                  <CheckboxGroup
                    items={GAME_PHASES}
                    selected={state.phases}
                    onChange={filters.setPhases}
                    labelPrefix="chess.phase"
                  />
                </div>
              </div>
            )}

            {hasDifficultyFilter && (
              <div class="filter-group">
                <div class="filter-label">{t('trainer.filters.difficulty')}</div>
                <div class="difficulty-filter">
                  <CheckboxGroup
                    items={DIFFICULTIES}
                    selected={state.difficulties}
                    onChange={filters.setDifficulties}
                    labelPrefix="dashboard.difficulty"
                  />
                </div>
              </div>
            )}

            {hasTacticalFilter && (
              <div class="filter-group">
                <div class="filter-label">{t('trainer.filters.tactical')}</div>
                <div class="tactical-filter">
                  {TACTICAL_PATTERNS.map(({ value, key }) => (
                    <button
                      key={value}
                      class={`tactical-filter-btn ${state.tacticalPattern === value ? 'active' : ''}`}
                      onClick={() => { filters.setTacticalPattern(
                        state.tacticalPattern === value ? null : value,
                      ); }}
                    >
                      {t(key)}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <div class="filter-group">
              <div class="filter-label">{t('trainer.filters.color')}</div>
              <div class="color-filter">
                {(['both', 'white', 'black'] as const).map(c => (
                  <label key={c} class="filter-radio-label">
                    <input
                      type="radio"
                      name="colorFilter"
                      checked={state.color === c}
                      onChange={() => { filters.setColor(c); }}
                    />
                    <span class={`color-option ${c}`}>
                      {c === 'white' ? '\u2654 ' : c === 'black' ? '\u265a ' : ''}
                      {t(`chess.color.${c}`)}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Board Settings */}
      <div class="panel-section filters-panel" style="padding: 0;">
        <div class="section-title filters-header" id="boardSettingsHeader" onClick={filters.toggleBoardSettingsCollapsed}>
          <div class="filters-header-left">
            <span>{t('trainer.board_settings.title')}</span>
          </div>
          <button class="filters-toggle-btn" id="boardSettingsToggleBtn" title="Toggle board settings">
            <ChevronSvg collapsed={state.boardSettingsCollapsed} />
          </button>
        </div>
        {!state.boardSettingsCollapsed && (
          <div class="filters-content">
            <div class="filter-group">
              <div class="board-toggles-vertical">
                <div class="arrow-toggle">
                  <input type="checkbox" id="showArrows" checked={state.showArrows} onChange={(e) => { filters.setShowArrows(e.currentTarget.checked); }} />
                  <label for="showArrows">{t('trainer.toggle.show_arrows')}</label>
                </div>
                {hasThreats && (
                  <div class="arrow-toggle">
                    <input type="checkbox" id="showThreats" checked={state.showThreats} onChange={(e) => { filters.setShowThreats(e.currentTarget.checked); }} />
                    <label for="showThreats">{t('trainer.toggle.show_threats')}</label>
                  </div>
                )}
                {hasTactics && (
                  <div class="arrow-toggle">
                    <input type="checkbox" id="showTactics" checked={state.showTactics} onChange={(e) => { filters.setShowTactics(e.currentTarget.checked); }} />
                    <label for="showTactics">{t('trainer.toggle.show_tactics')}</label>
                  </div>
                )}
                <div class="arrow-toggle">
                  <input type="checkbox" id="playFullLine" checked={state.playFullLine} onChange={(e) => { filters.setPlayFullLine(e.currentTarget.checked); }} />
                  <label for="playFullLine">{t('trainer.toggle.play_full_line')}</label>
                </div>
                <div class="arrow-toggle">
                  <input type="checkbox" id="showCoordinates" checked={state.showCoordinates} onChange={(e) => { filters.setShowCoordinates(e.currentTarget.checked); }} />
                  <label for="showCoordinates">{t('trainer.toggle.show_coordinates')}</label>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
