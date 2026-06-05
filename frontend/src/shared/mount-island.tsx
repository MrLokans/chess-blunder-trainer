import { render } from 'preact';
import type { ComponentChild } from 'preact';
import { ErrorBoundary } from '../components/feedback/ErrorBoundary';

export function mountIsland(rootId: string, node: ComponentChild): void {
  const root = document.getElementById(rootId);
  if (root) render(<ErrorBoundary>{node}</ErrorBoundary>, root);
}
