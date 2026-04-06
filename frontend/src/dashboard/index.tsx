import { render } from 'preact';
import { DashboardApp } from './DashboardApp';

const root = document.getElementById('dashboard-root');
if (root) {
  render(<DashboardApp />, root);
}
