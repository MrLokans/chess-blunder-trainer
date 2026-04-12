import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { TrapsApp } from './TrapsApp';

const root = document.getElementById('traps-root');
if (root) render(<ErrorBoundary><TrapsApp /></ErrorBoundary>, root);
