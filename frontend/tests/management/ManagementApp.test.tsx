import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { ManagementApp } from '../../src/management/ManagementApp';

vi.mock('../../src/shared/api', () => ({
  client: {
    system: {
      engineStatus: vi.fn().mockResolvedValue({ available: true, name: 'Stockfish 16', path: '/usr/bin/stockfish' }),
    },
    jobs: {
      startSync: vi.fn().mockResolvedValue({}),
    },
    profiles: {
      list: vi.fn().mockResolvedValue({ profiles: [] }),
      sync: vi.fn().mockResolvedValue({ job_id: 'sync-job-1' }),
    },
    analysis: {
      status: vi.fn().mockResolvedValue({ status: 'idle' }),
      start: vi.fn().mockResolvedValue({ job_id: 'analysis-job-1' }),
      stop: vi.fn().mockResolvedValue({}),
    },
    backfill: {
      phasesStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
      startPhases: vi.fn().mockResolvedValue({ job_id: 'phases-job-1' }),
      ecoStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
      startEco: vi.fn().mockResolvedValue({ job_id: 'eco-job-1' }),
      trapsStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
      startTraps: vi.fn().mockResolvedValue({ job_id: 'traps-job-1' }),
    },
    data: {
      deleteAll: vi.fn().mockResolvedValue({ job_id: 'delete-job-1' }),
      deleteStatus: vi.fn().mockResolvedValue({ status: 'idle' }),
    },
  },
}));

vi.mock('../../src/hooks/useWebSocket', () => ({
  useWebSocket: vi.fn().mockReturnValue({ on: vi.fn().mockReturnValue(() => {}) }),
}));

vi.mock('../../src/shared/debounce', () => ({
  debounce: (fn: (...args: unknown[]) => unknown) => fn,
}));

import { client } from '../../src/shared/api';

describe('ManagementApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal('htmx', { process: vi.fn(), trigger: vi.fn() });
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
  });

  describe('Engine status', () => {
    test('renders engine available status after loading', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByText(t('management.engine.available'))).toBeDefined();
      });
    });

    test('renders engine name and path', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByText('Stockfish 16')).toBeDefined();
        expect(screen.getByText('/usr/bin/stockfish')).toBeDefined();
      });
    });

    test('renders engine unavailable status when not available', async () => {
      vi.mocked(client.system.engineStatus).mockResolvedValueOnce({ available: false, path: '/missing/stockfish' });
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByText(t('management.engine.unavailable'))).toBeDefined();
      });
    });

    test('renders error when engine status fails to load', async () => {
      vi.mocked(client.system.engineStatus).mockRejectedValueOnce(new Error('connection refused'));
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByText(t('management.engine.load_failed', { error: 'connection refused' }))).toBeDefined();
      });
    });
  });

  describe('Bulk Import section', () => {
    test('shows empty state when there are no tracked profiles', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByText(t('profiles.bulk_import.empty_title'))).toBeDefined();
      });
    });

    test('renders run-import button when profiles are loaded', async () => {
      vi.mocked(client.profiles.list).mockResolvedValueOnce({
        profiles: [
          {
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
          },
        ],
      });
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('profiles.bulk_import.run_button') })).toBeDefined();
      });
    });

    test('hides bulk import panel in demo mode', async () => {
      render(<ManagementApp demoMode={true} />);
      await waitFor(() => {
        // The section heading still renders; the panel itself does not.
        expect(screen.queryByRole('button', { name: t('profiles.bulk_import.run_button') })).toBeNull();
      });
    });
  });

  describe('Sync section', () => {
    test('renders sync button when not in demo mode', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('management.sync.button') })).toBeDefined();
      });
    });

    test('hides sync button in demo mode', async () => {
      render(<ManagementApp demoMode={true} />);
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: t('management.sync.button') })).toBeNull();
      });
    });

    test('shows success message after sync', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('management.sync.button') })).toBeDefined();
      });
      fireEvent.click(screen.getByRole('button', { name: t('management.sync.button') }));
      await waitFor(() => {
        expect(screen.getByText(t('management.sync.started'))).toBeDefined();
      });
    });
  });

  describe('Job cards', () => {
    test('renders analysis job card when not in demo mode', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(client.analysis.status).toHaveBeenCalled();
      });
    });

    test('does not call analysis status in demo mode', async () => {
      render(<ManagementApp demoMode={true} />);
      await waitFor(() => {
        expect(screen.getByText(t('management.analysis.title'))).toBeDefined();
      });
      expect(client.analysis.status).not.toHaveBeenCalled();
    });

    test('renders backfill phases job card', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(client.backfill.phasesStatus).toHaveBeenCalled();
      });
    });

    test('renders eco backfill job card', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(client.backfill.ecoStatus).toHaveBeenCalled();
      });
    });

    test('renders traps backfill job card', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(client.backfill.trapsStatus).toHaveBeenCalled();
      });
    });
  });

  describe('Danger zone', () => {
    test('renders delete all button when not in demo mode', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('management.danger.button') })).toBeDefined();
      });
    });

    test('hides danger section in demo mode', async () => {
      render(<ManagementApp demoMode={true} />);
      await waitFor(() => {
        expect(screen.queryByRole('button', { name: t('management.danger.button') })).toBeNull();
      });
    });

    test('shows confirmation dialogs before deleting all data', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('management.danger.button') })).toBeDefined();
      });
      fireEvent.click(screen.getByRole('button', { name: t('management.danger.button') }));
      expect(window.confirm).toHaveBeenCalledTimes(2);
      expect(window.confirm).toHaveBeenCalledWith(t('management.danger.confirm1'));
      expect(window.confirm).toHaveBeenCalledWith(t('management.danger.confirm2'));
    });

    test('does not proceed when user cancels first confirmation', async () => {
      vi.stubGlobal('confirm', vi.fn().mockReturnValue(false));
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(screen.getByRole('button', { name: t('management.danger.button') })).toBeDefined();
      });
      fireEvent.click(screen.getByRole('button', { name: t('management.danger.button') }));
      expect(window.confirm).toHaveBeenCalledTimes(1);
    });
  });

  describe('Profile list for Bulk Import', () => {
    test('loads the profile list on mount', async () => {
      render(<ManagementApp demoMode={false} />);
      await waitFor(() => {
        expect(client.profiles.list).toHaveBeenCalled();
      });
    });
  });
});
