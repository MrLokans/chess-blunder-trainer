import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/preact';
import { CacheManagement } from '../../src/settings/CacheManagement';
import { client } from '../../src/shared/api';

vi.mock('../../src/shared/api', () => ({
  client: {
    cache: {
      clear: vi.fn().mockResolvedValue({ cleared: ['stats', 'traps'] }),
    },
  },
}));

const clearButton = () =>
  screen.getByRole('button', { name: 'settings.cache.clear_button' });

describe('CacheManagement', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(client.cache.clear).mockResolvedValue({ cleared: ['stats'] });
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true));
  });

  test('renders the section title and the clear button', () => {
    render(<CacheManagement />);
    expect(screen.getByText('settings.cache.title')).toBeDefined();
    expect(clearButton()).toBeDefined();
  });

  test('does not call the API when the confirm is declined', () => {
    vi.stubGlobal('confirm', vi.fn().mockReturnValue(false));
    render(<CacheManagement />);

    fireEvent.click(clearButton());

    expect(client.cache.clear).not.toHaveBeenCalled();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  test('clears the cache and shows the success toast on confirm', async () => {
    render(<CacheManagement />);

    fireEvent.click(clearButton());

    await waitFor(() => {
      expect(screen.getByText('settings.cache.cleared_toast')).toBeDefined();
    });
    expect(screen.getByRole('alert')).toBeDefined();
    expect(client.cache.clear).toHaveBeenCalledTimes(1);
  });

  test('shows the error toast when the API call fails', async () => {
    vi.mocked(client.cache.clear).mockRejectedValueOnce(new Error('boom'));
    render(<CacheManagement />);

    fireEvent.click(clearButton());

    await waitFor(() => {
      expect(screen.getByText('settings.cache.error')).toBeDefined();
    });
  });
});
