import { render } from 'preact';
import { ErrorBoundary } from '../components/feedback/ErrorBoundary';
import { DashboardApp } from './DashboardApp';

const root = document.getElementById('dashboard-root');
if (root) {
  render(<ErrorBoundary><DashboardApp /></ErrorBoundary>, root);
}
