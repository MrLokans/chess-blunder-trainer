import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { JobCard } from '../../src/components/JobCard';

describe('JobCard', () => {
  const defaultProps = {
    fetchStatus: vi.fn(),
    startJob: vi.fn(),
    startedMessage: 'Analysis started!',
    completedMessage: 'Analysis complete!',
    failedPrefix: 'Analysis failed: ',
  };

  beforeEach(() => {
    vi.resetAllMocks();
  });

  test('shows start button when no job is running', async () => {
    defaultProps.fetchStatus.mockResolvedValue({ status: 'idle' });
    render(<JobCard {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start/i })).toBeDefined();
    });
  });

  test('shows progress bar when job is running', async () => {
    defaultProps.fetchStatus.mockResolvedValue({
      status: 'running',
      job_id: 'abc',
      progress_current: 30,
      progress_total: 100,
    });
    render(<JobCard {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('30/100 (30%)')).toBeDefined();
    });
  });

  test('starts job on button click', async () => {
    const user = userEvent.setup();
    defaultProps.fetchStatus.mockResolvedValue({ status: 'idle' });
    defaultProps.startJob.mockResolvedValue({ job_id: 'new-job' });

    render(<JobCard {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /start/i })).toBeDefined();
    });

    await user.click(screen.getByRole('button', { name: /start/i }));
    expect(defaultProps.startJob).toHaveBeenCalled();
  });

  test('displays success message on job completion via externalStatus', async () => {
    defaultProps.fetchStatus.mockResolvedValue({
      status: 'running',
      job_id: 'abc',
      progress_current: 30,
      progress_total: 100,
    });

    const { rerender } = render(<JobCard {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('30/100 (30%)')).toBeDefined();
    });

    rerender(<JobCard {...defaultProps} externalStatus={{ job_id: 'abc', status: 'completed' }} />);
    await waitFor(() => {
      expect(screen.getByText('Analysis complete!')).toBeDefined();
    });
  });

  test('displays error message on job failure via externalStatus', async () => {
    defaultProps.fetchStatus.mockResolvedValue({
      status: 'running',
      job_id: 'abc',
      progress_current: 10,
      progress_total: 100,
    });

    const { rerender } = render(<JobCard {...defaultProps} />);
    await waitFor(() => {
      expect(screen.getByText('10/100 (10%)')).toBeDefined();
    });

    rerender(<JobCard {...defaultProps} externalStatus={{ job_id: 'abc', status: 'failed', error_message: 'timeout' }} />);
    await waitFor(() => {
      expect(screen.getByText('Analysis failed: timeout')).toBeDefined();
    });
  });

  test('calls onComplete callback when job finishes', async () => {
    const onComplete = vi.fn();
    defaultProps.fetchStatus.mockResolvedValue({
      status: 'running',
      job_id: 'abc',
      progress_current: 99,
      progress_total: 100,
    });

    const { rerender } = render(<JobCard {...defaultProps} onComplete={onComplete} />);
    await waitFor(() => {
      expect(screen.getByText('99/100 (99%)')).toBeDefined();
    });

    rerender(<JobCard {...defaultProps} onComplete={onComplete} externalStatus={{ job_id: 'abc', status: 'completed' }} />);
    await waitFor(() => {
      expect(onComplete).toHaveBeenCalled();
    });
  });
});
