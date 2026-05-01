import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ProfilePreferencesTab } from '../../src/profiles/ProfilePreferencesTab';
import type { Profile } from '../../src/types/profiles';

function makeProfile(overrides: Partial<Profile> = {}): Profile {
  return {
    id: 11,
    platform: 'lichess',
    username: 'magnuscarlsen',
    is_primary: true,
    created_at: '2026-04-01T12:00:00Z',
    last_validated_at: null,
    preferences: { auto_sync_enabled: true, sync_max_games: 200 },
    stats: [],
    last_game_sync_at: null,
    last_stats_sync_at: null,
    ...overrides,
  };
}

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, 'fetch');
});

afterEach(() => {
  cleanup();
  fetchSpy.mockRestore();
  document.body.style.overflow = '';
});

describe('ProfilePreferencesTab', () => {
  test('renders auto-sync toggle and max-games input prefilled from profile', () => {
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('true');
    const input = screen.getByRole('spinbutton');
    expect((input as HTMLInputElement).value).toBe('200');
  });

  test('saving toggles auto_sync_enabled via PATCH', async () => {
    const onProfileChange = vi.fn();
    const updated = makeProfile({ preferences: { auto_sync_enabled: false, sync_max_games: 200 } });
    fetchSpy.mockResolvedValueOnce(new Response(JSON.stringify(updated), { status: 200 }));
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={onProfileChange}
        onProfileDeleted={() => {}}
      />,
    );
    await user.click(screen.getByRole('switch'));
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.save' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/11',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ preferences: { auto_sync_enabled: false, sync_max_games: 200 } }),
        }),
      );
    });
    await waitFor(() => {
      expect(onProfileChange).toHaveBeenCalledWith(updated);
    });
    expect(screen.getByText('profiles.preferences.saved')).toBeDefined();
  });

  test('clearing the max-games input PATCHes sync_max_games: null', async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response(JSON.stringify(makeProfile({ preferences: { auto_sync_enabled: true, sync_max_games: null } })), { status: 200 }),
    );
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    const input = screen.getByRole('spinbutton');
    await user.clear(input);
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.save' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/11',
        expect.objectContaining({
          body: JSON.stringify({ preferences: { auto_sync_enabled: true, sync_max_games: null } }),
        }),
      );
    });
  });

  test('non-positive max-games shows inline error, no PATCH fired', async () => {
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    const input = screen.getByRole('spinbutton');
    await user.clear(input);
    await user.type(input, '0');
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.save' }));
    expect(screen.getByRole('alert').textContent).toContain('profiles.preferences.max_games_invalid');
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test('Delete profile opens ConfirmDialog with primary focus on Detach', async () => {
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.delete_button' }));
    expect(screen.getByRole('dialog')).toBeDefined();
    await waitFor(() => {
      expect(document.activeElement?.textContent).toBe('profiles.delete.detach_games');
    });
  });

  test('Detach button DELETEs with detach_games=true and calls onProfileDeleted', async () => {
    const onProfileDeleted = vi.fn();
    fetchSpy.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={onProfileDeleted}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.delete_button' }));
    await user.click(screen.getByRole('button', { name: 'profiles.delete.detach_games' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/11?detach_games=true',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
    await waitFor(() => {
      expect(onProfileDeleted).toHaveBeenCalledWith(11);
    });
  });

  test('Delete-games-too DELETEs with detach_games=false (cascade)', async () => {
    const onProfileDeleted = vi.fn();
    fetchSpy.mockResolvedValueOnce(new Response(null, { status: 204 }));
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={onProfileDeleted}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.delete_button' }));
    await user.click(screen.getByRole('button', { name: 'profiles.delete.delete_games' }));
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        '/api/profiles/11?detach_games=false',
        expect.objectContaining({ method: 'DELETE' }),
      );
    });
    await waitFor(() => {
      expect(onProfileDeleted).toHaveBeenCalledWith(11);
    });
  });

  test('Cancel in confirm dialog closes without an API call', async () => {
    const user = userEvent.setup();
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'profiles.preferences.delete_button' }));
    await user.click(screen.getByRole('button', { name: 'profiles.delete.cancel' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  test('switching to a different profile resets the form', () => {
    const { rerender } = render(
      <ProfilePreferencesTab
        profile={makeProfile({ preferences: { auto_sync_enabled: true, sync_max_games: 200 } })}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    const input = screen.getByRole('spinbutton');
    expect((input as HTMLInputElement).value).toBe('200');
    rerender(
      <ProfilePreferencesTab
        profile={makeProfile({ id: 99, preferences: { auto_sync_enabled: false, sync_max_games: null } })}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
      />,
    );
    const input2 = screen.getByRole('spinbutton');
    expect((input2 as HTMLInputElement).value).toBe('');
    expect(screen.getByRole('switch').getAttribute('aria-checked')).toBe('false');
  });

  test('demo mode disables both inputs and the save/delete buttons', () => {
    render(
      <ProfilePreferencesTab
        profile={makeProfile()}
        onProfileChange={() => {}}
        onProfileDeleted={() => {}}
        demoMode
      />,
    );
    expect(screen.getByRole('switch').hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('spinbutton').hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: 'profiles.preferences.save' }).hasAttribute('disabled')).toBe(true);
    expect(screen.getByRole('button', { name: 'profiles.preferences.delete_button' }).hasAttribute('disabled')).toBe(true);
  });
});
