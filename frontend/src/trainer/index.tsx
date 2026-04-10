import { render } from 'preact';
import { TrainerApp } from './TrainerApp';

const root = document.getElementById('trainer-root');
if (root) {
  render(<TrainerApp />, root);
} else {
  console.error('Trainer root element not found');
}
