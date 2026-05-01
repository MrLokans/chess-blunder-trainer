import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { BulkImportPanel } from '../../src/components/BulkImportPanel';
import type { Profile } from '../../src/types/profiles';

vi.mock('../../src/shared/api', async () => {
  const actual = await vi.importActual<typeof import('../../src/shared/api')>('../../src/shared/api');
  return {
    ...actual,
    client: {
      profiles: { sync: vi.fn().mockResolvedValue({ job_id: 'job-1' }) },
    },
  };
});

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    platform: 'lichess',
    username: 'magnus',
    is_primary: false,
    created_at: '2026-04-01T00:00:00Z',
    last_validated_at: null,
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [],
    last_game_sync_at: null,
    last_stats_sync_at: null,
    ...overrides,
  };
}

describe('BulkImportPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('shows empty state when there are no profiles', () => {
    render(<BulkImportPanel profiles={[]} onImportStarted={() => {}} />);
    expect(screen.getByText(t('profiles.bulk_import.empty_title'))).toBeDefined();
    expect(screen.getByText(t('profiles.bulk_import.empty_cta'))).toBeDefined();
  });

  test('shows loading state while profiles are being fetched', () => {
    render(<BulkImportPanel profiles={[]} loading onImportStarted={() => {}} />);
    expect(screen.getByText(t('common.loading'))).toBeDefined();
  });

  test('preselects the primary profile when one is marked', () => {
    const profiles = [
      makeProfile({ id: 1, username: 'alice', is_primary: false }),
      makeProfile({ id: 2, username: 'bob', is_primary: true }),
    ];
    render(<BulkImportPanel profiles={profiles} onImportStarted={() => {}} />);
    expect(screen.getByRole('combobox').value).toBe('2');
  });

  test('preselects the first profile when none is primary', () => {
    const profiles = [
      makeProfile({ id: 1, username: 'alice' }),
      makeProfile({ id: 2, username: 'bob' }),
    ];
    render(<BulkImportPanel profiles={profiles} onImportStarted={() => {}} />);
    expect(screen.getByRole('combobox').value).toBe('1');
  });

  test('switches the visible launcher when the selector changes', async () => {
    const profiles = [
      makeProfile({ id: 1, username: 'alice', preferences: { auto_sync_enabled: true, sync_max_games: 100 } }),
      makeProfile({ id: 2, username: 'bob', preferences: { auto_sync_enabled: true, sync_max_games: 500 } }),
    ];
    const user = userEvent.setup();
    render(<BulkImportPanel profiles={profiles} onImportStarted={() => {}} />);
    expect(screen.getByText('100')).toBeDefined();
    await user.selectOptions(screen.getByRole('combobox'), '2');
    expect(screen.getByText('500')).toBeDefined();
  });
});
