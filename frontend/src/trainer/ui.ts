import { client } from '../shared/api';
import type { PuzzleData } from './state';

const els: Record<string, HTMLElement | null> = {};

const DRAG_STORAGE_KEY = 'blunder-tutor-result-card-pos';

export function initUI(): Record<string, HTMLElement | null> {
  const ids = [
    'evalBarFill', 'evalValue', 'phaseIndicator', 'colorBadge',
    'blunderMove', 'evalBefore', 'evalAfter', 'cpLoss',
    'boardResultCard', 'feedbackTitle', 'feedbackDetail',
    'movePrompt', 'currentMove', 'bestMoveDisplay', 'bestLineDisplay',
    'tacticalDetails', 'explanationDetails',
    'historySection', 'moveHistory',
    'submitBtn', 'resetBtn', 'showBestBtn', 'nextBtn',
    'tryBestBtn', 'overlayNextBtn', 'undoBtn', 'lichessBtn',
    'highlightLegend', 'legendBlunder', 'legendBest', 'legendUser',
    'showArrows', 'showThreats', 'showTactics', 'legendTactic',
    'phaseBadge', 'tacticalBadge', 'tacticalPatternName',
    'tacticalInfoTitle', 'tacticalInfoReason',
    'emptyState', 'trainerLayout',
    'emptyStateTitle', 'emptyStateMessage', 'emptyStateAction',
    'statsCard',
    'shortcutsOverlay', 'shortcutsClose', 'shortcutsHintBtn',
    'blunderSection',
    'explanationBlunder', 'explanationBest',
    'playFullLine',
    'colorIndicator', 'colorTagText',
    'gameLink', 'gameLinkSeparator',
    'copyDebugBtn', 'starPuzzleBtn', 'reviewGameLink',
    'tacticalSeparator',
    'boardResultDragHandle',
  ];
  for (const id of ids) {
    els[id] = document.getElementById(id);
  }
  initDrag();
  return els;
}

export function getEl(id: string): HTMLElement | null {
  return els[id] ?? null;
}

export function showEmptyState(errorType: string, onClearFilters?: () => void): void {
  const trainerLayout = els['trainerLayout']!;
  const emptyState = els['emptyState']!;
  const emptyStateTitle = els['emptyStateTitle']!;
  const emptyStateMessage = els['emptyStateMessage']!;
  const emptyStateAction = els['emptyStateAction'] as HTMLAnchorElement;
  const statsCard = els['statsCard'];

  trainerLayout.classList.add('hidden');
  emptyState.classList.remove('hidden');
  if (statsCard) statsCard.classList.add('hidden');
  emptyStateAction.onclick = null;

  if (errorType === 'analyzing') {
    emptyStateTitle.textContent = t('trainer.empty.analyzing_title');
    emptyStateMessage.textContent = t('trainer.empty.analyzing_message');
    emptyStateAction.textContent = t('trainer.empty.analyzing_action');
    emptyStateAction.href = '/management';
  } else if (errorType === 'no_games') {
    emptyStateTitle.textContent = t('trainer.empty.no_games_title');
    emptyStateMessage.textContent = t('trainer.empty.no_games_message');
    emptyStateAction.textContent = t('trainer.empty.no_games_action');
    emptyStateAction.href = '/management';
  } else if (errorType === 'no_blunders_filtered') {
    emptyStateTitle.textContent = t('trainer.empty.no_matching_title');
    emptyStateMessage.textContent = t('trainer.empty.no_matching_message');
    emptyStateAction.textContent = t('trainer.empty.no_matching_action');
    emptyStateAction.href = '#';
    emptyStateAction.onclick = (e) => {
      e.preventDefault();
      if (onClearFilters) onClearFilters();
    };
  } else if (errorType === 'no_blunders') {
    emptyStateTitle.textContent = t('trainer.empty.no_blunders_title');
    emptyStateMessage.textContent = t('trainer.empty.no_blunders_message');
    emptyStateAction.textContent = t('trainer.empty.no_blunders_action');
    emptyStateAction.href = '/management';
  } else {
    emptyStateTitle.textContent = t('trainer.empty.default_title');
    emptyStateMessage.textContent = t('trainer.empty.default_message');
    emptyStateAction.textContent = t('trainer.empty.default_action');
    emptyStateAction.href = '/management';
  }
}

export function hideEmptyState(): void {
  els['emptyState']!.classList.add('hidden');
  els['trainerLayout']!.classList.remove('hidden');
  if (els['statsCard']) els['statsCard'].classList.remove('hidden');
}

let movePromptOriginalHTML = '';

export function showSubmitting(): void {
  const submitBtn = els['submitBtn'] as HTMLButtonElement;
  const movePrompt = els['movePrompt']!;
  submitBtn.disabled = true;
  submitBtn.classList.add('submitting');
  movePromptOriginalHTML = movePrompt.innerHTML;
  movePrompt.innerHTML = '<div class="submit-spinner"><span class="inline-spinner"></span> ' + t('trainer.feedback.evaluating') + '</div>';
}

export function hideSubmitting(): void {
  const submitBtn = els['submitBtn'] as HTMLButtonElement;
  const movePrompt = els['movePrompt']!;
  submitBtn.disabled = false;
  submitBtn.classList.remove('submitting');
  if (movePromptOriginalHTML) {
    movePrompt.innerHTML = movePromptOriginalHTML;
    movePromptOriginalHTML = '';
  }
}

export function showBoardResult(accentClass: string, titleText: string, detail: string): void {
  const card = els['boardResultCard']!;
  card.className = 'board-result-card visible ' + accentClass;
  els['feedbackTitle']!.textContent = titleText;
  els['feedbackDetail']!.textContent = detail;
  els['movePrompt']!.classList.add('hidden');
  requestAnimationFrame(() => restoreDragPosition());
}

export function hideBoardResult(): void {
  const card = els['boardResultCard']!;
  card.classList.remove('visible');
  card.style.left = '';
  card.style.top = '';
  card.style.right = '';
  card.style.bottom = '';
  els['movePrompt']!.classList.remove('hidden');
  els['tryBestBtn']!.classList.remove('hidden');
  const tacticalDetails = els['tacticalDetails'] as HTMLDetailsElement | null;
  const explanationDetails = els['explanationDetails'] as HTMLDetailsElement | null;
  if (tacticalDetails) tacticalDetails.removeAttribute('open');
  if (explanationDetails) explanationDetails.removeAttribute('open');
}

export function toggleBoardResultOverlay(): void {
  const card = els['boardResultCard']!;
  if (card.classList.contains('visible')) {
    hideBoardResult();
  } else {
    card.classList.add('visible');
    els['movePrompt']!.classList.add('hidden');
    requestAnimationFrame(() => restoreDragPosition());
  }
}

export function updateColorBadge(color: string): void {
  const colorBadge = els['colorBadge'];
  if (colorBadge) {
    if (color === 'white') {
      colorBadge.className = 'color-badge white';
      colorBadge.innerHTML = '<span class="color-dot white"></span> ' + t('trainer.color.playing_as_white');
    } else {
      colorBadge.className = 'color-badge black';
      colorBadge.innerHTML = '<span class="color-dot black"></span> ' + t('trainer.color.playing_as_black');
    }
  }
  const colorIndicator = els['colorIndicator'];
  if (colorIndicator) {
    colorIndicator.className = 'color-indicator ' + (color === 'white' ? 'white-piece' : 'black-piece');
  }
  const colorTagText = els['colorTagText'];
  if (colorTagText) {
    colorTagText.textContent = color === 'white' ? t('chess.color.white') : t('chess.color.black');
  }
}

export function updatePhaseBadge(phase: string | null): void {
  const phaseBadge = els['phaseBadge'];
  if (!phaseBadge) return;
  if (phase) {
    phaseBadge.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
    phaseBadge.className = 'context-tag phase-highlight';
    phaseBadge.classList.remove('hidden');
  } else {
    phaseBadge.classList.add('hidden');
  }
}

export function updateTacticalBadge(pattern: string | null): void {
  const tacticalBadge = els['tacticalBadge'];
  if (!tacticalBadge) return;
  if (pattern && pattern !== 'None') {
    els['tacticalPatternName']!.textContent = pattern;
    tacticalBadge.classList.remove('hidden');
    if (els['tacticalSeparator']) els['tacticalSeparator'].classList.remove('hidden');
  } else {
    tacticalBadge.classList.add('hidden');
    if (els['tacticalSeparator']) els['tacticalSeparator'].classList.add('hidden');
  }
}

export function showTacticalInfo(pattern: string | null, reason: string | null): void {
  const tacticalDetails = els['tacticalDetails'];
  if (!tacticalDetails) return;
  if (pattern && pattern !== 'None' && reason) {
    els['tacticalInfoTitle']!.textContent = pattern;
    els['tacticalInfoReason']!.textContent = reason;
    tacticalDetails.classList.remove('hidden');
  } else {
    tacticalDetails.classList.add('hidden');
  }
}

export function showExplanation(blunderText: string | null, bestText: string | null): void {
  const explanationDetails = els['explanationDetails'];
  if (!explanationDetails) return;
  if (!blunderText && !bestText) {
    explanationDetails.classList.add('hidden');
    return;
  }
  els['explanationBlunder']!.textContent = blunderText || '';
  els['explanationBest']!.textContent = bestText || '';
  explanationDetails.classList.remove('hidden');
}

export function updateGameLink(url: string | null): void {
  const gameLink = els['gameLink'] as HTMLAnchorElement | null;
  if (!gameLink) return;
  if (url) {
    gameLink.href = url;
    gameLink.classList.remove('hidden');
    if (els['gameLinkSeparator']) els['gameLinkSeparator'].classList.remove('hidden');
  } else {
    gameLink.classList.add('hidden');
    if (els['gameLinkSeparator']) els['gameLinkSeparator'].classList.add('hidden');
  }
}

export function updateCopyDebugBtn(gameId: string, ply: number): void {
  const btn = els['copyDebugBtn'];
  if (!btn) return;
  btn.classList.toggle('hidden', !gameId);
  btn.onclick = async () => {
    try {
      const params = ply != null ? { ply } : {};
      const text = await client.debug.gameInfo(gameId, params);
      await navigator.clipboard.writeText(text);
      const original = btn.textContent;
      btn.textContent = '✅ ' + t('trainer.debug.copied');
      setTimeout(() => { btn.textContent = original; }, 1500);
    } catch (e) {
      console.error('Copy debug failed:', e);
    }
  };
}

export function updateReviewGameLink(gameId: string, ply: number): void {
  const link = els['reviewGameLink'] as HTMLAnchorElement | null;
  if (!link) return;
  if (gameId) {
    const url = `/game/${encodeURIComponent(gameId)}` + (ply != null ? `?ply=${ply}` : '');
    link.href = url;
    link.classList.remove('hidden');
  } else {
    link.classList.add('hidden');
  }
}

export function updateStarButton(
  gameId: string,
  ply: number,
  getCurrentStarred: () => boolean,
  setCurrentStarred: (v: boolean) => void,
): void {
  const btn = els['starPuzzleBtn'];
  if (!btn) return;
  btn.classList.toggle('hidden', !gameId);

  async function refreshState(): Promise<void> {
    try {
      const resp = await client.starred.isStarred(gameId, ply) as { starred: boolean };
      setCurrentStarred(resp.starred);
      btn!.textContent = resp.starred ? '★ ' + t('trainer.star.remove') : '☆ ' + t('trainer.star.add');
      btn!.title = resp.starred ? t('trainer.star.remove') : t('trainer.star.add');
    } catch { /* ignore */ }
  }

  btn.onclick = async () => {
    try {
      if (getCurrentStarred()) {
        await client.starred.unstar(gameId, ply);
        setCurrentStarred(false);
        btn!.textContent = '☆ ' + t('trainer.star.add');
        btn!.title = t('trainer.star.add');
      } else {
        await client.starred.star(gameId, ply);
        setCurrentStarred(true);
        btn!.textContent = '★ ' + t('trainer.star.remove');
        btn!.title = t('trainer.star.remove');
      }
    } catch (e) {
      console.error('Star toggle failed:', e);
    }
  };

  refreshState();
}

export function updateCurrentMove(game: ChessInstance): void {
  const history = game.history({ verbose: true });
  const lastMove = history.length > 0 ? history[history.length - 1] : undefined;
  els['currentMove']!.textContent = lastMove ? lastMove.san : '-';
}

export function updateMoveHistory(moveHistory: string[]): void {
  els['moveHistory']!.textContent = moveHistory.join(' ');
}

export function resetUIForNewPuzzle(): void {
  hideBoardResult();
  const blunderSection = els['blunderSection'];
  if (blunderSection) blunderSection.classList.remove('blunder-dimmed');
  els['historySection']!.classList.add('hidden');
  els['moveHistory']!.textContent = '';
  els['currentMove']!.textContent = '-';
  els['phaseIndicator']!.textContent = t('trainer.phase.guess');
  els['phaseIndicator']!.className = 'phase guess';
  (els['submitBtn'] as HTMLButtonElement).disabled = false;
  els['submitBtn']!.classList.add('hidden');
  (els['showBestBtn'] as HTMLButtonElement).disabled = false;
  els['highlightLegend']!.classList.add('hidden');
  els['legendBest']!.classList.add('hidden');
  els['legendUser']!.classList.add('hidden');
  els['legendBlunder']!.classList.remove('hidden');
  if (els['legendTactic']) els['legendTactic'].classList.add('hidden');
  updateTacticalBadge(null);
  if (els['tacticalDetails']) els['tacticalDetails'].classList.add('hidden');
  if (els['explanationDetails']) els['explanationDetails'].classList.add('hidden');
}

export function showPuzzleData(puzzle: PuzzleData): void {
  els['blunderMove']!.textContent = puzzle.blunder_san;
  els['evalBefore']!.textContent = puzzle.eval_before_display;
  els['evalAfter']!.textContent = puzzle.eval_after_display;
  els['cpLoss']!.textContent = `(${(puzzle.cp_loss / 100).toFixed(1)})`;
  els['bestMoveDisplay']!.textContent = puzzle.best_move_san || '...';
  els['bestLineDisplay']!.textContent = puzzle.best_line && puzzle.best_line.length > 1
    ? puzzle.best_line.slice(1).join(' ') : '';
}

export function enterExplorePhase(): void {
  const card = els['boardResultCard']!;
  card.classList.add('visible', 'best-revealed');
  els['movePrompt']!.classList.add('hidden');
  requestAnimationFrame(() => restoreDragPosition());
  (els['submitBtn'] as HTMLButtonElement).disabled = true;
  els['submitBtn']!.classList.add('hidden');
  els['phaseIndicator']!.textContent = t('trainer.phase.explore');
  els['phaseIndicator']!.className = 'phase explore';
}

export function showCorrectFeedback(): void {
  showBoardResult('accent-correct', t('trainer.feedback.excellent'), t('trainer.feedback.found_best'));
  els['tryBestBtn']!.classList.add('hidden');
  els['phaseIndicator']!.textContent = t('trainer.phase.correct');
  els['phaseIndicator']!.className = 'phase explore';
  els['legendUser']!.classList.add('hidden');
}

export function showBlunderFeedback(userSan: string): void {
  showBoardResult('accent-blunder', t('trainer.feedback.same_blunder'), t('trainer.feedback.same_blunder_detail', { userMove: userSan }));
  els['legendUser']!.classList.add('hidden');
}

export function showNotQuiteFeedback(userSan: string, userEvalDisplay: string): void {
  showBoardResult('accent-revealed', t('trainer.feedback.not_quite'), t('trainer.feedback.not_quite_detail', { userMove: userSan, userEval: userEvalDisplay }));
  els['legendUser']!.classList.remove('hidden');
}

export function showGoodMoveFeedback(userSan: string): void {
  showBoardResult('accent-correct', t('trainer.feedback.good_move'), t('trainer.feedback.good_move_detail', { userMove: userSan }));
  els['legendUser']!.classList.remove('hidden');
}

export function showLegendBest(): void {
  els['legendBest']!.classList.remove('hidden');
}

export function showLegendTactic(): void {
  if (els['legendTactic']) els['legendTactic'].classList.remove('hidden');
}

export function dimBlunderSection(): void {
  const blunderSection = els['blunderSection'];
  if (blunderSection) blunderSection.classList.add('blunder-dimmed');
}

export function toggleShortcutsOverlay(): void {
  const overlay = els['shortcutsOverlay'];
  if (!overlay) return;
  overlay.classList.toggle('visible');
}

export function isShortcutsOverlayVisible(): boolean {
  const overlay = els['shortcutsOverlay'];
  return overlay !== null && overlay !== undefined && overlay.classList.contains('visible');
}

export function isBoardResultVisible(): boolean {
  return els['boardResultCard']!.classList.contains('visible');
}

export function showHistorySection(): void {
  els['historySection']!.classList.remove('hidden');
}

function initDrag(): void {
  const card = els['boardResultCard'];
  const handle = els['boardResultDragHandle'];
  if (!card || !handle) return;

  let dragging = false;
  let startX = 0;
  let startY = 0;
  let startLeft = 0;
  let startTop = 0;

  handle.addEventListener('pointerdown', (e: PointerEvent) => {
    e.preventDefault();
    dragging = true;
    card.classList.add('dragging');

    const rect = card.getBoundingClientRect();
    startX = e.clientX;
    startY = e.clientY;
    startLeft = rect.left;
    startTop = rect.top;

    handle.setPointerCapture(e.pointerId);
  });

  handle.addEventListener('pointermove', (e: PointerEvent) => {
    if (!dragging) return;
    const parent = card.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();

    let newLeft = startLeft + (e.clientX - startX) - parentRect.left;
    let newTop = startTop + (e.clientY - startY) - parentRect.top;

    newLeft = Math.max(0, Math.min(newLeft, parentRect.width - card.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, parentRect.height - card.offsetHeight));

    card.style.left = newLeft + 'px';
    card.style.top = newTop + 'px';
    card.style.right = 'auto';
    card.style.bottom = 'auto';
  });

  handle.addEventListener('pointerup', (e: PointerEvent) => {
    if (!dragging) return;
    dragging = false;
    card.classList.remove('dragging');
    handle.releasePointerCapture(e.pointerId);
    saveDragPosition();
  });
}

function saveDragPosition(): void {
  const card = els['boardResultCard'];
  if (!card) return;
  const parent = card.parentElement;
  if (!parent) return;
  const parentRect = parent.getBoundingClientRect();
  const cardRect = card.getBoundingClientRect();

  const pos = {
    leftPct: (cardRect.left - parentRect.left) / parentRect.width,
    topPct: (cardRect.top - parentRect.top) / parentRect.height,
  };
  localStorage.setItem(DRAG_STORAGE_KEY, JSON.stringify(pos));
}

export function restoreDragPosition(): void {
  const card = els['boardResultCard'];
  if (!card) return;
  const parent = card.parentElement;
  if (!parent) return;

  const stored = localStorage.getItem(DRAG_STORAGE_KEY);
  if (!stored) return;

  try {
    const pos = JSON.parse(stored) as { leftPct: number; topPct: number };
    const parentRect = parent.getBoundingClientRect();

    let left = pos.leftPct * parentRect.width;
    let top = pos.topPct * parentRect.height;

    left = Math.max(0, Math.min(left, parentRect.width - card.offsetWidth));
    top = Math.max(0, Math.min(top, parentRect.height - card.offsetHeight));

    card.style.left = left + 'px';
    card.style.top = top + 'px';
    card.style.right = 'auto';
    card.style.bottom = 'auto';
  } catch { /* ignore corrupt data */ }
}
