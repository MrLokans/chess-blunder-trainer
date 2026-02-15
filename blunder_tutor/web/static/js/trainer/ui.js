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
    'statsCard', 'sessionBar',
    'shortcutsOverlay', 'shortcutsClose', 'shortcutsHintBtn',
    'blunderSection',
    'explanationBlunder', 'explanationBest',
    'playFullLine',
    'colorIndicator', 'colorTagText',
    'gameLink', 'gameLinkSeparator',
    'copyDebugBtn', 'starPuzzleBtn',
    'tacticalSeparator',
  ];
  for (const id of ids) {
    els[id] = document.getElementById(id);
  }
  return els;
}

export function getEl(id) {
  return els[id];
}

export function showEmptyState(errorType, onClearFilters) {
  els.trainerLayout.style.display = 'none';
  els.emptyState.style.display = 'block';
  if (els.statsCard) els.statsCard.style.display = 'none';
  if (els.sessionBar) els.sessionBar.style.display = 'none';
  els.emptyStateAction.onclick = null;

  if (errorType === 'no_games') {
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
  els.emptyState.style.display = 'none';
  els.trainerLayout.style.display = 'grid';
  if (els.statsCard) els.statsCard.style.display = 'block';
  if (els.sessionBar) els.sessionBar.style.display = 'flex';
}

export function showBoardResult(accentClass, titleText, detail) {
  els.boardResultCard.className = 'board-result-card visible ' + accentClass;
  els.feedbackTitle.textContent = titleText;
  els.feedbackDetail.textContent = detail;
  els.movePrompt.style.display = 'none';
}

export function hideBoardResult() {
  els.boardResultCard.classList.remove('visible');
  els.movePrompt.style.display = '';
  els.tryBestBtn.style.display = '';
  if (els.tacticalDetails) els.tacticalDetails.removeAttribute('open');
  if (els.explanationDetails) els.explanationDetails.removeAttribute('open');
}

export function toggleBoardResultOverlay() {
  if (els.boardResultCard.classList.contains('visible')) {
    hideBoardResult();
  } else {
    els.boardResultCard.classList.add('visible');
    els.movePrompt.style.display = 'none';
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
    els.phaseBadge.style.display = 'inline-block';
  } else {
    els.phaseBadge.style.display = 'none';
  }
}

export function updateTacticalBadge(pattern) {
  if (!els.tacticalBadge) return;
  if (pattern && pattern !== 'None') {
    els.tacticalPatternName.textContent = pattern;
    els.tacticalBadge.style.display = 'inline-flex';
    if (els.tacticalSeparator) els.tacticalSeparator.style.display = '';
  } else {
    els.tacticalBadge.style.display = 'none';
    if (els.tacticalSeparator) els.tacticalSeparator.style.display = 'none';
  }
}

export function showTacticalInfo(pattern, reason) {
  if (!els.tacticalDetails) return;
  if (pattern && pattern !== 'None' && reason) {
    els.tacticalInfoTitle.textContent = pattern;
    els.tacticalInfoReason.textContent = reason;
    els.tacticalDetails.style.display = '';
  } else {
    els.tacticalDetails.style.display = 'none';
  }
}

export function showExplanation(blunderText, bestText) {
  if (!els.explanationDetails) return;
  if (!blunderText && !bestText) {
    els.explanationDetails.style.display = 'none';
    return;
  }
  els.explanationBlunder.textContent = blunderText || '';
  els.explanationBest.textContent = bestText || '';
  els.explanationDetails.style.display = '';
}

export function updateGameLink(url) {
  if (!els.gameLink) return;
  if (url) {
    els.gameLink.href = url;
    els.gameLink.style.display = 'inline-flex';
    if (els.gameLinkSeparator) els.gameLinkSeparator.style.display = '';
  } else {
    els.gameLink.style.display = 'none';
    if (els.gameLinkSeparator) els.gameLinkSeparator.style.display = 'none';
  }
}

export function updateCopyDebugBtn(gameId, ply) {
  const btn = els.copyDebugBtn;
  if (!btn) return;
  btn.style.display = gameId ? 'inline-block' : 'none';
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
  btn.style.display = gameId ? 'inline-block' : 'none';

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
  els.historySection.style.display = 'none';
  els.moveHistory.textContent = '';
  els.currentMove.textContent = '-';
  els.phaseIndicator.textContent = t('trainer.phase.guess');
  els.phaseIndicator.className = 'phase guess';
  els.submitBtn.disabled = false;
  els.submitBtn.style.display = 'none';
  els.showBestBtn.disabled = false;
  els.highlightLegend.style.display = 'none';
  els.legendBest.style.display = 'none';
  els.legendUser.style.display = 'none';
  els.legendBlunder.style.display = 'flex';
  if (els.legendTactic) els.legendTactic.style.display = 'none';
  updateTacticalBadge(null);
  if (els.tacticalDetails) els.tacticalDetails.style.display = 'none';
  if (els.explanationDetails) els.explanationDetails.style.display = 'none';
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
  els.movePrompt.style.display = 'none';
  els.submitBtn.disabled = true;
  els.submitBtn.style.display = 'none';
  els.phaseIndicator.textContent = t('trainer.phase.explore');
  els.phaseIndicator.className = 'phase explore';
}

export function showCorrectFeedback() {
  showBoardResult('accent-correct', t('trainer.feedback.excellent'), t('trainer.feedback.found_best'));
  els.tryBestBtn.style.display = 'none';
  els.phaseIndicator.textContent = t('trainer.phase.correct');
  els.phaseIndicator.className = 'phase explore';
  els.legendUser.style.display = 'none';
}

export function showBlunderFeedback(userSan) {
  showBoardResult('accent-blunder', t('trainer.feedback.same_blunder'), t('trainer.feedback.same_blunder_detail', { userMove: userSan }));
  els.legendUser.style.display = 'none';
}

export function showNotQuiteFeedback(userSan, userEvalDisplay) {
  showBoardResult('accent-revealed', t('trainer.feedback.not_quite'), t('trainer.feedback.not_quite_detail', { userMove: userSan, userEval: userEvalDisplay }));
  els.legendUser.style.display = 'flex';
}

export function showGoodMoveFeedback(userSan) {
  showBoardResult('accent-correct', t('trainer.feedback.good_move'), t('trainer.feedback.good_move_detail', { userMove: userSan }));
  els.legendUser.style.display = 'flex';
}

export function showLegendBest() {
  els.legendBest.style.display = 'flex';
}

export function showLegendTactic() {
  if (els.legendTactic) els.legendTactic.style.display = 'flex';
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
  els.historySection.style.display = 'block';
}
