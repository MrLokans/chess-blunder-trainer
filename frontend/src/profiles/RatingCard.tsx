import { useEffect, useState } from 'preact/hooks';
import type { ProfileStatSnapshot } from '../types/profiles';
import { Card } from '../components/Card';
import { Sparkline } from '../components/Sparkline';
import { client, ApiError } from '../shared/api';
import { formatRelativeAgo } from '../shared/relative-time';

export interface RatingCardProps {
  stat: ProfileStatSnapshot;
  profileId: number;
}

export function RatingCard({ stat, profileId }: RatingCardProps) {
  const ratingDisplay = stat.rating !== null
    ? String(stat.rating)
    : t('profiles.overview.no_rating');

  const [history, setHistory] = useState<number[]>([]);

  useEffect(() => {
    let cancelled = false;
    client.profiles
      .ratingHistory(profileId, stat.mode)
      .then((resp) => {
        if (cancelled) return;
        setHistory(resp.points.map((p) => p.rating));
      })
      .catch((err: unknown) => {
        // Silent on error: sparkline is best-effort, not load-blocking.
        // Log only; the card still renders the headline rating.
        if (err instanceof ApiError || err instanceof Error) {
          console.warn('rating-history fetch failed', stat.mode, err.message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [profileId, stat.mode]);

  const hasTrend = history.length >= 2;

  return (
    <Card>
      <div class="rating-card">
        <div class="rating-card__mode">
          {t(`profiles.stats.mode.${stat.mode}`)}
        </div>
        <div class="rating-card__rating">{ratingDisplay}</div>
        <div class="rating-card__trend">
          {hasTrend ? (
            <Sparkline
              values={history}
              width={180}
              ariaLabel={t('profiles.overview.sparkline_label', {
                mode: t(`profiles.stats.mode.${stat.mode}`),
              })}
            />
          ) : (
            <span class="rating-card__trend-empty" aria-hidden="true">—</span>
          )}
        </div>
        <div class="rating-card__games">
          {t('profiles.overview.games_count', { count: stat.games_count })}
        </div>
        <div class="rating-card__synced">
          {stat.synced_at
            ? t('profiles.overview.synced_ago', { ago: formatRelativeAgo(stat.synced_at) })
            : ' '}
        </div>
      </div>
    </Card>
  );
}
