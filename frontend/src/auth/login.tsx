import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { LoginForm } from './LoginForm';

const root = document.getElementById('auth-root');
if (root) render(<ErrorBoundary><LoginForm /></ErrorBoundary>, root);
