import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { SetupApp } from '../../src/setup/SetupApp';
import { ApiError } from '../../src/shared/api';

vi.mock('../../src/shared/api', async () => {
  const actual = await vi.importActual<typeof import('../../src/shared/api')>('../../src/shared/api');
  return {
    ...actual,
    client: {
      profiles: { validate: vi.fn(), create: vi.fn(), sync: vi.fn() },
      setup: { markComplete: vi.fn() },
      analysis: { status: vi.fn() },
      jobs: { getImportStatus: vi.fn() },
    },
  };
});

import { client } from '../../src/shared/api';

const VALIDATE_OK = {
  exists: true,
  already_tracked: false,
  profile_id: null,
  rate_limited: false,
};

// Full per-test reset: mockReset() also drains queued mockResolvedValueOnce
// values that mockClear() leaves behind. Without this, an Once override that
// outlives its test (because the source called it fewer times than queued)
// leaks into the next test as a phantom return value.
function resetClientDefaults() {
  const allMocks = [
    client.profiles.validate,
    client.profiles.create,
    client.profiles.sync,
    client.setup.markComplete,
    client.analysis.status,
    client.jobs.getImportStatus,
  ];
  for (const m of allMocks) vi.mocked(m).mockReset();
  vi.mocked(client.profiles.validate).mockResolvedValue(VALIDATE_OK);
  vi.mocked(client.profiles.create).mockImplementation(({ platform, username }) =>
    Promise.resolve({
      id: platform === 'lichess' ? 1 : 2,
      platform,
      username,
      is_primary: true,
      created_at: '2026-05-01T00:00:00Z',
      last_validated_at: null,
      preferences: { auto_sync_enabled: true, sync_max_games: null },
      stats: [],
      last_game_sync_at: null,
      last_stats_sync_at: null,
    }),
  );
  vi.mocked(client.profiles.sync).mockResolvedValue({ job_id: 'job1' });
  vi.mocked(client.setup.markComplete).mockResolvedValue({ success: true });
  vi.mocked(client.analysis.status).mockResolvedValue({ status: 'idle' });
  vi.mocked(client.jobs.getImportStatus).mockResolvedValue({ status: 'completed' });
}

describe('SetupApp', () => {
  beforeEach(() => {
    resetClientDefaults();
    Object.defineProperty(window, 'location', {
      value: { href: '' },
      writable: true,
    });
  });

  test('renders both username input fields', () => {
    render(<SetupApp />);
    expect(screen.getByLabelText(t('setup.lichess_label'))).toBeDefined();
    expect(screen.getByLabelText(t('setup.chesscom_label'))).toBeDefined();
  });

  test('renders submit button', () => {
    render(<SetupApp />);
    expect(screen.getByRole('button', { name: t('setup.submit') })).toBeDefined();
  });

  test('shows username required info alert', () => {
    render(<SetupApp />);
    expect(screen.getByText(t('setup.username_required'))).toBeDefined();
  });

  test('shows error when submitting with no usernames', async () => {
    render(<SetupApp />);
    const submitBtn = screen.getByRole('button', { name: t('setup.submit') });
    fireEvent.click(submitBtn);
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(t('setup.username_error'))).toBeDefined();
    });
  });

  test('calls profiles.validate when lichess input changes', async () => {
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'testuser' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(client.profiles.validate).toHaveBeenCalledWith({
        platform: 'lichess',
        username: 'testuser',
      });
    });
    vi.useRealTimers();
  });

  test('calls profiles.validate when chesscom input changes', async () => {
    vi.useFakeTimers();
    render(<SetupApp />);
    const chesscomInput = screen.getByLabelText(t('setup.chesscom_label'));
    fireEvent.input(chesscomInput, { target: { value: 'chessplayer' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(client.profiles.validate).toHaveBeenCalledWith({
        platform: 'chesscom',
        username: 'chessplayer',
      });
    });
    vi.useRealTimers();
  });

  test('shows valid status when username validates successfully', async () => {
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'validuser' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(screen.getByText(t('setup.username_valid'))).toBeDefined();
    });
    vi.useRealTimers();
  });

  test('shows invalid status when username fails validation', async () => {
    vi.mocked(client.profiles.validate).mockResolvedValueOnce({
      exists: false,
      already_tracked: false,
      profile_id: null,
      rate_limited: false,
    });
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'baduser' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(screen.getByText(t('setup.username_invalid'))).toBeDefined();
    });
    vi.useRealTimers();
  });

  test('shows already-tracked status when profile already exists', async () => {
    vi.mocked(client.profiles.validate).mockResolvedValueOnce({
      exists: true,
      already_tracked: true,
      profile_id: 99,
      rate_limited: false,
    });
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'reused' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(screen.getByText(t('setup.already_tracked', { username: 'reused' }))).toBeDefined();
    });
    vi.useRealTimers();
  });

  test('shows rate-limited soft warning instead of hard error', async () => {
    vi.mocked(client.profiles.validate).mockResolvedValueOnce({
      exists: false,
      already_tracked: false,
      profile_id: null,
      rate_limited: true,
    });
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'flaky' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(screen.getByText(t('setup.rate_limited', { username: 'flaky' }))).toBeDefined();
    });
    vi.useRealTimers();
  });

  test('blocks submit when validation is rate-limited', async () => {
    // Once-values cover the synchronous submit-time call plus the eventual
    // debounced re-validation; using a persistent mockResolvedValue here
    // would leak the rate_limited base into later tests.
    vi.mocked(client.profiles.validate)
      .mockResolvedValueOnce({
        exists: false, already_tracked: false, profile_id: null, rate_limited: true,
      })
      .mockResolvedValueOnce({
        exists: false, already_tracked: false, profile_id: null, rate_limited: true,
      });
    render(<SetupApp />);
    fireEvent.input(screen.getByLabelText(t('setup.lichess_label')), { target: { value: 'flaky' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
    });
    expect(client.profiles.create).not.toHaveBeenCalled();
  });

  test('creates one profile + dispatches one sync when only Lichess filled', async () => {
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(client.profiles.create).toHaveBeenCalledTimes(1);
      expect(client.profiles.create).toHaveBeenCalledWith({
        platform: 'lichess',
        username: 'myuser',
        make_primary: true,
      });
      expect(client.profiles.sync).toHaveBeenCalledTimes(1);
      expect(client.profiles.sync).toHaveBeenCalledWith(1);
      expect(client.setup.markComplete).toHaveBeenCalledTimes(1);
    });
  });

  test('creates two profiles + dispatches two syncs when both fields filled', async () => {
    render(<SetupApp />);
    fireEvent.input(screen.getByLabelText(t('setup.lichess_label')), { target: { value: 'lichuser' } });
    fireEvent.input(screen.getByLabelText(t('setup.chesscom_label')), { target: { value: 'cdotcomuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(client.profiles.create).toHaveBeenCalledTimes(2);
      expect(client.profiles.sync).toHaveBeenCalledTimes(2);
      expect(client.setup.markComplete).toHaveBeenCalledTimes(1);
    });
  });

  test('redirects to home after successful setup', async () => {
    // Polling exits as soon as analysis.status returns 'completed' on the
    // first tick, so the redirect should fire after the first poll interval.
    vi.mocked(client.analysis.status).mockResolvedValue({ status: 'completed' });
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await vi.advanceTimersByTimeAsync(2500);
    await waitFor(() => {
      expect(window.location.href).toBe('/');
    });
    vi.useRealTimers();
  });

  test('shows error when profile create fails with non-409 error', async () => {
    vi.mocked(client.profiles.create).mockRejectedValueOnce(new Error('Server error'));
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText('Server error')).toBeDefined();
    });
  });

  test('reuses already_tracked profile_id at submit (partial-success retry)', async () => {
    // Scenario: a previous submit created the Lichess profile but the
    // Chess.com create failed mid-flight. User retries: validate now reports
    // already_tracked=true with a profile_id, the submit path skips create
    // and goes straight to sync — exactly what `knownProfileId` exists for.
    vi.mocked(client.profiles.validate).mockResolvedValue({
      exists: true,
      already_tracked: true,
      profile_id: 7,
      rate_limited: false,
    });
    vi.useFakeTimers();
    render(<SetupApp />);
    fireEvent.input(screen.getByLabelText(t('setup.lichess_label')), { target: { value: 'recovered' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(client.profiles.validate).toHaveBeenCalled();
    });
    vi.useRealTimers();

    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(client.profiles.sync).toHaveBeenCalledWith(7);
      expect(client.setup.markComplete).toHaveBeenCalledTimes(1);
    });
    expect(client.profiles.create).not.toHaveBeenCalled();
  });

  test('recovers from 409 conflict by recovering profile_id from validate', async () => {
    vi.mocked(client.profiles.create).mockRejectedValueOnce(new ApiError(409, 'already_tracked'));
    vi.mocked(client.profiles.validate).mockResolvedValueOnce({
      exists: true,
      already_tracked: false,
      profile_id: null,
      rate_limited: false,
    }); // initial submit-time validation
    vi.mocked(client.profiles.validate).mockResolvedValueOnce({
      exists: true,
      already_tracked: true,
      profile_id: 42,
      rate_limited: false,
    }); // recovery validation after 409

    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'racy' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(client.profiles.sync).toHaveBeenCalledWith(42);
      expect(client.setup.markComplete).toHaveBeenCalledTimes(1);
    });
  });

  test('shows error for invalid username on submission', async () => {
    vi.mocked(client.profiles.validate).mockResolvedValue({
      exists: false,
      already_tracked: false,
      profile_id: null,
      rate_limited: false,
    });
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'baduser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(t('setup.lichess_not_found', { username: 'baduser' }))).toBeDefined();
    });
    expect(client.profiles.create).not.toHaveBeenCalled();
  });

  test('shows progress section while waiting for analysis', async () => {
    vi.mocked(client.analysis.status).mockResolvedValue({ status: 'completed' });
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.queryByRole('button', { name: t('setup.submit') })).toBeNull();
    });
    vi.useRealTimers();
  });
});
