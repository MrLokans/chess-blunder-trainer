interface EngineControlsProps {
  analysisMode: boolean;
  multipv: number;
  showArrows: boolean;
  showThreats: boolean;
  exploring: boolean;
  onToggleAnalysis: () => void;
  onMultiPv: (n: number) => void;
  onToggleArrows: () => void;
  onToggleThreats: () => void;
  onBackToGame: () => void;
}

export function EngineControls(props: EngineControlsProps) {
  return (
    <div class="engine-controls" id="engineControls">
      <label class="engine-toggle">
        <input type="checkbox" checked={props.analysisMode} onChange={props.onToggleAnalysis} />
        {t('game_review.engine.enable')}
      </label>

      {props.analysisMode && (
        <>
          <label class="engine-multipv">
            {t('game_review.engine.multipv')}
            <select
              value={String(props.multipv)}
              onChange={(e) => { props.onMultiPv(Number(e.currentTarget.value)); }}
            >
              {[1, 2, 3, 4, 5].map(n => <option key={n} value={String(n)}>{n}</option>)}
            </select>
          </label>

          <label class="engine-toggle">
            <input type="checkbox" checked={props.showArrows} onChange={props.onToggleArrows} />
            {t('game_review.engine.show_arrows')}
          </label>

          <label class="engine-toggle">
            <input type="checkbox" checked={props.showThreats} onChange={props.onToggleThreats} />
            {t('game_review.engine.show_threats')}
          </label>

          {props.exploring && (
            <button type="button" class="btn btn-secondary engine-back" onClick={props.onBackToGame}>
              {t('game_review.engine.back_to_game')}
            </button>
          )}
        </>
      )}
    </div>
  );
}
