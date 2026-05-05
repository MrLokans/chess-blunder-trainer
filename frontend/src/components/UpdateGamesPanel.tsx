import { useState } from 'preact/hooks';
import { client } from '../shared/api';
import { formatRelativeAgo } from '../shared/relative-time';
import type { Profile } from '../types/profiles';
import { PLATFORM_LABEL } from '../types/profiles';
import { Alert } from './Alert';
import { Button } from './Button';
import { EmptyState } from './EmptyState';

export interface UpdateGamesPanelProps {
  profiles: Profile[];
  loading?: boolean;
  demoMode?: boolean;
}

interface Status {
  type: 'success' | 'error';
  text: string;
}

export function UpdateGamesPanel({
  profiles,
  loading = false,
  demoMode = false,
}: UpdateGamesPanelProps) {
  const [dispatching, setDispatching] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);

  if (loading) {
    return <p class="section-description">{t('common.loading')}</p>;
  }

  if (profiles.length === 0) {
    return (
      <EmptyState
        title={t('management.update.empty_title')}
        message={t('management.update.empty_message')}
        action={
          <a class="btn btn--primary btn--md" href="/profiles">
            {t('management.update.empty_cta')}
          </a>
        }
      />
    );
  }

  async function handleUpdate() {
    setStatus(null);
    setDispatching(true);
    const settled = await Promise.allSettled(
      profiles.map((p) => client.profiles.sync(p.id)),
    );
    const outcome = settled.reduce(
      (acc, r) => {
        if (r.status === 'fulfilled') {
          acc.successes += 1;
        } else {
          acc.failures += 1;
        }
        return acc;
      },
      { successes: 0, failures: 0 },
    );
    if (outcome.failures === 0) {
      setStatus({
        type: 'success',
        text: t('management.update.started', { count: outcome.successes }),
      });
    } else if (outcome.successes === 0) {
      setStatus({
        type: 'error',
        text: t('management.update.all_failed', { count: outcome.failures }),
      });
    } else {
      setStatus({
        type: 'error',
        text: t('management.update.partial_failure', {
          successes: outcome.successes,
          failures: outcome.failures,
        }),
      });
    }
    setDispatching(false);
  }

  return (
    <div class="update-games-panel">
      <ul class="update-games-panel__profiles">
        {profiles.map((profile) => (
          <li key={profile.id} class="update-games-panel__profile">
            <span class="update-games-panel__profile-name">
              {PLATFORM_LABEL[profile.platform]} — {profile.username}
            </span>
            <span class="update-games-panel__profile-last-sync">
              {profile.last_game_sync_at
                ? formatRelativeAgo(profile.last_game_sync_at)
                : t('profiles.list.never_synced')}
            </span>
          </li>
        ))}
      </ul>

      {status && <Alert type={status.type} message={status.text} />}

      <div class="update-games-panel__actions">
        <Button
          variant="primary"
          onClick={() => { void handleUpdate(); }}
          loading={dispatching}
          disabled={demoMode}
        >
          {t('management.update.button')}
        </Button>
      </div>
    </div>
  );
}
