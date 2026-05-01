import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { ProfilesApp } from './ProfilesApp';

const root = document.getElementById('profiles-root');
if (root) {
  const demoMode = root.dataset.demoMode === 'true';
  render(
    <ErrorBoundary>
      <ProfilesApp demoMode={demoMode} />
    </ErrorBoundary>,
    root,
  );
}
