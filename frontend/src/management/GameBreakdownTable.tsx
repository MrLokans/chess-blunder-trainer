import { DataTable } from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import type { GameBreakdownItem } from '../types/dashboard';

export function GameBreakdownTable({ items }: { items: GameBreakdownItem[] }) {
  if (items.length === 0) {
    return <div class="no-data-message">{t('dashboard.no_data')}</div>;
  }

  const columns: Column<GameBreakdownItem>[] = [
    { key: 'source', header: t('dashboard.chart.source') },
    { key: 'username', header: t('dashboard.chart.username') },
    { key: 'total_games', header: t('dashboard.chart.total_games'), render: row => String(row.total_games) },
    { key: 'analyzed_games', header: t('dashboard.chart.analyzed'), render: row => String(row.analyzed_games) },
    { key: 'pending_games', header: t('dashboard.chart.pending'), render: row => String(row.pending_games) },
  ];

  return (
    <DataTable
      columns={columns}
      rows={items}
      rowKey={row => `${row.source}-${row.username}`}
    />
  );
}
