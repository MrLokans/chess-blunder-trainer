import { render } from 'preact';
import { TrapsApp } from './TrapsApp';

const root = document.getElementById('traps-root');
if (root) render(<TrapsApp />, root);
