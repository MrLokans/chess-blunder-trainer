import { render } from 'preact';
import { GameReviewApp } from './GameReviewApp';

function getGameId(): string | null {
  const path = window.location.pathname;
  const match = path.match(/^\/game\/(.+)$/);
  return match ? decodeURIComponent(match[1]!) : null;
}

function getStartPly(): number | null {
  const params = new URLSearchParams(window.location.search);
  const ply = params.get('ply');
  return ply ? parseInt(ply, 10) : null;
}

const root = document.getElementById('game-review-root');
if (root) {
  const gameId = getGameId();
  const startPly = getStartPly();
  render(<GameReviewApp gameId={gameId} startPly={startPly} />, root);
}
