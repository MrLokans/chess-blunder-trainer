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

  test('shows the default context while collapsed', () => {
    render(<DashboardFilters {...defaultProps} />);
    expect(screen.getByText(`${t('dashboard.filter.all_time')} · ${t('dashboard.filter.all_time_controls')} · ${t('dashboard.filter.all_phases')}`)).toBeDefined();
  });

  test('marks active preset', () => {
    const { container } = render(<DashboardFilters {...defaultProps} datePreset="30d" />);
    const activeBtn = container.querySelector('.filter-presets button.active');
    expect(activeBtn?.getAttribute('data-preset')).toBe('30d');
  });

  test('toggles its accessible disclosure', async () => {
    const user = userEvent.setup();
    render(<DashboardFilters {...defaultProps} />);

    const toggle = screen.getByRole('button', { name: new RegExp(t('dashboard.filter.title')) });
    expect(toggle.getAttribute('aria-expanded')).toBe('false');
    expect(toggle.getAttribute('aria-controls')).toBe('dashboard-filter-body');
    await user.tab();
    await user.keyboard('{Enter}');
    expect(toggle.getAttribute('aria-expanded')).toBe('true');
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
    const bullet = screen.getByLabelText(t('trainer.game_type.bullet'));
    expect(bullet.checked).toBe(true);
  });

  test('calls onGameTypesChange when checkbox toggled', async () => {
    const onGameTypesChange = vi.fn();
    const user = userEvent.setup();
    render(<DashboardFilters {...defaultProps} onGameTypesChange={onGameTypesChange} />);

    await user.click(screen.getByLabelText(t('trainer.game_type.bullet')));
    expect(onGameTypesChange).toHaveBeenCalledWith(['blitz', 'rapid', 'classical']);
  });

  test('shows and clears non-default filters', async () => {
    const onClearDate = vi.fn();
    const onGameTypesChange = vi.fn();
    const onGamePhasesChange = vi.fn();
    const user = userEvent.setup();
    render(<DashboardFilters {...defaultProps} datePreset={null} dateFrom="2025-01-01" dateTo="2025-01-31" gameTypes={['blitz']} gamePhases={['endgame']} onClearDate={onClearDate} onGameTypesChange={onGameTypesChange} onGamePhasesChange={onGamePhasesChange} />);

    expect(screen.getByText(`2025-01-01 – 2025-01-31 · ${t('trainer.game_type.blitz')} · ${t('chess.phase.endgame')}`)).toBeDefined();
    await user.click(screen.getByRole('button', { name: t('dashboard.filter.clear_all') }));
    expect(onClearDate).toHaveBeenCalledOnce();
    expect(onGameTypesChange).toHaveBeenCalledWith(['bullet', 'blitz', 'rapid', 'classical']);
    expect(onGamePhasesChange).toHaveBeenCalledWith(['opening', 'middlegame', 'endgame']);
  });
});
