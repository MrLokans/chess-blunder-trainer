import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ProfilesApp } from '../../src/profiles/ProfilesApp';
import type { Profile } from '../../src/types/profiles';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 1,
    platform: 'lichess',
    username: 'magnuscarlsen',
    is_primary: true,
    created_at: '2026-04-01T12:00:00Z',
    last_validated_at: '2026-05-01T11:55:00Z',
    preferences: { auto_sync_enabled: true, sync_max_games: null },
    stats: [],
    last_game_sync_at: '2026-05-01T11:00:00Z',
    last_stats_sync_at: '2026-05-01T11:50:00Z',
    ...overrides,
  };
}

function mockListResponse(profiles: Profile[]): Response {
  return new Response(JSON.stringify({ profiles }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, 'fetch');
});

afterEach(() => {
  cleanup();
  fetchSpy.mockRestore();
  document.body.style.overflow = '';
  window.history.replaceState({}, '', '/profiles');
});

describe('ProfilesApp', () => {
  test('shows loading state then renders the profile list', async () => {
    fetchSpy.mockResolvedValueOnce(mockListResponse([makeProfile()]));
    render(<ProfilesApp />);
    expect(screen.getByText('common.loading')).toBeDefined();
    await waitFor(() => {
      expect(screen.getByText('magnuscarlsen')).toBeDefined();
    });
  });

  test('empty state shows when no profiles + clicking CTA opens add modal', async () => {
    fetchSpy.mockResolvedValueOnce(mockListResponse([]));
    const user = userEvent.setup();
    render(<ProfilesApp />);
    await waitFor(() => {
      expect(screen.getByText('profiles.empty_state.title')).toBeDefined();
    });
    await user.click(screen.getByRole('button', { name: 'profiles.empty_state.cta' }));
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  test('selects the first profile by default and clicking another switches selection', async () => {
    const profiles = [
      makeProfile({ id: 1, username: 'first' }),
      makeProfile({ id: 2, username: 'second', is_primary: false }),
    ];
    fetchSpy.mockResolvedValueOnce(mockListResponse(profiles));
    const user = userEvent.setup();
    render(<ProfilesApp />);

    await waitFor(() => {
      expect(screen.getByText('first')).toBeDefined();
    });
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'first' })).toBeDefined();
    });

    await user.click(screen.getByText('second'));
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'second' })).toBeDefined();
    });
  });

  test('?profile_id= URL param selects that profile', async () => {
    const profiles = [
      makeProfile({ id: 1, username: 'first' }),
      makeProfile({ id: 2, username: 'second', is_primary: false }),
    ];
    window.history.replaceState({}, '', '/profiles?profile_id=2');
    fetchSpy.mockResolvedValueOnce(mockListResponse(profiles));
    render(<ProfilesApp />);

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'second' })).toBeDefined();
    });
  });

  test('?tab= URL param sets the initial detail tab', async () => {
    window.history.replaceState({}, '', '/profiles?profile_id=1&tab=preferences');
    fetchSpy.mockResolvedValueOnce(mockListResponse([makeProfile({ id: 1 })]));
    render(<ProfilesApp />);

    await waitFor(() => {
      const prefs = screen.getByRole('tab', { name: /preferences/i });
      expect(prefs.getAttribute('aria-selected')).toBe('true');
    });
  });

  test('shows error message when API fails', async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'boom' }), { status: 500 }),
    );
    render(<ProfilesApp />);

    await waitFor(() => {
      const alert = screen.getByRole('alert');
      expect(alert.textContent).toContain('profiles.load_failed');
      expect(alert.textContent).toContain('boom');
    });
  });

  test('add-profile sidebar button opens the placeholder modal', async () => {
    fetchSpy.mockResolvedValueOnce(mockListResponse([makeProfile()]));
    const user = userEvent.setup();
    render(<ProfilesApp />);

    await waitFor(() => {
      expect(screen.getByText('magnuscarlsen')).toBeDefined();
    });
    await user.click(screen.getByRole('button', { name: 'profiles.add_button' }));
    expect(screen.getByRole('dialog')).toBeDefined();
  });

  test('demo mode swaps the add-modal body to the demo notice', async () => {
    fetchSpy.mockResolvedValueOnce(mockListResponse([makeProfile()]));
    const user = userEvent.setup();
    render(<ProfilesApp demoMode />);

    await waitFor(() => {
      expect(screen.getByText('magnuscarlsen')).toBeDefined();
    });
    await user.click(screen.getByRole('button', { name: 'profiles.add_button' }));
    expect(screen.getByText('profiles.add_modal.demo_disabled')).toBeDefined();
  });
});
