import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { AddProfileModal } from '../../src/profiles/AddProfileModal';
import type { Profile, ProfileValidateResponse } from '../../src/types/profiles';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    platform: 'lichess',
    username: 'test',
    is_primary: true,
    created_at: '2026-04-01T12:00:00Z',
    last_validated_at: null,
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [],
    last_game_sync_at: null,
    last_stats_sync_at: null,
    ...overrides,
  };
}

function validateResponse(overrides: Partial<ProfileValidateResponse> = {}): Response {
  const body: ProfileValidateResponse = {
    exists: true,
    already_tracked: false,
    profile_id: null,
    rate_limited: false,
    ...overrides,
  };
  return new Response(JSON.stringify(body), { status: 200 });
}

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  fetchSpy = vi.spyOn(globalThis, 'fetch');
});

afterEach(() => {
  cleanup();
  fetchSpy.mockRestore();
  vi.useRealTimers();
  document.body.style.overflow = '';
});

describe('AddProfileModal', () => {
  test('renders nothing when closed', () => {
    render(
      <AddProfileModal
        open={false}
        onClose={() => {}}
        onCreated={() => {}}
        existingProfiles={[]}
      />,
    );
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  test('default make_primary is true when no profile exists for the platform', () => {
    render(
      <AddProfileModal
        open={true}
        onClose={() => {}}
        onCreated={() => {}}
        existingProfiles={[]}
      />,
    );
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('true');
  });

  test('default make_primary is false when a profile already exists for the platform', () => {
    render(
      <AddProfileModal
        open={true}
        onClose={() => {}}
        onCreated={() => {}}
        existingProfiles={[makeProfile({ platform: 'lichess' })]}
      />,
    );
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('false');
  });

  test('typing username triggers debounced validation and shows valid state', async () => {
    fetchSpy.mockResolvedValueOnce(validateResponse({ exists: true, already_tracked: false }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={() => {}} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.type(screen.getByRole('textbox'), 'magnuscarlsen');
    expect(fetchSpy).not.toHaveBeenCalled();
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/validate',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ platform: 'lichess', username: 'magnuscarlsen' }),
        }),
      );
    });
    await waitFor(() => {
      expect(screen.getByText(/profiles\.add_modal\.validation\.valid/)).toBeDefined();
    });
  });

  test('not_found result disables submit and surfaces error', async () => {
    fetchSpy.mockResolvedValueOnce(validateResponse({ exists: false }));
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={() => {}} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.type(screen.getByRole('textbox'), 'nobody');
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('profiles.add_modal.validation.not_found');
    });
    expect(screen.getByRole('button', { name: 'profiles.add_modal.submit' })
      .hasAttribute('disabled')).toBe(true);
  });

  test('already_tracked result disables submit', async () => {
    fetchSpy.mockResolvedValueOnce(
      validateResponse({ exists: true, already_tracked: true, profile_id: 9 }),
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={() => {}} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.type(screen.getByRole('textbox'), 'taken');
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('profiles.add_modal.validation.already_tracked');
    });
    expect(screen.getByRole('button', { name: 'profiles.add_modal.submit' })
      .hasAttribute('disabled')).toBe(true);
  });

  test('rate_limited shows soft warning', async () => {
    fetchSpy.mockResolvedValueOnce(
      validateResponse({ exists: false, rate_limited: true }),
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={() => {}} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.type(screen.getByRole('textbox'), 'maybe');
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('profiles.add_modal.validation.rate_limited');
    });
  });

  test('successful submit POSTs to /api/profiles, calls onCreated and onClose', async () => {
    const created = makeProfile({ id: 42, username: 'newprofile' });
    fetchSpy.mockResolvedValueOnce(validateResponse({ exists: true, already_tracked: false }));
    fetchSpy.mockResolvedValueOnce(new Response(JSON.stringify(created), { status: 200 }));
    const onCreated = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal
        open={true}
        onClose={onClose}
        onCreated={onCreated}
        existingProfiles={[]}
      />,
    );
    await user.type(screen.getByRole('textbox'), 'newprofile');
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'profiles.add_modal.submit' })
        .hasAttribute('disabled')).toBe(false);
    });
    await user.click(screen.getByRole('button', { name: 'profiles.add_modal.submit' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ platform: 'lichess', username: 'newprofile', make_primary: true }),
        }),
      );
    });
    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(created);
      expect(onClose).toHaveBeenCalled();
    });
  });

  test('409 conflict on submit shows the race-condition message', async () => {
    fetchSpy.mockResolvedValueOnce(validateResponse({ exists: true, already_tracked: false }));
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'race' }), { status: 409 }),
    );
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={() => {}} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.type(screen.getByRole('textbox'), 'racy');
    vi.advanceTimersByTime(500);
    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'profiles.add_modal.submit' })
        .hasAttribute('disabled')).toBe(false);
    });
    await user.click(screen.getByRole('button', { name: 'profiles.add_modal.submit' }));
    await waitFor(() => {
      expect(screen.getByRole('alert').textContent).toContain('profiles.add_modal.race_conflict');
    });
  });

  test('Cancel closes without API call', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(
      <AddProfileModal open={true} onClose={onClose} onCreated={() => {}} existingProfiles={[]} />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.add_modal.cancel' }));
    expect(onClose).toHaveBeenCalled();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
