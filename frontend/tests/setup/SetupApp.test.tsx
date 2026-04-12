import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { SetupApp } from '../../src/setup/SetupApp';

vi.mock('../../src/shared/api', () => ({
  client: {
    setup: {
      validateUsername: vi.fn().mockResolvedValue({ valid: true }),
      complete: vi.fn().mockResolvedValue({ import_job_ids: [] }),
    },
    analysis: {
      status: vi.fn().mockResolvedValue({ status: 'idle' }),
    },
    jobs: {
      getImportStatus: vi.fn().mockResolvedValue({ status: 'completed' }),
    },
  },
}));

import { client } from '../../src/shared/api';

describe('SetupApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
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

  test('calls validateUsername when lichess input changes', async () => {
    vi.useFakeTimers();
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'testuser' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(client.setup.validateUsername).toHaveBeenCalledWith('lichess', 'testuser');
    });
    vi.useRealTimers();
  });

  test('calls validateUsername when chesscom input changes', async () => {
    vi.useFakeTimers();
    render(<SetupApp />);
    const chesscomInput = screen.getByLabelText(t('setup.chesscom_label'));
    fireEvent.input(chesscomInput, { target: { value: 'chessplayer' } });
    vi.advanceTimersByTime(600);
    await waitFor(() => {
      expect(client.setup.validateUsername).toHaveBeenCalledWith('chesscom', 'chessplayer');
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
    vi.mocked(client.setup.validateUsername).mockResolvedValueOnce({ valid: false });
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

  test('calls setup.complete on valid form submission', async () => {
    vi.mocked(client.setup.validateUsername).mockResolvedValue({ valid: true });
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    const submitBtn = screen.getByRole('button', { name: t('setup.submit') });
    fireEvent.click(submitBtn);
    await waitFor(() => {
      expect(client.setup.complete).toHaveBeenCalledWith({ lichess: 'myuser', chesscom: '' });
    });
  });

  test('redirects to home after successful setup', async () => {
    vi.mocked(client.setup.validateUsername).mockResolvedValue({ valid: true });
    vi.mocked(client.setup.complete).mockResolvedValue({ import_job_ids: [] });
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(window.location.href).toBe('/');
    });
  });

  test('shows error when API call fails', async () => {
    vi.mocked(client.setup.validateUsername).mockResolvedValue({ valid: true });
    vi.mocked(client.setup.complete).mockRejectedValueOnce(new Error('Server error'));
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'myuser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText('Server error')).toBeDefined();
    });
  });

  test('shows error for invalid username on submission', async () => {
    vi.mocked(client.setup.validateUsername).mockResolvedValue({ valid: false });
    render(<SetupApp />);
    const lichessInput = screen.getByLabelText(t('setup.lichess_label'));
    fireEvent.input(lichessInput, { target: { value: 'baduser' } });
    fireEvent.click(screen.getByRole('button', { name: t('setup.submit') }));
    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeDefined();
      expect(screen.getByText(t('setup.lichess_not_found', { username: 'baduser' }))).toBeDefined();
    });
  });

  test('shows progress section while waiting for analysis', async () => {
    vi.mocked(client.setup.validateUsername).mockResolvedValue({ valid: true });
    vi.mocked(client.setup.complete).mockResolvedValue({ import_job_ids: ['job1'] });
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
