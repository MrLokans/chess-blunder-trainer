import { render } from 'preact';
import { StarredApp } from './StarredApp';

const root = document.getElementById('starred-root');
if (root) render(<StarredApp />, root);
