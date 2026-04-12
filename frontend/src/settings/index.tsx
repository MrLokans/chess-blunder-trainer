import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SettingsApp } from './SettingsApp';

const init = window.__settingsInit;
if (!init) {
  console.error('Settings page: missing __settingsInit data');
} else {
  const root = document.getElementById('settings-root');
  if (root) {
    render(<ErrorBoundary><SettingsApp init={init} /></ErrorBoundary>, root);
  }
}
