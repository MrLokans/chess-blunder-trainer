import { useState, useCallback } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import type { Profile } from '../types/profiles';
import { PLATFORM_LABEL } from '../types/profiles';
import { Button } from '../components/Button';
import { Badge } from '../components/Badge';
import { Alert } from '../components/Alert';
import { RatingCard } from './RatingCard';
import { formatRelativeAgo } from '../shared/relative-time';

export interface OverviewToast {
  type: 'success' | 'error';
  text: string;
}

export interface ProfileOverviewTabProps {
  profile: Profile;
  onProfileChange: (next: Profile) => void;
  /** Toast lifted to ProfilesApp so it survives a tab switch. */
  onSyncToast: (toast: OverviewToast) => void;
  demoMode?: boolean;
}

interface Status {
  type: 'success' | 'error';
  text: string;
}

export function ProfileOverviewTab({
  profile,
  onProfileChange,
  onSyncToast,
  demoMode = false,
}: ProfileOverviewTabProps) {
  const [refreshStatus, setRefreshStatus] = useState<Status | null>(null);
  const [primaryStatus, setPrimaryStatus] = useState<Status | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [promoting, setPromoting] = useState(false);

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await client.profiles.sync(profile.id);
      onSyncToast({ type: 'success', text: t('profiles.overview.sync_started') });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      onSyncToast({ type: 'error', text: t('profiles.overview.sync_failed', { error: msg }) });
    } finally {
      setSyncing(false);
    }
  }, [profile.id, onSyncToast]);

  const handleRefreshStats = useCallback(async () => {
    setRefreshStatus(null);
    setRefreshing(true);
    try {
      const resp = await client.profiles.refreshStats(profile.id);
      onProfileChange({
        ...profile,
        stats: resp.stats,
        last_validated_at: resp.last_validated_at,
        last_stats_sync_at: resp.last_validated_at ?? profile.last_stats_sync_at,
      });
      setRefreshStatus({ type: 'success', text: t('profiles.overview.refresh_succeeded') });
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setRefreshStatus({ type: 'error', text: t('profiles.overview.refresh_failed', { error: msg }) });
    } finally {
      setRefreshing(false);
    }
  }, [profile, onProfileChange]);

  const handleMakePrimary = useCallback(async () => {
    setPrimaryStatus(null);
    setPromoting(true);
    try {
      const next = await client.profiles.update(profile.id, { is_primary: true });
      onProfileChange(next);
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error ? err.message : t('common.error');
      setPrimaryStatus({ type: 'error', text: t('profiles.overview.primary_failed', { error: msg }) });
    } finally {
      setPromoting(false);
    }
  }, [profile, onProfileChange]);

  return (
    <div class="profile-overview">
      <header class="profile-overview__header">
        <div class="profile-overview__identity">
          <h2 class="profile-overview__username">{profile.username}</h2>
          <Badge variant="info">{PLATFORM_LABEL[profile.platform]}</Badge>
        </div>
        <div class="profile-overview__primary">
          {profile.is_primary ? (
            <Badge variant="primary">{t('profiles.overview.primary_badge')}</Badge>
          ) : (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => { void handleMakePrimary(); }}
              loading={promoting}
              disabled={demoMode}
            >
              {t('profiles.overview.make_primary')}
            </Button>
          )}
        </div>
      </header>

      {primaryStatus?.type === 'error' && (
        <Alert type="error" message={primaryStatus.text} />
      )}

      <dl class="profile-overview__meta">
        <div class="profile-overview__meta-row">
          <dt>{t('profiles.overview.last_game_sync')}</dt>
          <dd>{profile.last_game_sync_at ? formatRelativeAgo(profile.last_game_sync_at) : t('profiles.list.never_synced')}</dd>
        </div>
        <div class="profile-overview__meta-row">
          <dt>{t('profiles.overview.last_stats_sync')}</dt>
          <dd>{profile.last_stats_sync_at ? formatRelativeAgo(profile.last_stats_sync_at) : t('profiles.list.never_synced')}</dd>
        </div>
      </dl>

      <section class="profile-overview__ratings">
        {profile.stats.length === 0 ? (
          <p class="profile-overview__empty-stats">{t('profiles.overview.no_stats_yet')}</p>
        ) : (
          <div class="profile-overview__rating-grid">
            {profile.stats.map((stat) => (
              <RatingCard key={stat.mode} stat={stat} profileId={profile.id} />
            ))}
          </div>
        )}
      </section>

      <div class="profile-overview__actions">
        <Button
          variant="primary"
          onClick={() => { void handleSync(); }}
          loading={syncing}
          disabled={demoMode}
        >
          {t('profiles.overview.sync_now')}
        </Button>
        <Button
          variant="secondary"
          onClick={() => { void handleRefreshStats(); }}
          loading={refreshing}
          disabled={demoMode}
        >
          {t('profiles.overview.refresh_stats')}
        </Button>
      </div>
      {refreshStatus && <Alert type={refreshStatus.type} message={refreshStatus.text} />}
    </div>
  );
}
