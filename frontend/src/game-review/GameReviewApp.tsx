import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
import { client } from '../shared/api';
import { MoveSequence, ReadOnlyBoard, PlaybackController } from '../shared/sequence-player';
import { applyBoardBackground, applyPieceSet } from '../shared/board-theme';
import { updateEvalBar } from '../trainer/eval-bar';
import { EvalChart, evalFromWhite } from './eval-chart';

interface ReviewMove {
  san: string;
  move_number: number;
  player: string;
  ply: number;
  eval_after: number;
  classification?: string;
}

interface ReviewGame {
  username?: string;
  white: string;
  black: string;
  result?: string;
  game_url?: string;
}

interface ReviewData {
  moves: ReviewMove[];
  game: ReviewGame;
  analyzed: boolean;
}

interface BoardSettings {
  board_light: string;
  board_dark: string;
  piece_set?: string;
}

interface MovePair {
  white: (ReviewMove & { index: number }) | null;
  black: (ReviewMove & { index: number }) | null;
}

function deriveOutcome(result: string, playerColor: string): string {
  if (result === '1/2-1/2') return t('game_review.result.draw');
  const whiteWon = result === '1-0';
  const playerWon = (playerColor === 'white') === whiteWon;
  return playerWon ? t('game_review.result.win') : t('game_review.result.loss');
}

function buildMovePairs(moves: ReviewMove[]): Map<number, MovePair> {
  const pairs = new Map<number, MovePair>();
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i]!;
    const num = m.move_number;
    if (!pairs.has(num)) {
      pairs.set(num, { white: null, black: null });
    }
    const entry = pairs.get(num)!;
    if (m.player === 'white') {
      entry.white = { ...m, index: i };
    } else {
      entry.black = { ...m, index: i };
    }
  }
  return pairs;
}

interface MoveCellProps {
  moveInfo: (ReviewMove & { index: number }) | null;
  activeIndex: number;
  onSelect: (index: number) => void;
}

function MoveCell({ moveInfo, activeIndex, onSelect }: MoveCellProps) {
  if (!moveInfo) return <span class="review-move-cell" />;

  const isActive = moveInfo.index === activeIndex;
  const cls = 'review-move-cell' + (isActive ? ' active' : '');

  return (
    <span
      class={cls}
      data-index={moveInfo.index}
      onClick={() => onSelect(moveInfo.index)}
    >
      {moveInfo.classification && moveInfo.classification !== 'normal' && (
        <span class={`review-move-dot ${moveInfo.classification}`} />
      )}
      {moveInfo.san}
    </span>
  );
}

interface MoveListProps {
  moves: ReviewMove[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function MoveList({ moves, activeIndex, onSelect }: MoveListProps) {
  const activeRef = useRef<HTMLSpanElement>(null);
  const pairs = buildMovePairs(moves);

  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }, [activeIndex]);

  return (
    <div class="review-move-list" id="reviewMoveList">
      {Array.from(pairs.entries()).map(([num, pair]) => (
        <div key={num} class="review-move-row">
          <span class="review-move-num">{num}.</span>
          <MoveCell moveInfo={pair.white} activeIndex={activeIndex} onSelect={onSelect} />
          <MoveCell moveInfo={pair.black} activeIndex={activeIndex} onSelect={onSelect} />
        </div>
      ))}
    </div>
  );
}

interface EvalChartProps {
  moves: ReviewMove[];
  activeIndex: number;
  onSelect: (index: number) => void;
}

function EvalChartCanvas({ moves, activeIndex, onSelect }: EvalChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<EvalChart | null>(null);

  useEffect(() => {
    if (!canvasRef.current) return;
    chartRef.current = new EvalChart(canvasRef.current);
    chartRef.current.render(moves);
    chartRef.current.onClick(onSelect);
    return () => {
      chartRef.current = null;
    };
  }, [moves, onSelect]);

  useEffect(() => {
    chartRef.current?.setActivePly(activeIndex);
  }, [activeIndex]);

  return <canvas ref={canvasRef} id="reviewEvalChart" />;
}

interface EvalBarProps {
  moves: ReviewMove[];
  activeIndex: number;
}

function EvalBar({ moves, activeIndex }: EvalBarProps) {
  const fillRef = useRef<HTMLDivElement>(null);
  const valueRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!fillRef.current || !valueRef.current) return;
    if (moves.length > 0 && activeIndex >= 0 && activeIndex < moves.length) {
      const move = moves[activeIndex]!;
      updateEvalBar(evalFromWhite(move), 'white', fillRef.current, valueRef.current);
    } else {
      updateEvalBar(0, 'white', fillRef.current, valueRef.current);
    }
  }, [moves, activeIndex]);

  return (
    <div class="eval-bar-container" id="reviewEvalBarContainer">
      <div class="eval-value" ref={valueRef} id="reviewEvalValue">0.0</div>
      <div class="eval-bar" id="reviewEvalBar">
        <div class="eval-bar-fill" ref={fillRef} id="reviewEvalBarFill" style="height: 50%" />
      </div>
    </div>
  );
}

interface GameReviewAppProps {
  gameId: string | null;
  startPly?: number | null;
}

export function GameReviewApp({ gameId, startPly }: GameReviewAppProps) {
  const [data, setData] = useState<ReviewData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [orientation, setOrientation] = useState<'white' | 'black'>('white');
  const [activeIndex, setActiveIndex] = useState(-1);
  const [isPlaying, setIsPlaying] = useState(false);

  const sequenceRef = useRef<MoveSequence | null>(null);
  const boardRef = useRef<ReadOnlyBoard | null>(null);
  const playbackRef = useRef<PlaybackController | null>(null);
  const initializedRef = useRef(false);

  const goToIndex = useCallback((index: number) => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    pb.pause();
    setIsPlaying(false);
    seq.goTo(index);
    board.setPosition(seq.fen, seq.lastMove);
    setActiveIndex(seq.currentIndex);
  }, []);

  const goFirst = useCallback(() => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    pb.pause();
    setIsPlaying(false);
    seq.goToStart();
    board.setPosition(seq.fen, null);
    setActiveIndex(seq.currentIndex);
  }, []);

  const goPrev = useCallback(() => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    pb.pause();
    setIsPlaying(false);
    const result = seq.stepBack();
    if (result) board.setPosition(seq.fen, result.lastMove);
    setActiveIndex(seq.currentIndex);
  }, []);

  const goNext = useCallback(() => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    pb.pause();
    setIsPlaying(false);
    const result = seq.stepForward();
    if (result) board.setPosition(result.fen, result.lastMove);
    setActiveIndex(seq.currentIndex);
  }, []);

  const goLast = useCallback(() => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    pb.pause();
    setIsPlaying(false);
    seq.goToEnd();
    board.setPosition(seq.fen, seq.lastMove);
    setActiveIndex(seq.currentIndex);
  }, []);

  const togglePlayPause = useCallback(() => {
    const seq = sequenceRef.current;
    const board = boardRef.current;
    const pb = playbackRef.current;
    if (!seq || !board || !pb) return;
    if (seq.isAtEnd) {
      seq.goToStart();
      board.setPosition(seq.fen, null);
      setActiveIndex(seq.currentIndex);
    }
    pb.toggle();
    setIsPlaying(pb.isPlaying);
  }, []);

  const flipBoard = useCallback(() => {
    setOrientation(prev => {
      const next = prev === 'white' ? 'black' : 'white';
      boardRef.current?.setOrientation(next);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!gameId) {
      setError(t('game_review.not_found'));
      return;
    }

    Promise.all([
      client.gameReview.getReview<ReviewData>(gameId),
      client.settings.getBoard().catch(() => null),
    ]).then(([reviewData, boardSettings]) => {
      let orient: 'white' | 'black' = 'white';
      if (reviewData.game.username) {
        const uname = reviewData.game.username.toLowerCase();
        if (reviewData.game.black.toLowerCase() === uname) {
          orient = 'black';
        }
      }
      setOrientation(orient);

      if (boardSettings) {
        const root = document.documentElement;
        root.style.setProperty('--board-light', boardSettings.board_light);
        root.style.setProperty('--board-dark', boardSettings.board_dark);
        applyBoardBackground(boardSettings.board_light, boardSettings.board_dark);
        applyPieceSet(boardSettings.piece_set || 'gioco');
      }

      setData(reviewData);
    }).catch((err: unknown) => {
      const isNotFound = typeof err === 'object' && err !== null && 'status' in err && (err as { status: unknown }).status === 404;
      if (isNotFound) {
        setError(t('game_review.not_found'));
      } else {
        setError(t('common.error'));
        console.error('Failed to load game review:', err);
      }
    });
  }, [gameId]);

  useEffect(() => {
    if (!data || initializedRef.current) return;
    const boardEl = document.getElementById('reviewBoard');
    if (!boardEl) return;
    initializedRef.current = true;

    const sanMoves = data.moves.map(m => m.san);
    const seq = new MoveSequence(sanMoves);
    sequenceRef.current = seq;

    const board = new ReadOnlyBoard(boardEl, {
      orientation,
      fen: seq.fen,
    });
    boardRef.current = board;

    const pb = new PlaybackController({
      speed: 1000,
      onTick: () => {
        if (seq.isAtEnd) {
          pb.pause();
          setIsPlaying(false);
          return;
        }
        const result = seq.stepForward();
        if (result) board.setPosition(result.fen, result.lastMove);
        setActiveIndex(seq.currentIndex);
      },
    });
    playbackRef.current = pb;

    if (startPly != null) {
      const moveIndex = data.moves.findIndex(m => m.ply === startPly);
      if (moveIndex >= 0) {
        seq.goTo(moveIndex);
        board.setPosition(seq.fen, seq.lastMove);
        setActiveIndex(seq.currentIndex);
        return;
      }
    }

    setActiveIndex(seq.currentIndex);

    return () => {
      pb.destroy();
      board.destroy();
      sequenceRef.current = null;
      boardRef.current = null;
      playbackRef.current = null;
      initializedRef.current = false;
    };
  }, [data]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;
      switch (e.key) {
        case 'ArrowLeft':  e.preventDefault(); goPrev(); break;
        case 'ArrowRight': e.preventDefault(); goNext(); break;
        case 'Home':       e.preventDefault(); goFirst(); break;
        case 'End':        e.preventDefault(); goLast(); break;
        case 'f': case 'F': flipBoard(); break;
        case ' ':          e.preventDefault(); togglePlayPause(); break;
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [goPrev, goNext, goFirst, goLast, flipBoard, togglePlayPause]);

  if (error) {
    return (
      <div class="review-page" id="reviewPage">
        <div class="review-error" id="reviewError">
          <p id="reviewErrorMessage">{error}</p>
          <a href="/" class="btn btn-primary">{t('common.back_to_trainer')}</a>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div class="review-page" id="reviewPage">
        <div class="review-loading" id="reviewLoading">
          <p>{t('common.loading')}</p>
        </div>
      </div>
    );
  }

  const { game, moves, analyzed } = data;
  const playerColor = orientation;
  const atStart = activeIndex < 0;
  const atEnd = activeIndex >= moves.length - 1;

  return (
    <div class="review-page" id="reviewPage">
      <div class="review-content" id="reviewContent">
        <div class="review-main">
          <div class="review-board-area">
            <div class="context-tags">
              <span class="context-tag" id="reviewColorTag">
                <span class={`color-indicator ${playerColor}-piece`} id="reviewColorIndicator" />
                <span id="reviewColorText">
                  {playerColor === 'black' ? t('chess.color.black') : t('chess.color.white')}
                </span>
              </span>
              {game.result && (
                <>
                  <span class="context-tag-separator" id="reviewResultSep">·</span>
                  <span class="context-tag phase-highlight" id="reviewResultBadge">
                    {deriveOutcome(game.result, playerColor)}
                  </span>
                </>
              )}
              {game.game_url && (
                <>
                  <span class="context-tag-separator" id="reviewLinkSep">·</span>
                  <a
                    id="reviewSourceLink"
                    href={game.game_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    class="context-tag-link"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                      <polyline points="15 3 21 3 21 9" />
                      <line x1="10" y1="14" x2="21" y2="3" />
                    </svg>
                    {t('trainer.link.original_game')}
                  </a>
                </>
              )}
            </div>

            <div class="board-eval-wrapper">
              {analyzed && <EvalBar moves={moves} activeIndex={activeIndex} />}
              <div class="review-board" id="reviewBoardWrapper">
                <div class="cg-wrap-board" id="reviewBoard" />
              </div>
            </div>

            {analyzed && (
              <div class="review-eval-chart" id="reviewEvalChartContainer">
                <EvalChartCanvas moves={moves} activeIndex={activeIndex} onSelect={goToIndex} />
              </div>
            )}
          </div>

          <div class="review-panel">
            {!analyzed && (
              <div class="review-not-analyzed" id="reviewNotAnalyzed">
                {t('game_review.no_analysis')}
              </div>
            )}

            <MoveList moves={moves} activeIndex={activeIndex} onSelect={goToIndex} />

            <div class="review-controls">
              <button
                class="review-nav-btn"
                id="reviewFirst"
                title={t('game_review.controls.first')}
                disabled={atStart}
                onClick={goFirst}
              >&#x23EE;</button>
              <button
                class="review-nav-btn"
                id="reviewPrev"
                title={t('game_review.controls.prev')}
                disabled={atStart}
                onClick={goPrev}
              >&#x25C0;</button>
              <button
                class="review-nav-btn"
                id="reviewPlayPause"
                title={isPlaying ? t('game_review.controls.pause') : t('game_review.controls.play')}
                onClick={togglePlayPause}
              >
                {isPlaying ? '\u23F8' : '\u25B6'}
              </button>
              <button
                class="review-nav-btn"
                id="reviewNext"
                title={t('game_review.controls.next')}
                disabled={atEnd}
                onClick={goNext}
              >&#x25B6;</button>
              <button
                class="review-nav-btn"
                id="reviewLast"
                title={t('game_review.controls.last')}
                disabled={atEnd}
                onClick={goLast}
              >&#x23ED;</button>
              <button
                class="review-nav-btn"
                id="reviewFlip"
                title={t('game_review.flip_board')}
                onClick={flipBoard}
              >&#x21C5;</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
