import { useCallback, useEffect, useMemo, useState } from 'preact/hooks';
import { useEngine } from '../shared/engine/useEngine';
import type { StockfishEngine } from '../shared/engine/stockfish';
import type { EngineLine } from '../shared/engine/uci';
import { uciToArrow } from '../shared/engine/uci';
import { buildThreatHighlights } from '../shared/threats';
import { STORAGE_KEYS } from '../shared/storage-keys';
import { hasFeature } from '../shared/features';
import type { AnalysisBoard } from '../shared/analysis-board';
import { IDLE, begin, push, pop } from './exploration';

const MATE_CP = 10000;

interface ChessgroundShape {
  orig: string;
  dest?: string;
  brush?: string;
}

export interface UseAnalysisModeParams {
  currentFen: string;
  boardRef: { current: AnalysisBoard | null };
  exploreGameRef: { current: ChessInstance | null };
  createEngine?: () => StockfishEngine;
}

export interface UseAnalysisModeResult {
  enabled: boolean;
  analysisMode: boolean;
  multipv: number;
  showArrows: boolean;
  showThreats: boolean;
  exploring: boolean;
  fen: string;
  lines: EngineLine[];
  depth: number;
  status: 'loading' | 'ready' | 'error';
  evalCp: number | null;
  onToggleAnalysis: () => void;
  setMultiPv: (n: number) => void;
  onToggleArrows: () => void;
  onToggleThreats: () => void;
  handleExploreMove: () => void;
  backToGame: () => void;
  takeback: () => void;
  playLine: (uciMoves: string[]) => void;
  resetExploration: (toFen?: string) => void;
}

function loadBool(key: string, fallback: boolean): boolean {
  const raw = localStorage.getItem(key);
  if (raw === null) return fallback;
  return raw === 'true';
}

function loadMultiPv(): number {
  const raw = localStorage.getItem(STORAGE_KEYS.reviewMultiPv);
  if (raw === null) return 3;
  const n = Number(raw);
  if (Number.isNaN(n) || n < 1 || n > 5) return 3;
  return Math.trunc(n);
}

function lineEvalCp(line: EngineLine | undefined): number | null {
  if (!line) return null;
  if (line.mate !== null) return line.mate > 0 ? MATE_CP : -MATE_CP;
  return line.scoreCp;
}

export function useAnalysisMode(params: UseAnalysisModeParams): UseAnalysisModeResult {
  const { currentFen, boardRef, exploreGameRef, createEngine } = params;
  const enabled = hasFeature('review.engine');

  const [analysisMode, setAnalysisMode] = useState(() => enabled && loadBool(STORAGE_KEYS.reviewAnalysisMode, false));
  const [multipv, setMultipvState] = useState(loadMultiPv);
  const [showArrows, setShowArrows] = useState(() => loadBool(STORAGE_KEYS.reviewShowArrows, true));
  const [showThreats, setShowThreats] = useState(() => loadBool(STORAGE_KEYS.reviewShowThreats, false));
  const [exploration, setExploration] = useState(IDLE);

  const exploring = exploration.active && exploration.sans.length > 0;
  const fen = exploring ? exploration.fen : currentFen;

  const { lines, depth, status } = useEngine({
    fen,
    multipv,
    enabled: enabled && analysisMode && fen !== '',
    createEngine,
  });

  const evalCp = analysisMode ? lineEvalCp(lines[0]) : null;

  const resetExploration = useCallback((toFen?: string) => {
    const target = toFen ?? currentFen;
    setExploration(IDLE);
    const game = exploreGameRef.current;
    if (game) game.load(target);
  }, [currentFen, exploreGameRef]);

  const onToggleAnalysis = useCallback(() => {
    setAnalysisMode(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEYS.reviewAnalysisMode, String(next));
      if (!next) setExploration(IDLE);
      return next;
    });
  }, []);

  const setMultiPv = useCallback((n: number) => {
    setMultipvState(n);
    localStorage.setItem(STORAGE_KEYS.reviewMultiPv, String(n));
  }, []);

  const onToggleArrows = useCallback(() => {
    setShowArrows(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEYS.reviewShowArrows, String(next));
      return next;
    });
  }, []);

  const onToggleThreats = useCallback(() => {
    setShowThreats(prev => {
      const next = !prev;
      localStorage.setItem(STORAGE_KEYS.reviewShowThreats, String(next));
      return next;
    });
  }, []);

  const handleExploreMove = useCallback(() => {
    const game = exploreGameRef.current;
    if (!game) return;
    const hist = game.history({ verbose: true });
    const last = hist[hist.length - 1];
    if (!last) return;
    setExploration(prev => {
      const base = prev.active ? prev : begin(currentFen);
      return push(base, game.fen(), last.san);
    });
  }, [currentFen, exploreGameRef]);

  const backToGame = useCallback(() => {
    resetExploration();
    boardRef.current?.setPosition(new Chess(currentFen), null);
  }, [resetExploration, currentFen, boardRef]);

  const takeback = useCallback(() => {
    const game = exploreGameRef.current;
    if (!game) return;
    if (exploration.sans.length <= 1) {
      resetExploration();
      boardRef.current?.setPosition(new Chess(currentFen), null);
      return;
    }
    game.undo();
    const hist = game.history({ verbose: true });
    const last = hist[hist.length - 1];
    setExploration(prev => pop(prev, game.fen()));
    boardRef.current?.setPosition(game, last ? [last.from, last.to] : null);
  }, [exploration.sans.length, resetExploration, currentFen, boardRef, exploreGameRef]);

  const playLine = useCallback((uciMoves: string[]) => {
    const game = exploreGameRef.current;
    if (!game || uciMoves.length === 0) return;
    game.load(currentFen);
    let state = begin(currentFen);
    let lastMove: { from: string; to: string } | null = null;
    for (const uci of uciMoves) {
      const move = game.move({ from: uci.slice(0, 2), to: uci.slice(2, 4), promotion: uci.slice(4) || 'q' });
      if (!move) break;
      state = push(state, game.fen(), move.san);
      lastMove = { from: move.from, to: move.to };
    }
    if (state.sans.length === 0) return;
    setExploration(state);
    boardRef.current?.setPosition(game, lastMove ? [lastMove.from, lastMove.to] : null);
  }, [currentFen, boardRef, exploreGameRef]);

  // Depend on the best-move string, not the whole `lines` array: `lines` gets a
  // new identity on every engine tick (depth/score changes), but the arrow and
  // threat shapes only change when the best move or position changes. Keying on
  // the primitive avoids re-running `new Chess(fen)` + buildThreatHighlights on
  // every tick.
  const bestMove = lines[0]?.pv[0] ?? null;
  const shapes = useMemo((): ChessgroundShape[] => {
    if (!analysisMode) return [];
    const out: ChessgroundShape[] = [];
    if (showArrows && bestMove) {
      const turn = fen.split(' ')[1] === 'b' ? 'black' : 'white';
      const arrow = uciToArrow(bestMove, turn);
      out.push({ orig: arrow.from, dest: arrow.to, brush: 'green' });
    }
    if (showThreats) {
      const game = new Chess(fen);
      const highlights = buildThreatHighlights(game, true);
      for (const [square, brush] of highlights) out.push({ orig: square, brush });
    }
    return out;
  }, [analysisMode, bestMove, showArrows, showThreats, fen]);

  useEffect(() => {
    if (!analysisMode) return;
    boardRef.current?.setShapes(shapes);
  }, [analysisMode, shapes, boardRef]);

  return {
    enabled,
    analysisMode,
    multipv,
    showArrows,
    showThreats,
    exploring,
    fen,
    lines,
    depth,
    status,
    evalCp,
    onToggleAnalysis,
    setMultiPv,
    onToggleArrows,
    onToggleThreats,
    handleExploreMove,
    backToGame,
    takeback,
    playLine,
    resetExploration,
  };
}
