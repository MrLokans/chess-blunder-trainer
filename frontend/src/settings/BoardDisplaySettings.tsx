import { useState } from 'preact/hooks';
import { useFeature } from '../hooks/useFeature';
import {
  BOARD_DISPLAY_OPTIONS, loadBoardDisplay, saveBoardDisplay, type BoardDisplayOption,
} from '../shared/board-display';

const OPTIONS = Object.keys(BOARD_DISPLAY_OPTIONS) as BoardDisplayOption[];

function BoardDisplayToggle({ option }: { option: BoardDisplayOption }): preact.JSX.Element | null {
  const spec: { label: string; feature?: string } = BOARD_DISPLAY_OPTIONS[option];
  const featureOn = useFeature(spec.feature ?? '');
  const [checked, setChecked] = useState(() => loadBoardDisplay(option));
  if (spec.feature && !featureOn) return null;

  return (
    <label class="checkbox-label">
      <input
        type="checkbox"
        id={`boardDisplay-${option}`}
        checked={checked}
        onChange={(e) => {
          setChecked(e.currentTarget.checked);
          saveBoardDisplay(option, e.currentTarget.checked);
        }}
      />
      {t(spec.label)}
    </label>
  );
}

export function BoardDisplaySettings(): preact.JSX.Element {
  return (
    <fieldset class="form-group mt-8">
      <legend>{t('trainer.board_settings.title')}</legend>
      {OPTIONS.map(option => <BoardDisplayToggle key={option} option={option} />)}
      <div class="help-text">{t('settings.board_display.description')}</div>
    </fieldset>
  );
}
