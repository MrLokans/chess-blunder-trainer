export interface RankedBar {
  key: string;
  label: string;
  value: number;
  display: string;
  detail?: string;
  // A catch-all row (unclassified blunders) is drawn but never singled out as the one to act on.
  muted?: boolean;
  // Drawn normally but never picked as the leader, e.g. a rate resting on too few games.
  noLead?: boolean;
}

// A leader only earns the highlight when it clearly beats the runner-up.
const LEAD_MARGIN = 1.1;

export function leaderKey(rows: RankedBar[]): string | null {
  const ranked = rows.filter(r => !r.muted).sort((a, b) => b.value - a.value);
  const [first, second] = ranked;
  if (!first || first.value <= 0 || first.noLead) return null;
  return !second || first.value >= second.value * LEAD_MARGIN ? first.key : null;
}

interface RankedBarsProps {
  rows: RankedBar[];
  // Fixed top of the scale (e.g. 100 for rates); defaults to the largest row.
  scale?: number;
  // Off where a bigger bar is good news rather than the thing to train.
  highlight?: boolean;
}

export function RankedBars({ rows, scale, highlight = true }: RankedBarsProps) {
  if (rows.length === 0) return null;
  const top = scale ?? (Math.max(...rows.map(r => r.value)) || 1);
  const leader = highlight ? leaderKey(rows) : null;

  // Explicit roles keep row/header semantics when phones restyle the rows as grids.
  return (
    <table class="ranked-bars" role="table">
      <tbody role="rowgroup">
        {rows.map(row => (
          <tr
            key={row.key}
            role="row"
            class={row.muted ? 'ranked-bars__row--muted' : row.key === leader ? 'ranked-bars__row--top' : undefined}
            data-key={row.key}
          >
            <th scope="row" role="rowheader" class="ranked-bars__label">{row.label}</th>
            <td role="cell" class="ranked-bars__track">
              <span class="ranked-bars__bar" aria-hidden="true" style={{ width: `${String(Math.min(row.value / top, 1) * 100)}%` }} />
            </td>
            <td role="cell" class="ranked-bars__value">
              {row.display}
              {row.detail && <span class="ranked-bars__detail">{row.detail}</span>}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
