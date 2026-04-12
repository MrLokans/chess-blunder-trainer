import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { ImportApp } from './ImportApp';

const root = document.getElementById('import-root');
if (root) {
  const demoMode = root.dataset.demoMode === 'true';
  render(<ErrorBoundary><ImportApp demoMode={demoMode} /></ErrorBoundary>, root);
}
