import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { DashboardFilters } from '../../src/dashboard/DashboardFilters';

const defaultProps = {
  datePreset: 'all' as const,
  dateFrom: null as string | null,
  dateTo: null as string | null,
  gameTypes: ['bullet', 'blitz', 'rapid', 'classical'],
  gamePhases: ['opening', 'middlegame', 'endgame'],
  onDatePreset: vi.fn(),
  onCustomDateRange: vi.fn(),
  onClearDate: vi.fn(),
  onGameTypesChange: vi.fn(),
  onGamePhasesChange: vi.fn(),
};

describe('DashboardFilters', () => {
  test('renders preset buttons', () => {
    render(<DashboardFilters {...defaultProps} />);
    expect(screen.getByText(t('dashboard.filter.last_7d'))).toBeDefined();
    expect(screen.getByText(t('dashboard.filter.all_time'))).toBeDefined();
  });

  test('marks active preset', () => {
    const { container } = render(<DashboardFilters {...defaultProps} datePreset="30d" />);
    const activeBtn = container.querySelector('.filter-presets button.active');
    expect(activeBtn?.getAttribute('data-preset')).toBe('30d');
  });

  test('calls onDatePreset when preset button clicked', async () => {
    const onDatePreset = vi.fn();
    const user = userEvent.setup();
    render(<DashboardFilters {...defaultProps} onDatePreset={onDatePreset} />);

    await user.click(screen.getByText(t('dashboard.filter.last_7d')));
    expect(onDatePreset).toHaveBeenCalledWith('7d');
  });

  test('renders game type checkboxes all checked', () => {
    render(<DashboardFilters {...defaultProps} />);
    const bullet = screen.getByLabelText(t('trainer.game_type.bullet')) as HTMLInputElement;
    expect(bullet.checked).toBe(true);
  });

  test('calls onGameTypesChange when checkbox toggled', async () => {
    const onGameTypesChange = vi.fn();
    const user = userEvent.setup();
    render(<DashboardFilters {...defaultProps} onGameTypesChange={onGameTypesChange} />);

    await user.click(screen.getByLabelText(t('trainer.game_type.bullet')));
    expect(onGameTypesChange).toHaveBeenCalledWith(['blitz', 'rapid', 'classical']);
  });
});
