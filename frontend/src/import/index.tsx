import { render } from 'preact';
import { ImportApp } from './ImportApp';

const root = document.getElementById('import-root');
if (root) {
  const demoMode = root.dataset.demoMode === 'true';
  render(<ImportApp demoMode={demoMode} />, root);
}
