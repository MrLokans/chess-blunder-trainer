import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { AsyncBoundary } from '../../src/components/feedback/AsyncBoundary';

describe('AsyncBoundary', () => {
  test('renders canonical loading markup while loading', () => {
    const { container } = render(
      <AsyncBoundary state={{ loading: true, error: null, data: null }}>
        {() => <div>never</div>}
      </AsyncBoundary>,
    );
    const loading = container.querySelector('.loading');
    expect(loading).not.toBeNull();
    expect(loading?.textContent).toBe('common.loading');
  });

  test('renders an error Alert when error is set', () => {
    const { container } = render(
      <AsyncBoundary state={{ loading: false, error: 'boom', data: null }}>
        {() => <div>never</div>}
      </AsyncBoundary>,
    );
    const alert = container.querySelector('.alert-error');
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toBe('boom');
  });

  test('renders the empty slot when data is empty (default predicate)', () => {
    render(
      <AsyncBoundary
        state={{ loading: false, error: null, data: [] }}
        empty={<div>nothing here</div>}
      >
        {() => <div>rows</div>}
      </AsyncBoundary>,
    );
    expect(screen.getByText('nothing here')).toBeTruthy();
  });

  test('renders children when data is present (default predicate)', () => {
    render(
      <AsyncBoundary
        state={{ loading: false, error: null, data: [1, 2] }}
        empty={<div>nothing here</div>}
      >
        {(data) => <div>rows: {data.length}</div>}
      </AsyncBoundary>,
    );
    expect(screen.getByText('rows: 2')).toBeTruthy();
  });

  test('honors a custom isEmpty predicate', () => {
    render(
      <AsyncBoundary
        state={{ loading: false, error: null, data: { count: 0 } }}
        empty={<div>custom empty</div>}
        isEmpty={(d) => d.count === 0}
      >
        {(data) => <div>count: {data.count}</div>}
      </AsyncBoundary>,
    );
    expect(screen.getByText('custom empty')).toBeTruthy();
  });

  test('renders children when no empty slot is provided even for empty data', () => {
    render(
      <AsyncBoundary state={{ loading: false, error: null, data: [] }}>
        {(data) => <div>len: {data.length}</div>}
      </AsyncBoundary>,
    );
    expect(screen.getByText('len: 0')).toBeTruthy();
  });
});
