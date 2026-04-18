import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SignupForm } from './SignupForm';

const root = document.getElementById('auth-root');
if (root) render(<ErrorBoundary><SignupForm /></ErrorBoundary>, root);
