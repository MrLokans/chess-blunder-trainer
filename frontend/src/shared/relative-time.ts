const MINUTE = 60;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const WEEK = 7 * DAY;

export function formatRelativeAgo(isoTimestamp: string, now: Date = new Date()): string {
  const ts = new Date(isoTimestamp);
  const seconds = Math.max(0, Math.floor((now.getTime() - ts.getTime()) / 1000));

  if (seconds < MINUTE) return t('time.just_now');
  if (seconds < HOUR) {
    const m = Math.floor(seconds / MINUTE);
    return t('time.minutes_ago', { count: m });
  }
  if (seconds < DAY) {
    const h = Math.floor(seconds / HOUR);
    return t('time.hours_ago', { count: h });
  }
  if (seconds < WEEK) {
    const d = Math.floor(seconds / DAY);
    return t('time.days_ago', { count: d });
  }
  return ts.toLocaleDateString();
}
