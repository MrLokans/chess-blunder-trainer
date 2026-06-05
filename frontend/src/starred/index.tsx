import { render } from 'preact';
import { ErrorBoundary } from '../components/feedback/ErrorBoundary';
import { StarredApp } from './StarredApp';

const root = document.getElementById('starred-root');
if (root) render(<ErrorBoundary><StarredApp /></ErrorBoundary>, root);
