import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { UpdateGamesPanel } from '../../src/components/UpdateGamesPanel';
import type { Profile } from '../../src/types/profiles';

vi.mock('../../src/shared/api', () => ({
  client: {
    profiles: {
      sync: vi.fn(),
    },
  },
}));

import { client } from '../../src/shared/api';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    platform: 'lichess',
    username: 'alice',
    is_primary: true,
    created_at: '2026-04-01T00:00:00Z',
    last_validated_at: null,
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [],
    last_game_sync_at: null,
    last_stats_sync_at: null,
    ...overrides,
  };
}

describe('UpdateGamesPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders empty state when no profiles', () => {
    render(<UpdateGamesPanel profiles={[]} />);
    expect(screen.getByText(t('management.update.empty_title'))).toBeDefined();
  });

  test('lists every profile with platform label', () => {
    const profiles = [
      makeProfile({ id: 1, platform: 'lichess', username: 'alice' }),
      makeProfile({ id: 2, platform: 'chesscom', username: 'bob' }),
    ];
    render(<UpdateGamesPanel profiles={profiles} />);
    expect(screen.getByText(/Lichess — alice/)).toBeDefined();
    expect(screen.getByText(/Chess\.com — bob/)).toBeDefined();
  });

  test('fans out one sync call per profile when clicked', async () => {
    vi.mocked(client.profiles.sync).mockResolvedValue({ job_id: 'j' });
    const profiles = [
      makeProfile({ id: 1 }),
      makeProfile({ id: 2 }),
      makeProfile({ id: 3 }),
    ];
    render(<UpdateGamesPanel profiles={profiles} />);
    fireEvent.click(screen.getByRole('button', { name: t('management.update.button') }));
    await waitFor(() => {
      expect(client.profiles.sync).toHaveBeenCalledTimes(3);
    });
    expect(client.profiles.sync).toHaveBeenCalledWith(1);
    expect(client.profiles.sync).toHaveBeenCalledWith(2);
    expect(client.profiles.sync).toHaveBeenCalledWith(3);
  });

  test('shows success message after a clean fan-out', async () => {
    vi.mocked(client.profiles.sync).mockResolvedValue({ job_id: 'j' });
    render(<UpdateGamesPanel profiles={[makeProfile(), makeProfile({ id: 2 })]} />);
    fireEvent.click(screen.getByRole('button', { name: t('management.update.button') }));
    await waitFor(() => {
      expect(screen.getByText(t('management.update.started', { count: 2 }))).toBeDefined();
    });
  });

  test('shows partial-failure message when one dispatch fails', async () => {
    // First call succeeds, second rejects — single profile per call so we
    // can assert the mixed-outcome branch independently of order.
    vi.mocked(client.profiles.sync)
      .mockResolvedValueOnce({ job_id: 'j1' })
      .mockRejectedValueOnce(new Error('upstream 503'));
    render(<UpdateGamesPanel profiles={[makeProfile({ id: 1 }), makeProfile({ id: 2 })]} />);
    fireEvent.click(screen.getByRole('button', { name: t('management.update.button') }));
    await waitFor(() => {
      expect(
        screen.getByText(
          t('management.update.partial_failure', { successes: 1, failures: 1 }),
        ),
      ).toBeDefined();
    });
  });

  test('shows all-failed message when every dispatch fails', async () => {
    vi.mocked(client.profiles.sync).mockRejectedValue(new Error('boom'));
    render(<UpdateGamesPanel profiles={[makeProfile({ id: 1 }), makeProfile({ id: 2 })]} />);
    fireEvent.click(screen.getByRole('button', { name: t('management.update.button') }));
    await waitFor(() => {
      expect(screen.getByText(t('management.update.all_failed', { count: 2 }))).toBeDefined();
    });
  });

  test('disables the button in demo mode', () => {
    render(<UpdateGamesPanel profiles={[makeProfile()]} demoMode />);
    const button = screen.getByRole('button', { name: t('management.update.button') });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});
