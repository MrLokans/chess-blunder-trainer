import type { ComponentChildren, VNode } from 'preact';
import { Alert } from './Alert';
import type { AsyncDataState } from '../hooks/useAsyncData';

export interface AsyncBoundaryProps<T> {
  state: Pick<AsyncDataState<T>, 'loading' | 'error' | 'data'>;
  children: (data: T) => ComponentChildren;
  empty?: ComponentChildren;
  isEmpty?: (data: T) => boolean;
}

function defaultIsEmpty(data: unknown): boolean {
  return Array.isArray(data) && data.length === 0;
}

export function AsyncBoundary<T>({
  state,
  children,
  empty,
  isEmpty = defaultIsEmpty,
}: AsyncBoundaryProps<T>): VNode | null {
  if (state.loading && state.data === null && state.error === null) {
    return <div class="loading">{t('common.loading')}</div>;
  }

  if (state.error !== null) {
    return <Alert type="error" message={state.error} />;
  }

  if (state.data === null) {
    return <div class="loading">{t('common.loading')}</div>;
  }

  if (empty !== undefined && isEmpty(state.data)) {
    return <>{empty}</>;
  }

  return <>{children(state.data)}</>;
}
