import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { ImportApp } from '../../src/import/ImportApp';

vi.mock('../../src/shared/api', () => ({
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  },
  client: {
    importPgn: vi.fn(),
    jobs: {
      getImportStatus: vi.fn(),
    },
  },
}));

import { client } from '../../src/shared/api';

const SAMPLE_PGN = '[White "Alice"]\n[Black "Bob"]\n1. e4 e5 *';

describe('ImportApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('renders textarea and submit button', () => {
    render(<ImportApp demoMode={false} />);
    expect(screen.getByPlaceholderText(t('import.placeholder'))).toBeDefined();
    expect(screen.getByText(t('import.submit'))).toBeDefined();
  });

  test('hides submit button in demo mode', () => {
    render(<ImportApp demoMode={true} />);
    expect(screen.queryByText(t('import.submit'))).toBeNull();
  });

  test('shows analyzing spinner during import', async () => {
    vi.mocked(client.importPgn).mockResolvedValue({ success: true, job_id: 'job-1' });
    vi.mocked(client.jobs.getImportStatus).mockResolvedValue({ status: 'pending' });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText(t('import.analyzing'))).toBeDefined();
    });
  });

  test('shows results when job completes', async () => {
    vi.mocked(client.importPgn).mockResolvedValue({ success: true, job_id: 'job-1' });
    vi.mocked(client.jobs.getImportStatus).mockResolvedValue({
      status: 'completed',
      result: {
        eco_code: 'C20',
        eco_name: 'King Pawn Game',
        total_moves: 40,
        blunders: 2,
        mistakes: 3,
        inaccuracies: 5,
      },
    });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText(t('import.success'))).toBeDefined();
    });

    expect(screen.getByText('C20 \u2014 King Pawn Game')).toBeDefined();
    expect(screen.getByText('40')).toBeDefined();
    expect(screen.getByText('2')).toBeDefined();
    expect(screen.getByText('3')).toBeDefined();
    expect(screen.getByText('5')).toBeDefined();
  });

  test('shows error when import API returns failure', async () => {
    vi.mocked(client.importPgn).mockResolvedValue({
      success: false,
      errors: ['Invalid PGN format'],
    });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: 'bad pgn' } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText('Invalid PGN format')).toBeDefined();
    });
  });

  test('shows error when job fails', async () => {
    vi.mocked(client.importPgn).mockResolvedValue({ success: true, job_id: 'job-1' });
    vi.mocked(client.jobs.getImportStatus).mockResolvedValue({
      status: 'failed',
      error_message: 'Analysis engine error',
    });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText('Analysis engine error')).toBeDefined();
    });
  });

  test('shows error on network failure', async () => {
    vi.mocked(client.importPgn).mockRejectedValue(new Error('Network error'));

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText('Network error')).toBeDefined();
    });
  });

  test('polls until job is complete', async () => {
    vi.useFakeTimers();
    vi.mocked(client.importPgn).mockResolvedValue({ success: true, job_id: 'job-1' });
    vi.mocked(client.jobs.getImportStatus)
      .mockResolvedValueOnce({ status: 'pending' })
      .mockResolvedValueOnce({ status: 'running' })
      .mockResolvedValueOnce({ status: 'completed', result: { blunders: 1, mistakes: 0, inaccuracies: 0, total_moves: 10 } });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    // First poll fires immediately after importPgn resolves
    await vi.runAllTimersAsync();
    // Advance through poll intervals until all mocked responses are consumed
    await vi.runAllTimersAsync();
    await vi.runAllTimersAsync();

    vi.useRealTimers();

    await waitFor(() => {
      expect(screen.getByText(t('import.success'))).toBeDefined();
    });
  });

  test('submit button disabled when textarea is empty', () => {
    render(<ImportApp demoMode={false} />);
    const btn = screen.getByText(t('import.submit')) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
  });

  test('go to trainer link shown after success', async () => {
    vi.mocked(client.importPgn).mockResolvedValue({ success: true, job_id: 'job-1' });
    vi.mocked(client.jobs.getImportStatus).mockResolvedValue({
      status: 'completed',
      result: { total_moves: 10, blunders: 0, mistakes: 0, inaccuracies: 0 },
    });

    render(<ImportApp demoMode={false} />);

    const textarea = screen.getByPlaceholderText(t('import.placeholder'));
    fireEvent.input(textarea, { target: { value: SAMPLE_PGN } });
    fireEvent.click(screen.getByText(t('import.submit')));

    await waitFor(() => {
      expect(screen.getByText(t('import.results.go_to_trainer'))).toBeDefined();
    });
  });
});
