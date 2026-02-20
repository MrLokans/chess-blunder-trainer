import { client } from '../api.js';

const els = {};

export function initUI() {
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
    'copyDebugBtn', 'starPuzzleBtn',
    'tacticalSeparator',
    'boardResultDragHandle',
  ];
  for (const id of ids) {
    els[id] = document.getElementById(id);
  }
  initDrag();
  return els;
}

export function getEl(id) {
  return els[id];
}

export function showEmptyState(errorType, onClearFilters) {
  els.trainerLayout.classList.add('hidden');
  els.emptyState.classList.remove('hidden');
  if (els.statsCard) els.statsCard.classList.add('hidden');
  els.emptyStateAction.onclick = null;

  if (errorType === 'analyzing') {
    els.emptyStateTitle.textContent = t('trainer.empty.analyzing_title');
    els.emptyStateMessage.textContent = t('trainer.empty.analyzing_message');
    els.emptyStateAction.textContent = t('trainer.empty.analyzing_action');
    els.emptyStateAction.href = '/management';
  } else if (errorType === 'no_games') {
    els.emptyStateTitle.textContent = t('trainer.empty.no_games_title');
    els.emptyStateMessage.textContent = t('trainer.empty.no_games_message');
    els.emptyStateAction.textContent = t('trainer.empty.no_games_action');
    els.emptyStateAction.href = '/management';
  } else if (errorType === 'no_blunders_filtered') {
    els.emptyStateTitle.textContent = t('trainer.empty.no_matching_title');
    els.emptyStateMessage.textContent = t('trainer.empty.no_matching_message');
    els.emptyStateAction.textContent = t('trainer.empty.no_matching_action');
    els.emptyStateAction.href = '#';
    els.emptyStateAction.onclick = (e) => {
      e.preventDefault();
      if (onClearFilters) onClearFilters();
    };
  } else if (errorType === 'no_blunders') {
    els.emptyStateTitle.textContent = t('trainer.empty.no_blunders_title');
    els.emptyStateMessage.textContent = t('trainer.empty.no_blunders_message');
    els.emptyStateAction.textContent = t('trainer.empty.no_blunders_action');
    els.emptyStateAction.href = '/management';
  } else {
    els.emptyStateTitle.textContent = t('trainer.empty.default_title');
    els.emptyStateMessage.textContent = t('trainer.empty.default_message');
    els.emptyStateAction.textContent = t('trainer.empty.default_action');
    els.emptyStateAction.href = '/management';
  }
}

export function hideEmptyState() {
  els.emptyState.classList.add('hidden');
  els.trainerLayout.classList.remove('hidden');
  if (els.statsCard) els.statsCard.classList.remove('hidden');
}

let movePromptOriginalHTML = '';

export function showSubmitting() {
  els.submitBtn.disabled = true;
  els.submitBtn.classList.add('submitting');
  movePromptOriginalHTML = els.movePrompt.innerHTML;
  els.movePrompt.innerHTML = '<div class="submit-spinner"><span class="inline-spinner"></span> ' + t('trainer.feedback.evaluating') + '</div>';
}

export function hideSubmitting() {
  els.submitBtn.disabled = false;
  els.submitBtn.classList.remove('submitting');
  if (movePromptOriginalHTML) {
    els.movePrompt.innerHTML = movePromptOriginalHTML;
    movePromptOriginalHTML = '';
  }
}

export function showBoardResult(accentClass, titleText, detail) {
  els.boardResultCard.className = 'board-result-card visible ' + accentClass;
  els.feedbackTitle.textContent = titleText;
  els.feedbackDetail.textContent = detail;
  els.movePrompt.classList.add('hidden');
  requestAnimationFrame(() => restoreDragPosition());
}

export function hideBoardResult() {
  els.boardResultCard.classList.remove('visible');
  els.boardResultCard.style.left = '';
  els.boardResultCard.style.top = '';
  els.boardResultCard.style.right = '';
  els.boardResultCard.style.bottom = '';
  els.movePrompt.classList.remove('hidden');
  els.tryBestBtn.classList.remove('hidden');
  if (els.tacticalDetails) els.tacticalDetails.removeAttribute('open');
  if (els.explanationDetails) els.explanationDetails.removeAttribute('open');
}

export function toggleBoardResultOverlay() {
  if (els.boardResultCard.classList.contains('visible')) {
    hideBoardResult();
  } else {
    els.boardResultCard.classList.add('visible');
    els.movePrompt.classList.add('hidden');
    requestAnimationFrame(() => restoreDragPosition());
  }
}

export function updateColorBadge(color) {
  if (els.colorBadge) {
    if (color === 'white') {
      els.colorBadge.className = 'color-badge white';
      els.colorBadge.innerHTML = '<span class="color-dot white"></span> ' + t('trainer.color.playing_as_white');
    } else {
      els.colorBadge.className = 'color-badge black';
      els.colorBadge.innerHTML = '<span class="color-dot black"></span> ' + t('trainer.color.playing_as_black');
    }
  }
  if (els.colorIndicator) {
    els.colorIndicator.className = 'color-indicator ' + (color === 'white' ? 'white-piece' : 'black-piece');
  }
  if (els.colorTagText) {
    els.colorTagText.textContent = color === 'white' ? t('chess.color.white') : t('chess.color.black');
  }
}

export function updatePhaseBadge(phase) {
  if (!els.phaseBadge) return;
  if (phase) {
    els.phaseBadge.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
    els.phaseBadge.className = 'context-tag phase-highlight';
    els.phaseBadge.classList.remove('hidden');
  } else {
    els.phaseBadge.classList.add('hidden');
  }
}

export function updateTacticalBadge(pattern) {
  if (!els.tacticalBadge) return;
  if (pattern && pattern !== 'None') {
    els.tacticalPatternName.textContent = pattern;
    els.tacticalBadge.classList.remove('hidden');
    if (els.tacticalSeparator) els.tacticalSeparator.classList.remove('hidden');
  } else {
    els.tacticalBadge.classList.add('hidden');
    if (els.tacticalSeparator) els.tacticalSeparator.classList.add('hidden');
  }
}

export function showTacticalInfo(pattern, reason) {
  if (!els.tacticalDetails) return;
  if (pattern && pattern !== 'None' && reason) {
    els.tacticalInfoTitle.textContent = pattern;
    els.tacticalInfoReason.textContent = reason;
    els.tacticalDetails.classList.remove('hidden');
  } else {
    els.tacticalDetails.classList.add('hidden');
  }
}

export function showExplanation(blunderText, bestText) {
  if (!els.explanationDetails) return;
  if (!blunderText && !bestText) {
    els.explanationDetails.classList.add('hidden');
    return;
  }
  els.explanationBlunder.textContent = blunderText || '';
  els.explanationBest.textContent = bestText || '';
  els.explanationDetails.classList.remove('hidden');
}

export function updateGameLink(url) {
  if (!els.gameLink) return;
  if (url) {
    els.gameLink.href = url;
    els.gameLink.classList.remove('hidden');
    if (els.gameLinkSeparator) els.gameLinkSeparator.classList.remove('hidden');
  } else {
    els.gameLink.classList.add('hidden');
    if (els.gameLinkSeparator) els.gameLinkSeparator.classList.add('hidden');
  }
}

export function updateCopyDebugBtn(gameId, ply) {
  const btn = els.copyDebugBtn;
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

export function updateStarButton(gameId, ply, getCurrentStarred, setCurrentStarred) {
  const btn = els.starPuzzleBtn;
  if (!btn) return;
  btn.classList.toggle('hidden', !gameId);

  async function refreshState() {
    try {
      const resp = await client.starred.isStarred(gameId, ply);
      setCurrentStarred(resp.starred);
      btn.textContent = resp.starred ? '★ ' + t('trainer.star.remove') : '☆ ' + t('trainer.star.add');
      btn.title = resp.starred ? t('trainer.star.remove') : t('trainer.star.add');
    } catch { /* ignore */ }
  }

  btn.onclick = async () => {
    try {
      if (getCurrentStarred()) {
        await client.starred.unstar(gameId, ply);
        setCurrentStarred(false);
        btn.textContent = '☆ ' + t('trainer.star.add');
        btn.title = t('trainer.star.add');
      } else {
        await client.starred.star(gameId, ply);
        setCurrentStarred(true);
        btn.textContent = '★ ' + t('trainer.star.remove');
        btn.title = t('trainer.star.remove');
      }
    } catch (e) {
      console.error('Star toggle failed:', e);
    }
  };

  refreshState();
}

export function updateCurrentMove(game) {
  const history = game.history({ verbose: true });
  const lastMove = history.length > 0 ? history[history.length - 1] : null;
  els.currentMove.textContent = lastMove ? lastMove.san : '-';
}

export function updateMoveHistory(moveHistory) {
  els.moveHistory.textContent = moveHistory.join(' ');
}

export function resetUIForNewPuzzle() {
  hideBoardResult();
  if (els.blunderSection) els.blunderSection.classList.remove('blunder-dimmed');
  els.historySection.classList.add('hidden');
  els.moveHistory.textContent = '';
  els.currentMove.textContent = '-';
  els.phaseIndicator.textContent = t('trainer.phase.guess');
  els.phaseIndicator.className = 'phase guess';
  els.submitBtn.disabled = false;
  els.submitBtn.classList.add('hidden');
  els.showBestBtn.disabled = false;
  els.highlightLegend.classList.add('hidden');
  els.legendBest.classList.add('hidden');
  els.legendUser.classList.add('hidden');
  els.legendBlunder.classList.remove('hidden');
  if (els.legendTactic) els.legendTactic.classList.add('hidden');
  updateTacticalBadge(null);
  if (els.tacticalDetails) els.tacticalDetails.classList.add('hidden');
  if (els.explanationDetails) els.explanationDetails.classList.add('hidden');
}

export function showPuzzleData(puzzle) {
  els.blunderMove.textContent = puzzle.blunder_san;
  els.evalBefore.textContent = puzzle.eval_before_display;
  els.evalAfter.textContent = puzzle.eval_after_display;
  els.cpLoss.textContent = `(${(puzzle.cp_loss / 100).toFixed(1)})`;
  els.bestMoveDisplay.textContent = puzzle.best_move_san || '...';
  els.bestLineDisplay.textContent = puzzle.best_line && puzzle.best_line.length > 1
    ? puzzle.best_line.slice(1).join(' ') : '';
}

export function enterExplorePhase() {
  els.boardResultCard.classList.add('visible', 'best-revealed');
  els.movePrompt.classList.add('hidden');
  requestAnimationFrame(() => restoreDragPosition());
  els.submitBtn.disabled = true;
  els.submitBtn.classList.add('hidden');
  els.phaseIndicator.textContent = t('trainer.phase.explore');
  els.phaseIndicator.className = 'phase explore';
}

export function showCorrectFeedback() {
  showBoardResult('accent-correct', t('trainer.feedback.excellent'), t('trainer.feedback.found_best'));
  els.tryBestBtn.classList.add('hidden');
  els.phaseIndicator.textContent = t('trainer.phase.correct');
  els.phaseIndicator.className = 'phase explore';
  els.legendUser.classList.add('hidden');
}

export function showBlunderFeedback(userSan) {
  showBoardResult('accent-blunder', t('trainer.feedback.same_blunder'), t('trainer.feedback.same_blunder_detail', { userMove: userSan }));
  els.legendUser.classList.add('hidden');
}

export function showNotQuiteFeedback(userSan, userEvalDisplay) {
  showBoardResult('accent-revealed', t('trainer.feedback.not_quite'), t('trainer.feedback.not_quite_detail', { userMove: userSan, userEval: userEvalDisplay }));
  els.legendUser.classList.remove('hidden');
}

export function showGoodMoveFeedback(userSan) {
  showBoardResult('accent-correct', t('trainer.feedback.good_move'), t('trainer.feedback.good_move_detail', { userMove: userSan }));
  els.legendUser.classList.remove('hidden');
}

export function showLegendBest() {
  els.legendBest.classList.remove('hidden');
}

export function showLegendTactic() {
  if (els.legendTactic) els.legendTactic.classList.remove('hidden');
}

export function dimBlunderSection() {
  if (els.blunderSection) els.blunderSection.classList.add('blunder-dimmed');
}

export function toggleShortcutsOverlay() {
  if (!els.shortcutsOverlay) return;
  els.shortcutsOverlay.classList.toggle('visible');
}

export function isShortcutsOverlayVisible() {
  return els.shortcutsOverlay && els.shortcutsOverlay.classList.contains('visible');
}

export function isBoardResultVisible() {
  return els.boardResultCard.classList.contains('visible');
}

export function showHistorySection() {
  els.historySection.classList.remove('hidden');
}

const DRAG_STORAGE_KEY = 'blunder-tutor-result-card-pos';

function initDrag() {
  const card = els.boardResultCard;
  const handle = els.boardResultDragHandle;
  if (!card || !handle) return;

  let dragging = false;
  let startX, startY, startLeft, startTop;

  handle.addEventListener('pointerdown', (e) => {
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

  handle.addEventListener('pointermove', (e) => {
    if (!dragging) return;
    const parent = card.parentElement;
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

  handle.addEventListener('pointerup', (e) => {
    if (!dragging) return;
    dragging = false;
    card.classList.remove('dragging');
    handle.releasePointerCapture(e.pointerId);
    saveDragPosition();
  });
}

function saveDragPosition() {
  const card = els.boardResultCard;
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

export function restoreDragPosition() {
  const card = els.boardResultCard;
  const parent = card.parentElement;
  if (!parent) return;

  const stored = localStorage.getItem(DRAG_STORAGE_KEY);
  if (!stored) return;

  try {
    const pos = JSON.parse(stored);
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
