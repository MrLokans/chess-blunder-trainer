import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { Tabs, type TabDescriptor } from '../../src/components/Tabs';

type TabKey = 'overview' | 'preferences' | 'history';

const TABS: TabDescriptor<TabKey>[] = [
  { key: 'overview', label: 'Overview' },
  { key: 'preferences', label: 'Preferences' },
  { key: 'history', label: 'History', badge: 3 },
];

describe('Tabs', () => {
  test('renders one button per tab + active panel content', () => {
    render(
      <Tabs tabs={TABS} value="overview" onChange={() => {}}>
        <div data-testid="panel">overview body</div>
      </Tabs>,
    );
    expect(screen.getAllByRole('tab')).toHaveLength(3);
    expect(screen.getByTestId('panel').textContent).toBe('overview body');
  });

  test('marks the active tab with aria-selected', () => {
    render(<Tabs tabs={TABS} value="preferences" onChange={() => {}} />);
    const prefsTab = screen.getByRole('tab', { name: /Preferences/ });
    expect(prefsTab.getAttribute('aria-selected')).toBe('true');
    expect(prefsTab.className).toContain('tabs__tab--active');
  });

  test('clicking a tab fires onChange with its key', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} value="overview" onChange={onChange} />);
    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    expect(onChange).toHaveBeenCalledWith('preferences');
  });

  test('badge is rendered when provided', () => {
    render(<Tabs tabs={TABS} value="overview" onChange={() => {}} />);
    const historyTab = screen.getByRole('tab', { name: /History/ });
    expect(historyTab.querySelector('.tabs__badge')?.textContent).toBe('3');
  });

  test('ArrowRight moves to next tab', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} value="overview" onChange={onChange} />);
    screen.getByRole('tab', { name: /Overview/ }).focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('preferences');
  });

  test('ArrowLeft wraps to last tab', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} value="overview" onChange={onChange} />);
    screen.getByRole('tab', { name: /Overview/ }).focus();
    await user.keyboard('{ArrowLeft}');
    expect(onChange).toHaveBeenCalledWith('history');
  });

  test('Home jumps to first, End jumps to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Tabs tabs={TABS} value="preferences" onChange={onChange} />);
    screen.getByRole('tab', { name: /Preferences/ }).focus();
    await user.keyboard('{End}');
    expect(onChange).toHaveBeenLastCalledWith('history');
    await user.keyboard('{Home}');
    expect(onChange).toHaveBeenLastCalledWith('overview');
  });

  test('inactive tabs have tabIndex=-1 (roving tabindex)', () => {
    render(<Tabs tabs={TABS} value="overview" onChange={() => {}} />);
    expect(screen.getByRole('tab', { name: /Overview/ }).getAttribute('tabindex')).toBe('0');
    expect(screen.getByRole('tab', { name: /Preferences/ }).getAttribute('tabindex')).toBe('-1');
  });

  test('aria-controls and aria-labelledby link tab to its panel', () => {
    render(<Tabs tabs={TABS} value="preferences" onChange={() => {}}>body</Tabs>);
    const prefsTab = screen.getByRole('tab', { name: /Preferences/ });
    const panel = screen.getByRole('tabpanel');
    const controls = prefsTab.getAttribute('aria-controls');
    const labelledBy = panel.getAttribute('aria-labelledby');
    expect(controls).toBe(panel.id);
    expect(labelledBy).toBe(prefsTab.id);
  });

  test('panel remounts on tab change so stale state does not leak', () => {
    const { rerender } = render(
      <Tabs tabs={TABS} value="overview" onChange={() => {}}>
        <span data-testid="panel-content">A</span>
      </Tabs>,
    );
    const before = screen.getByTestId('panel-content');
    rerender(
      <Tabs tabs={TABS} value="preferences" onChange={() => {}}>
        <span data-testid="panel-content">B</span>
      </Tabs>,
    );
    const after = screen.getByTestId('panel-content');
    expect(after.textContent).toBe('B');
    expect(after).not.toBe(before);
  });

  test('disabled tab is not clickable and is skipped by arrow keys', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const tabsWithDisabled: TabDescriptor<TabKey>[] = [
      { key: 'overview', label: 'Overview' },
      { key: 'preferences', label: 'Preferences', disabled: true },
      { key: 'history', label: 'History' },
    ];
    render(<Tabs tabs={tabsWithDisabled} value="overview" onChange={onChange} />);
    await user.click(screen.getByRole('tab', { name: /Preferences/ }));
    expect(onChange).not.toHaveBeenCalled();

    screen.getByRole('tab', { name: /Overview/ }).focus();
    await user.keyboard('{ArrowRight}');
    expect(onChange).toHaveBeenCalledWith('history');
  });
});
