import type { ProfileStatSnapshot } from '../types/profiles';
import { Card } from '../components/Card';
import { formatRelativeAgo } from '../shared/relative-time';

export interface RatingCardProps {
  stat: ProfileStatSnapshot;
}

export function RatingCard({ stat }: RatingCardProps) {
  const ratingDisplay = stat.rating !== null
    ? String(stat.rating)
    : t('profiles.overview.no_rating');

  return (
    <Card>
      <div class="rating-card">
        <div class="rating-card__mode">
          {t(`profiles.stats.mode.${stat.mode}`)}
        </div>
        <div class="rating-card__rating">{ratingDisplay}</div>
        <div class="rating-card__games">
          {t('profiles.overview.games_count', { count: stat.games_count })}
        </div>
        {stat.synced_at && (
          <div class="rating-card__synced">
            {t('profiles.overview.synced_ago', { ago: formatRelativeAgo(stat.synced_at) })}
          </div>
        )}
      </div>
    </Card>
  );
}
