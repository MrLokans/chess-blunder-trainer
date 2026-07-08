interface InboxZeroCardProps {
  onContinue: () => void;
}

export function InboxZeroCard({ onContinue }: InboxZeroCardProps): preact.JSX.Element {
  return (
    <div class="inbox-zero-card" data-testid="srs-inbox-zero">
      <h2>{t('trainer.srs.inbox_zero_title')}</h2>
      <p>{t('trainer.srs.inbox_zero_message')}</p>
      {/* eslint-disable-next-line no-restricted-syntax -- CTA needs the .inbox-zero-btn hook; <Button> takes no className */}
      <button type="button" class="btn btn-primary inbox-zero-btn" onClick={onContinue}>
        {t('trainer.srs.continue')}
      </button>
    </div>
  );
}
