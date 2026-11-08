import type { FiltersAPI } from '../hooks/useFilters';
import { useFeature } from '../../hooks/useFeature';
import { GAME_TYPES, GAME_PHASES, DIFFICULTIES, TACTICAL_PATTERNS } from '../../shared/constants';
import { Button } from '../../components/primitives/Button';

interface FiltersPanelProps {
  filters: FiltersAPI;
}

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
        <label key={item} class="filter-checkbox-label" data-value={item}>
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

export function FilterSummary({ filters, onChange }: { filters: FiltersAPI; onChange: () => void }): preact.JSX.Element {
  const { state } = filters;
  const narrowed = (selected: string[], all: readonly string[], prefix: string): string | null =>
    selected.length > 0 && selected.length < all.length ? selected.map(v => t(`${prefix}.${v}`)).join(', ') : null;
  const tactical = TACTICAL_PATTERNS.find(p => p.value === state.tacticalPattern);
  const parts = [
    narrowed(state.gameTypes, GAME_TYPES, 'trainer.game_type'),
    narrowed(state.phases, GAME_PHASES, 'chess.phase'),
    narrowed(state.difficulties, DIFFICULTIES, 'dashboard.difficulty'),
    tactical ? t(tactical.key) : null,
    state.color !== 'both' ? t(`chess.color.${state.color}`) : null,
  ].filter(Boolean);

  return (
    <div class="filter-summary">
      <div class="filter-summary-text">
        <span class="filter-summary-label">{t('trainer.filters.title')}</span>
        <span class="filter-summary-value" data-testid="filter-summary">
          {parts.length > 0 ? parts.join(' · ') : t('trainer.filters.all_puzzles')}
        </span>
      </div>
      <Button variant="secondary" size="sm" testId="change-filters" onClick={onChange}>
        {t('trainer.filters.change')}
      </Button>
    </div>
  );
}

export function FiltersPanel({ filters }: FiltersPanelProps): preact.JSX.Element {
  const { state } = filters;
  const hasPhaseFilter = useFeature('trainer.filter.phase');
  const hasDifficultyFilter = useFeature('trainer.filter.difficulty');
  const hasTacticalFilter = useFeature('trainer.filter.tactical');

  return (
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
            <label key={c} class="filter-radio-label" data-value={c}>
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
  );
}
