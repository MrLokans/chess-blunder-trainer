import { Button } from '../components/primitives/Button';
import { Toggle } from '../components/primitives/Toggle';
import { Segmented } from '../components/primitives/Segmented';
import { RangeSlider } from '../components/primitives/RangeSlider';

interface EngineControlsProps {
  analysisMode: boolean;
  multipv: number;
  maxDepth: number;
  depth: number;
  showArrows: boolean;
  showThreats: boolean;
  exploring: boolean;
  onToggleAnalysis: () => void;
  onMultiPv: (n: number) => void;
  onMaxDepth: (n: number) => void;
  onToggleArrows: () => void;
  onToggleThreats: () => void;
  onBackToGame: () => void;
}

const MIN_DEPTH = 5;
const MAX_DEPTH = 30;
const LINE_OPTIONS = [1, 2, 3, 4, 5].map(n => ({ label: String(n), value: n }));

export function EngineControls(props: EngineControlsProps) {
  const progressPct = Math.min(100, Math.round((props.depth / props.maxDepth) * 100));

  return (
    <div class="engine-controls" id="engineControls">
      <div class="engine-controls__header">
        <span class="engine-controls__title">{t('game_review.engine.enable')}</span>
        <Toggle
          value={props.analysisMode}
          onChange={props.onToggleAnalysis}
          ariaLabel={t('game_review.engine.enable')}
          id="engineAnalysisToggle"
        />
      </div>

      {props.analysisMode && (
        <>
          <div class="engine-controls__group">
            <div class="engine-controls__group-label">{t('game_review.engine.analysis_group')}</div>

            <div class="engine-controls__row">
              <span class="engine-controls__label">{t('game_review.engine.multipv')}</span>
              <Segmented
                options={LINE_OPTIONS}
                value={props.multipv}
                onChange={props.onMultiPv}
                ariaLabel={t('game_review.engine.multipv')}
              />
            </div>

            <div class="engine-controls__row">
              <span class="engine-controls__label">{t('game_review.engine.max_depth')}</span>
              <RangeSlider
                min={MIN_DEPTH}
                max={MAX_DEPTH}
                value={props.maxDepth}
                onChange={props.onMaxDepth}
                ariaLabel={t('game_review.engine.max_depth')}
                id="engineMaxDepth"
              />
              <span class="engine-controls__value">{props.maxDepth}</span>
            </div>

            <div class="engine-depth-progress" aria-hidden="true">
              <span class="engine-depth-progress__label">
                {t('game_review.engine.depth_progress', { current: props.depth, max: props.maxDepth })}
              </span>
              <div class="engine-depth-progress__track">
                <div class="engine-depth-progress__fill" style={`width: ${String(progressPct)}%`} />
              </div>
            </div>
          </div>

          <div class="engine-controls__group">
            <div class="engine-controls__group-label">{t('game_review.engine.display_group')}</div>
            <div class="engine-controls__row engine-controls__row--display">
              <Toggle value={props.showArrows} onChange={props.onToggleArrows} label={t('game_review.engine.show_arrows')} />
              <Toggle value={props.showThreats} onChange={props.onToggleThreats} label={t('game_review.engine.show_threats')} />
            </div>
          </div>

          {props.exploring && (
            <div class="engine-back">
              <Button variant="secondary" onClick={props.onBackToGame}>
                {t('game_review.engine.back_to_game')}
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
