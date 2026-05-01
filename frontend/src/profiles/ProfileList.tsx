import type { Profile } from '../types/profiles';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { formatRelativeAgo } from '../shared/relative-time';

export interface ProfileListProps {
  profiles: Profile[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

const PLATFORM_LABEL: Record<Profile['platform'], string> = {
  lichess: 'Lichess',
  chesscom: 'Chess.com',
};

function lastSyncLabel(profile: Profile): string {
  const ts = profile.last_game_sync_at ?? profile.last_validated_at;
  if (!ts) return t('profiles.list.never_synced');
  return t('profiles.list.last_sync', { ago: formatRelativeAgo(ts) });
}

export function ProfileList({ profiles, selectedId, onSelect }: ProfileListProps) {
  return (
    <ul class="profile-list" role="list">
      {profiles.map((p) => {
        const selected = p.id === selectedId;
        return (
          <li key={p.id} class={`profile-list__item${selected ? ' profile-list__item--selected' : ''}`}>
            <Card interactive onClick={() => { onSelect(p.id); }}>
              <div class="profile-list__row">
                <span class="profile-list__platform">{PLATFORM_LABEL[p.platform]}</span>
                {p.is_primary && (
                  <Badge variant="primary">
                    {t('profiles.list.primary_indicator')}
                  </Badge>
                )}
              </div>
              <div class="profile-list__username">{p.username}</div>
              <div class="profile-list__meta">{lastSyncLabel(p)}</div>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
