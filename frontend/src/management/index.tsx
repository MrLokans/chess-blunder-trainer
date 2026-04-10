import { render } from 'preact';
import { ManagementApp } from './ManagementApp';

const root = document.getElementById('management-root');
if (root) {
  const demoMode = root.dataset.demoMode === 'true';
  render(<ManagementApp demoMode={demoMode} />, root);
}
