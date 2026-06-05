import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { DataTable } from '../../src/components/data/DataTable';
import type { Column } from '../../src/components/data/DataTable';

interface Item {
  id: string;
  name: string;
  count: number | null;
  note: string;
}

const alpha: Item = { id: 'a', name: 'Alpha', count: 0, note: '' };
const beta: Item = { id: 'b', name: 'Beta', count: null, note: 'hi' };
const rows: Item[] = [alpha, beta];

describe('DataTable', () => {
  test('renders headers in column order', () => {
    const columns: Column<Item>[] = [
      { key: 'name', header: 'Name' },
      { key: 'count', header: 'Count' },
    ];
    const { container } = render(<DataTable columns={columns} rows={rows} rowKey={r => r.id} />);
    const headers = [...container.querySelectorAll('thead th')].map(th => th.textContent);
    expect(headers).toEqual(['Name', 'Count']);
  });

  test('renders cells in column order matching the row', () => {
    const columns: Column<Item>[] = [
      { key: 'name', header: 'Name' },
      { key: 'note', header: 'Note' },
    ];
    const { container } = render(<DataTable columns={columns} rows={[alpha]} rowKey={r => r.id} />);
    const cells = [...container.querySelectorAll('tbody tr td')].map(td => td.textContent);
    expect(cells).toEqual(['Alpha', '']);
  });

  test('custom render overrides the default cell', () => {
    const columns: Column<Item>[] = [
      { key: 'name', header: 'Name', render: r => <strong>{r.name.toUpperCase()}</strong> },
    ];
    const { container } = render(<DataTable columns={columns} rows={[alpha]} rowKey={r => r.id} />);
    expect(container.querySelector('tbody td strong')?.textContent).toBe('ALPHA');
  });

  test('renders em-dash for null and undefined values', () => {
    const columns: Column<Item>[] = [{ key: 'count', header: 'Count' }];
    const { container } = render(<DataTable columns={columns} rows={[beta]} rowKey={r => r.id} />);
    expect(container.querySelector('tbody td')?.textContent).toBe('—');
  });

  test('does NOT render em-dash for 0', () => {
    const columns: Column<Item>[] = [{ key: 'count', header: 'Count' }];
    const { container } = render(<DataTable columns={columns} rows={[alpha]} rowKey={r => r.id} />);
    expect(container.querySelector('tbody td')?.textContent).toBe('0');
  });

  test('does NOT render em-dash for empty string', () => {
    const columns: Column<Item>[] = [{ key: 'note', header: 'Note' }];
    const { container } = render(<DataTable columns={columns} rows={[alpha]} rowKey={r => r.id} />);
    expect(container.querySelector('tbody td')?.textContent).toBe('');
  });

  test('uses rowKey to key each row uniquely', () => {
    const columns: Column<Item>[] = [{ key: 'name', header: 'Name' }];
    const { container } = render(<DataTable columns={columns} rows={rows} rowKey={r => r.id} />);
    const bodyRows = container.querySelectorAll('tbody tr');
    expect(bodyRows.length).toBe(2);
    expect(bodyRows[0]?.textContent).toBe('Alpha');
    expect(bodyRows[1]?.textContent).toBe('Beta');
  });

  test('passes className through to the table element', () => {
    const columns: Column<Item>[] = [{ key: 'name', header: 'Name' }];
    const { container } = render(
      <DataTable columns={columns} rows={rows} rowKey={r => r.id} className="starred-table" />,
    );
    expect(container.querySelector('table')?.className).toBe('starred-table');
  });

  test('applies Column.className to the matching td cells', () => {
    const columns: Column<Item>[] = [
      { key: 'name', header: 'Name' },
      { key: 'count', header: 'Count', className: 'eval-swing' },
    ];
    const { container } = render(<DataTable columns={columns} rows={[alpha]} rowKey={r => r.id} />);
    const cells = container.querySelectorAll('tbody td');
    expect(cells[0]?.className).toBe('');
    expect(cells[1]?.className).toBe('eval-swing');
  });
});
