export interface RankedBar {
  key: string;
  label: string;
  value: number;
  display: string;
  detail?: string;
  // A catch-all row (unclassified blunders) is drawn but never singled out as the one to act on.
  muted?: boolean;
}

// Ink bars scaled to the largest row; the largest actionable row is the one to train, so it alone is full strength.
export function RankedBars({ rows, caption }: { rows: RankedBar[]; caption?: string }) {
  const max = Math.max(...rows.map(r => r.value), 0);
  if (rows.length === 0 || max <= 0) return null;
  const top = Math.max(...rows.filter(r => !r.muted).map(r => r.value), 0);

  return (
    <table class="ranked-bars">
      {caption && <caption class="sr-only">{caption}</caption>}
      <tbody>
        {rows.map(row => (
          <tr key={row.key} class={row.muted ? 'ranked-bars__row--muted' : row.value === top && top > 0 ? 'ranked-bars__row--top' : undefined} data-key={row.key}>
            <th scope="row" class="ranked-bars__label">{row.label}</th>
            <td class="ranked-bars__track" aria-hidden="true">
              <span class="ranked-bars__bar" style={{ width: `${String((row.value / max) * 100)}%` }} />
            </td>
            <td class="ranked-bars__value">
              {row.display}
              {row.detail && <span class="ranked-bars__detail">{row.detail}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
