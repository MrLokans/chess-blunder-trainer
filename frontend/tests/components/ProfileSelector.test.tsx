import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ProfileSelector } from '../../src/components/ProfileSelector';
import type { Profile } from '../../src/types/profiles';

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

describe('ProfileSelector', () => {
  test('renders one option per profile', () => {
    const profiles = [
      makeProfile({ id: 1, platform: 'lichess', username: 'alice' }),
      makeProfile({ id: 2, platform: 'chesscom', username: 'bob' }),
    ];
    render(<ProfileSelector profiles={profiles} value={1} onChange={() => {}} />);
    expect(screen.getAllByRole('option')).toHaveLength(2);
    expect(screen.getByText(/Lichess.*alice/)).toBeDefined();
    expect(screen.getByText(/Chess\.com.*bob/)).toBeDefined();
  });

  test('marks the primary profile in the visible label', () => {
    const profiles = [
      makeProfile({ id: 1, username: 'alice', is_primary: true }),
      makeProfile({ id: 2, username: 'bob', is_primary: false }),
    ];
    render(<ProfileSelector profiles={profiles} value={1} onChange={() => {}} />);
    const aliceOption = screen.getByText(new RegExp(`alice.*${t('profiles.list.primary_indicator')}`));
    expect(aliceOption).toBeDefined();
  });

  test('calls onChange with the chosen profile id', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    const profiles = [
      makeProfile({ id: 5, username: 'alice' }),
      makeProfile({ id: 9, username: 'bob' }),
    ];
    render(<ProfileSelector profiles={profiles} value={5} onChange={onChange} />);
    await user.selectOptions(screen.getByRole('combobox'), '9');
    expect(onChange).toHaveBeenCalledWith(9);
  });

  test('disables when profiles list is empty', () => {
    render(<ProfileSelector profiles={[]} value={null} onChange={() => {}} />);
    expect(screen.getByRole('combobox').disabled).toBe(true);
  });

  test('respects explicit disabled prop', () => {
    const profiles = [makeProfile()];
    render(<ProfileSelector profiles={profiles} value={1} onChange={() => {}} disabled />);
    expect(screen.getByRole('combobox').disabled).toBe(true);
  });
});
