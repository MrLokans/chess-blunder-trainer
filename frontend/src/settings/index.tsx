import { render } from 'preact';
import { SettingsApp } from './SettingsApp';

const init = window.__settingsInit;
if (!init) {
  console.error('Settings page: missing __settingsInit data');
} else {
  const root = document.getElementById('settings-root');
  if (root) {
    render(<SettingsApp init={init} />, root);
  }
}
