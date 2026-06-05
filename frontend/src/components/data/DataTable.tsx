import type { ComponentChildren } from 'preact';

export interface Column<Row> {
  key: string;
  header: string;
  render?: (row: Row) => ComponentChildren;
  className?: string;
}

export interface DataTableProps<Row> {
  columns: Column<Row>[];
  rows: Row[];
  rowKey: (row: Row) => string;
  className?: string;
}

function defaultCell(value: unknown): ComponentChildren {
  if (value === null || value === undefined) {
    return '—';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return value;
  }
  return null;
}

function cellValue(row: unknown, key: string): unknown {
  return row !== null && typeof row === 'object' ? Reflect.get(row, key) : undefined;
}

export function DataTable<Row>({ columns, rows, rowKey, className }: DataTableProps<Row>) {
  return (
    <table class={className}>
      <thead>
        <tr>
          {columns.map(col => (
            <th key={col.key}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map(row => (
          <tr key={rowKey(row)}>
            {columns.map(col => (
              <td key={col.key} class={col.className}>
                {col.render ? col.render(row) : defaultCell(cellValue(row, col.key))}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
