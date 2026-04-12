import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { ManagementApp } from './ManagementApp';

const root = document.getElementById('management-root');
if (root) {
  const demoMode = root.dataset.demoMode === 'true';
  render(<ErrorBoundary><ManagementApp demoMode={demoMode} /></ErrorBoundary>, root);
}
