import { render } from 'preact';
import { SetupApp } from './SetupApp';

const APP_STORAGE_KEYS = [
  'theme',
  'dashboard-date-filter',
  'dashboard-game-type-filters',
  'dashboard-game-phase-filters',
  'blunder-tutor-tactical-filter',
];

for (const key of APP_STORAGE_KEYS) {
  localStorage.removeItem(key);
}

const root = document.getElementById('setup-root');
if (root) render(<SetupApp />, root);
