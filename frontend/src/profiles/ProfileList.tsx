import type { Profile } from '../types/profiles';
import { PLATFORM_LABEL, platformProfileUrl } from '../types/profiles';
import { Card } from '../components/Card';
import { Badge } from '../components/Badge';
import { formatRelativeAgo } from '../shared/relative-time';

export interface ProfileListProps {
  profiles: Profile[];
  selectedId: number | null;
  onSelect: (id: number) => void;
}

function lastGameSyncLabel(profile: Profile): string {
  // Only `last_game_sync_at` counts as "synced" here. `last_validated_at`
  // is bumped by validate / stats refresh and would mislead the user into
  // thinking games are up to date when only the existence check ran.
  if (!profile.last_game_sync_at) return t('profiles.list.never_synced');
  return t('profiles.list.last_sync', { ago: formatRelativeAgo(profile.last_game_sync_at) });
}

export function ProfileList({ profiles, selectedId, onSelect }: ProfileListProps) {
  return (
    <ul class="profile-list" role="list">
      {profiles.map((p) => {
        const selected = p.id === selectedId;
        return (
          <li key={p.id} class="profile-list__item">
            <Card interactive selected={selected} onClick={() => { onSelect(p.id); }}>
              <div class="profile-list__row">
                <span class="profile-list__platform">{PLATFORM_LABEL[p.platform]}</span>
                {p.is_primary && (
                  <Badge variant="primary">
                    {t('profiles.list.primary_indicator')}
                  </Badge>
                )}
              </div>
              <div class="profile-list__username-row">
                <span class="profile-list__username">{p.username}</span>
                <a
                  class="profile-list__platform-link"
                  href={platformProfileUrl(p.platform, p.username)}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => { e.stopPropagation(); }}
                  aria-label={t('profiles.list.open_on_platform', {
                    platform: PLATFORM_LABEL[p.platform],
                    username: p.username,
                  })}
                  title={t('profiles.list.open_on_platform', {
                    platform: PLATFORM_LABEL[p.platform],
                    username: p.username,
                  })}
                >
                  ↗
                </a>
              </div>
              <div class="profile-list__meta">{lastGameSyncLabel(p)}</div>
            </Card>
          </li>
        );
      })}
    </ul>
  );
}
