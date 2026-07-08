interface ReviewBannerProps {
  dueCount: number;
  onStart: () => void;
}

export function ReviewBanner({ dueCount, onStart }: ReviewBannerProps): preact.JSX.Element | null {
  if (dueCount <= 0) return null;
  return (
    <div class="review-banner" data-testid="srs-review-banner">
      <span class="review-banner-text">{t('trainer.srs.banner', { count: dueCount })}</span>
      <button type="button" class="review-banner-btn" data-testid="srs-start-review" onClick={onStart}>
        {t('trainer.srs.start')}
      </button>
    </div>
  );
}
