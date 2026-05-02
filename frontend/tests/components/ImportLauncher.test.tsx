import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { ImportLauncher } from '../../src/components/ImportLauncher';
import type { Profile } from '../../src/types/profiles';

vi.mock('../../src/shared/api', async () => {
  const actual = await vi.importActual<typeof import('../../src/shared/api')>('../../src/shared/api');
  return {
    ...actual,
    client: {
      profiles: { sync: vi.fn() },
    },
  };
});

import { client } from '../../src/shared/api';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    platform: 'lichess',
    username: 'magnus',
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

describe('ImportLauncher', () => {
  beforeEach(() => {
    vi.mocked(client.profiles.sync).mockReset();
    vi.mocked(client.profiles.sync).mockResolvedValue({ job_id: 'job-1' });
  });

  test('renders preferences with global-default fallback for max_games', () => {
    const profile = makeProfile({ preferences: { auto_sync_enabled: true, sync_max_games: null } });
    render(<ImportLauncher profile={profile} onImportStarted={() => {}} />);
    expect(screen.getByText(t('profiles.preferences.use_global'))).toBeDefined();
  });

  test('renders the per-profile max_games override when set', () => {
    const profile = makeProfile({ preferences: { auto_sync_enabled: true, sync_max_games: 250 } });
    render(<ImportLauncher profile={profile} onImportStarted={() => {}} />);
    expect(screen.getByText('250')).toBeDefined();
  });

  test('renders never_synced when last_game_sync_at is null', () => {
    const profile = makeProfile({ last_game_sync_at: null });
    render(<ImportLauncher profile={profile} onImportStarted={() => {}} />);
    expect(screen.getByText(t('profiles.list.never_synced'))).toBeDefined();
  });

  test('renders last_game_sync_at as a relative-time string, not raw ISO', () => {
    const recent = new Date(Date.now() - 60_000).toISOString();
    const profile = makeProfile({ last_game_sync_at: recent });
    render(<ImportLauncher profile={profile} onImportStarted={() => {}} />);
    // Whatever formatRelativeAgo returns, it must NOT be the raw ISO.
    expect(screen.queryByText(recent)).toBeNull();
    expect(screen.queryByText(t('profiles.list.never_synced'))).toBeNull();
  });

  test('dispatches sync and notifies parent on Run import click', async () => {
    const onImportStarted = vi.fn();
    const profile = makeProfile({ id: 7 });
    render(<ImportLauncher profile={profile} onImportStarted={onImportStarted} />);
    fireEvent.click(screen.getByRole('button', { name: t('profiles.bulk_import.run_button') }));
    await waitFor(() => {
      expect(client.profiles.sync).toHaveBeenCalledWith(7);
      expect(onImportStarted).toHaveBeenCalledWith('job-1');
    });
  });

  test('renders Edit preferences link with deep-link query', () => {
    const profile = makeProfile({ id: 42 });
    const { container } = render(<ImportLauncher profile={profile} onImportStarted={() => {}} />);
    const link = container.querySelector('a.import-launcher__edit-link') as HTMLAnchorElement;
    expect(link).toBeDefined();
    expect(link.href).toContain('/profiles?profile_id=42&tab=preferences');
  });

  test('disables the Run button in demo mode', () => {
    const profile = makeProfile();
    render(<ImportLauncher profile={profile} demoMode onImportStarted={() => {}} />);
    expect(screen.getByRole('button', { name: t('profiles.bulk_import.run_button') }).disabled).toBe(true);
  });

  test('shows error alert on dispatch failure', async () => {
    vi.mocked(client.profiles.sync).mockRejectedValueOnce(new Error('boom'));
    render(<ImportLauncher profile={makeProfile()} onImportStarted={() => {}} />);
    fireEvent.click(screen.getByRole('button', { name: t('profiles.bulk_import.run_button') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
    });
  });
});
