import { render } from 'preact';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { TrainerApp } from './TrainerApp';

const root = document.getElementById('trainer-root');
if (root) {
  render(<ErrorBoundary><TrainerApp /></ErrorBoundary>, root);
} else {
  console.error('Trainer root element not found');
}
