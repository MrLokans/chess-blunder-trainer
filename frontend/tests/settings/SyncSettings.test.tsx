import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { SyncSettings } from '../../src/settings/SyncSettings';
import type { SyncSettings as SyncSettingsData } from '../../src/settings/types';

const DEFAULTS: SyncSettingsData = {
  auto_sync: false,
  sync_interval: 24,
  max_games: 1000,
  auto_analyze: true,
  spaced_repetition_days: 30,
};

describe('SyncSettings', () => {
  test('renders form fields with loaded values', () => {
    render(<SyncSettings settings={DEFAULTS} syncVisible={true} analyzeVisible={true} onChange={() => {}} />);
    expect((screen.getByLabelText('settings.auto_sync.enable') as HTMLInputElement).checked).toBe(false);
    expect((screen.getByLabelText('settings.max_games.label') as HTMLInputElement).value).toBe('1000');
    expect((screen.getByLabelText('settings.spaced_repetition.label') as HTMLInputElement).value).toBe('30');
  });

  test('hides sync section when syncVisible is false', () => {
    const { container } = render(
      <SyncSettings settings={DEFAULTS} syncVisible={false} analyzeVisible={true} onChange={() => {}} />
    );
    const syncSection = container.querySelector('[data-section="sync"]');
    expect(syncSection?.classList.contains('hidden')).toBe(true);
  });

  test('calls onChange when a field changes', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<SyncSettings settings={DEFAULTS} syncVisible={true} analyzeVisible={true} onChange={onChange} />);

    await user.click(screen.getByLabelText('settings.auto_sync.enable'));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ auto_sync: true }));
  });

  test('always shows spaced repetition (not tied to feature flag)', () => {
    render(<SyncSettings settings={DEFAULTS} syncVisible={false} analyzeVisible={false} onChange={() => {}} />);
    expect(screen.getByLabelText('settings.spaced_repetition.label')).toBeDefined();
  });
});
