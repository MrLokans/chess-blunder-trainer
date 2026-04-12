import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SetupApp } from './SetupApp';
import { ALL_STORAGE_KEYS } from '../shared/storage-keys';

for (const key of ALL_STORAGE_KEYS) {
  localStorage.removeItem(key);
}

const root = document.getElementById('setup-root');
if (root) render(<ErrorBoundary><SetupApp /></ErrorBoundary>, root);
