import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { BillingSection } from '../../src/settings/BillingSection';
import { ApiError, client, type BillingStatusResponse } from '../../src/shared/api';

vi.mock('../../src/shared/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../src/shared/api')>();
  return {
    ...actual,
    client: {
      billing: {
        status: vi.fn(),
        checkout: vi.fn(),
        portal: vi.fn(),
      },
    },
  };
});

function trialingStatus(): BillingStatusResponse {
  return {
    status: 'trialing',
    plan: null,
    trial_ends_at: '2026-08-01T00:00:00+00:00',
    current_period_end: null,
    read_only: false,
    grants: ['cloud.autosync'],
  };
}

describe('BillingSection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders nothing when cloud mode is off (404)', async () => {
    vi.mocked(client.billing.status).mockRejectedValue(
      new ApiError(404, 'cloud_mode_disabled'),
    );
    const { container } = render(<BillingSection />);
    await waitFor(() => {
      expect(client.billing.status).toHaveBeenCalled();
    });
    expect(container.innerHTML).toBe('');
  });

  test('shows subscribe buttons while trialing', async () => {
    vi.mocked(client.billing.status).mockResolvedValue(trialingStatus());
    render(<BillingSection />);
    await waitFor(() => {
      expect(
        screen.getByText('billing.settings.subscribe_monthly'),
      ).toBeDefined();
      expect(screen.getByText('billing.settings.subscribe_annual')).toBeDefined();
    });
  });

  test('shows manage button when active', async () => {
    vi.mocked(client.billing.status).mockResolvedValue({
      ...trialingStatus(),
      status: 'active',
      plan: 'monthly',
      trial_ends_at: null,
      current_period_end: '2026-09-01T00:00:00+00:00',
    });
    render(<BillingSection />);
    await waitFor(() => {
      expect(screen.getByText('billing.settings.manage')).toBeDefined();
      expect(
        screen.queryByText('billing.settings.subscribe_monthly'),
      ).toBeNull();
    });
  });
});
