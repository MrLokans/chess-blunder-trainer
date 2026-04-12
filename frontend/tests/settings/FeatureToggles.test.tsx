import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { FeatureToggles } from '../../src/settings/FeatureToggles';
import type { FeatureGroup } from '../../src/settings/types';

const GROUPS: FeatureGroup[] = [
  {
    label: 'group.automation',
    features: [
      { id: 'auto.sync', label: 'features.auto_sync', enabled: true },
      { id: 'auto.analyze', label: 'features.auto_analyze', enabled: false },
    ],
  },
  {
    label: 'group.developer',
    features: [
      { id: 'debug.copy', label: 'features.debug_copy', enabled: true },
    ],
  },
];

const mockSaveFeatures = vi.fn().mockResolvedValue({});

describe('FeatureToggles', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockSaveFeatures.mockResolvedValue({});
    window.__features = { 'auto.sync': true, 'auto.analyze': false, 'debug.copy': true };
  });

  test('renders all groups and features', () => {
    render(<FeatureToggles groups={GROUPS} onSave={mockSaveFeatures} />);
    expect(screen.getByText('group.automation')).toBeDefined();
    expect(screen.getByText('group.developer')).toBeDefined();
    expect(screen.getByLabelText('features.auto_sync')).toBeDefined();
    expect(screen.getByLabelText('features.auto_analyze')).toBeDefined();
    expect(screen.getByLabelText('features.debug_copy')).toBeDefined();
  });

  test('checkboxes reflect initial enabled state', () => {
    render(<FeatureToggles groups={GROUPS} onSave={mockSaveFeatures} />);
    expect((screen.getByLabelText('features.auto_sync')).checked).toBe(true);
    expect((screen.getByLabelText('features.auto_analyze')).checked).toBe(false);
  });

  test('calls onSave with feature id and new value on toggle', async () => {
    const user = userEvent.setup();
    render(<FeatureToggles groups={GROUPS} onSave={mockSaveFeatures} />);

    await user.click(screen.getByLabelText('features.auto_analyze'));
    expect(mockSaveFeatures).toHaveBeenCalledWith({ 'auto.analyze': true });
  });

  test('reverts checkbox if save fails', async () => {
    mockSaveFeatures.mockRejectedValue(new Error('Network error'));
    const user = userEvent.setup();
    render(<FeatureToggles groups={GROUPS} onSave={mockSaveFeatures} />);

    const checkbox = screen.getByLabelText('features.auto_analyze');
    expect(checkbox.checked).toBe(false);

    await user.click(checkbox);
    await waitFor(() => {
      expect(checkbox.checked).toBe(false);
    });
  });

  test('calls onFeatureChanged when a toggle succeeds', async () => {
    const onChanged = vi.fn();
    const user = userEvent.setup();
    render(<FeatureToggles groups={GROUPS} onSave={mockSaveFeatures} onFeatureChanged={onChanged} />);

    await user.click(screen.getByLabelText('features.auto_analyze'));
    await waitFor(() => {
      expect(onChanged).toHaveBeenCalledWith('auto.analyze', true);
    });
  });
});
