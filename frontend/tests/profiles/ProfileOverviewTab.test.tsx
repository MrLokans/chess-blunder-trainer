import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ProfileOverviewTab } from '../../src/profiles/ProfileOverviewTab';
import type { Profile } from '../../src/types/profiles';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 7,
    platform: 'lichess',
    username: 'magnuscarlsen',
    is_primary: true,
    created_at: '2026-04-01T12:00:00Z',
    last_validated_at: '2026-05-01T11:55:00Z',
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [
      { mode: 'bullet', rating: 3200, games_count: 5000, synced_at: '2026-05-01T11:50:00Z' },
      { mode: 'blitz', rating: 3000, games_count: 12000, synced_at: '2026-05-01T11:50:00Z' },
      { mode: 'rapid', rating: null, games_count: 0, synced_at: null },
    ],
    last_game_sync_at: '2026-05-01T11:00:00Z',
    last_stats_sync_at: '2026-05-01T11:50:00Z',
    ...overrides,
  };
}

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, 'fetch');
});

afterEach(() => {
  cleanup();
  fetchSpy.mockRestore();
});

describe('ProfileOverviewTab', () => {
  test('renders username, platform badge, and a rating card per stat entry', () => {
    render(<ProfileOverviewTab profile={makeProfile()} onProfileChange={() => {}} />);
    expect(screen.getByRole('heading', { name: 'magnuscarlsen' })).toBeDefined();
    expect(screen.getByText('Lichess')).toBeDefined();
    expect(screen.getByText('profiles.stats.mode.bullet')).toBeDefined();
    expect(screen.getByText('profiles.stats.mode.blitz')).toBeDefined();
    expect(screen.getByText('profiles.stats.mode.rapid')).toBeDefined();
    expect(screen.getByText('3200')).toBeDefined();
    expect(screen.getByText('3000')).toBeDefined();
  });

  test('shows primary badge when profile is primary', () => {
    render(<ProfileOverviewTab profile={makeProfile({ is_primary: true })} onProfileChange={() => {}} />);
    expect(screen.getByText('profiles.overview.primary_badge')).toBeDefined();
    expect(screen.queryByRole('button', { name: 'profiles.overview.make_primary' })).toBeNull();
  });

  test('shows Make Primary button when not primary; click PATCHes is_primary=true', async () => {
    const onProfileChange = vi.fn();
    const updated = makeProfile({ is_primary: true });
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify(updated), { status: 200 }),
    );
    const user = userEvent.setup();
    render(
      <ProfileOverviewTab
        profile={makeProfile({ is_primary: false })}
        onProfileChange={onProfileChange}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.overview.make_primary' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/7',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ is_primary: true }),
        }),
      );
    });
    await waitFor(() => {
      expect(onProfileChange).toHaveBeenCalledWith(updated);
    });
  });

  test('Sync Now button POSTs to /api/profiles/{id}/sync and shows success', async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ job_id: 'job-123' }), { status: 200 }),
    );
    const user = userEvent.setup();
    render(<ProfileOverviewTab profile={makeProfile()} onProfileChange={() => {}} />);
    await user.click(screen.getByRole('button', { name: 'profiles.overview.sync_now' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/7/sync',
        expect.objectContaining({ method: 'POST' }),
      );
    });
    await waitFor(() => {
      expect(screen.getByText('profiles.overview.sync_started')).toBeDefined();
    });
  });

  test('Refresh stats POSTs and updates stats inline via onProfileChange', async () => {
    const onProfileChange = vi.fn();
    const newStats = [
      { mode: 'bullet', rating: 3250, games_count: 5100, synced_at: '2026-05-01T13:00:00Z' },
    ];
    fetchSpy.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ stats: newStats, last_validated_at: '2026-05-01T13:00:00Z' }),
        { status: 200 },
      ),
    );
    const user = userEvent.setup();
    render(<ProfileOverviewTab profile={makeProfile()} onProfileChange={onProfileChange} />);
    await user.click(screen.getByRole('button', { name: 'profiles.overview.refresh_stats' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/7/stats/refresh',
        expect.objectContaining({ method: 'POST' }),
      );
    });
    await waitFor(() => {
      expect(onProfileChange).toHaveBeenCalled();
    });
    const updatedArg = onProfileChange.mock.calls[0]?.[0] as Profile;
    expect(updatedArg.stats).toEqual(newStats);
    expect(updatedArg.last_validated_at).toBe('2026-05-01T13:00:00Z');
  });

  test('demo mode disables Sync now, Refresh stats, and Make Primary', () => {
    render(
      <ProfileOverviewTab
        profile={makeProfile({ is_primary: false })}
        onProfileChange={() => {}}
        demoMode
      />,
    );
    expect(screen.getByRole('button', { name: 'profiles.overview.sync_now' })
      .hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: 'profiles.overview.refresh_stats' })
      .hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: 'profiles.overview.make_primary' })
      .hasAttribute('disabled')).toBe(true);
  });

  test('shows empty stats hint when stats array is empty', () => {
    render(<ProfileOverviewTab profile={makeProfile({ stats: [] })} onProfileChange={() => {}} />);
    expect(screen.getByText('profiles.overview.no_stats_yet')).toBeDefined();
  });

  test('rating card with null rating renders the placeholder', () => {
    render(<ProfileOverviewTab profile={makeProfile()} onProfileChange={() => {}} />);
    expect(screen.getByText('profiles.overview.no_rating')).toBeDefined();
  });
});
