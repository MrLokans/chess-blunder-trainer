import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useAnalysisMode } from '../../src/game-review/useAnalysisMode';
import type { StockfishEngine, EngineUpdate } from '../../src/shared/engine/stockfish';
import type { AnalysisBoard } from '../../src/shared/analysis-board';
import { STORAGE_KEYS } from '../../src/shared/storage-keys';
import { loadChessGlobal } from '../helpers/chess';

const START_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

function makeFakeEngine() {
  let sub: ((u: EngineUpdate) => void) | null = null;
  const init = vi.fn(() => Promise.resolve());
  const fake = {
    init,
    setMultiPV: vi.fn(),
    setMaxDepth: vi.fn(),
    analyze: vi.fn(),
    stop: vi.fn(),
    dispose: vi.fn(),
    subscribe: vi.fn((cb: (u: EngineUpdate) => void) => { sub = cb; return () => { sub = null; }; }),
  };
  return {
    create: () => fake as unknown as StockfishEngine,
    raw: fake,
    emit: (u: EngineUpdate) => { sub?.(u); },
  };
}

function makeBoardStub() {
  const stub = {
    setPosition: vi.fn(),
    setShapes: vi.fn(),
    setOrientation: vi.fn(),
    destroy: vi.fn(),
  };
  return { ref: { current: stub as unknown as AnalysisBoard }, stub };
}

function renderAnalysis(createEngine: () => StockfishEngine, currentFen = START_FEN) {
  const board = makeBoardStub();
  const exploreGameRef: { current: ChessInstance | null } = { current: new Chess(currentFen) };
  const view = renderHook(() => useAnalysisMode({
    currentFen,
    boardRef: board.ref,
    exploreGameRef,
    createEngine,
  }));
  return { ...view, board, exploreGameRef };
}

async function flush(): Promise<void> {
  await act(async () => { await Promise.resolve(); });
}

describe('useAnalysisMode', () => {
  beforeEach(() => {
    loadChessGlobal();
    localStorage.clear();
    window.__features = {};
  });

  it('does not enable the engine until analysis mode is toggled on', async () => {
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);

    await flush();
    expect(result.current.analysisMode).toBe(false);
    expect(engine.raw.init).not.toHaveBeenCalled();

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();
    expect(engine.raw.init).toHaveBeenCalled();
    expect(localStorage.getItem(STORAGE_KEYS.reviewAnalysisMode)).toBe('true');
  });

  it('drives the eval bar cp from the first engine line while in analysis mode', async () => {
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);

    expect(result.current.evalCp).toBeNull();

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();
    void act(() => { engine.emit({ depth: 18, lines: [{ multipv: 1, scoreCp: 73, mate: null, pv: ['e2e4'] }] }); });

    expect(result.current.evalCp).toBe(73);
  });

  it('playLine pushes the full pv and repositions the board to the final position', async () => {
    const engine = makeFakeEngine();
    const { result, board, exploreGameRef } = renderAnalysis(engine.create);

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();
    void act(() => { result.current.playLine(['e2e4', 'e7e5']); });

    expect(result.current.exploring).toBe(true);
    expect(result.current.fen).not.toBe(START_FEN);
    // After e4 e5 the explore game should have both moves in its history
    expect(exploreGameRef.current?.history()).toHaveLength(2);
    expect(board.stub.setPosition).toHaveBeenCalled();
  });

  it('handleExploreMove records the latest move played on the explore game', async () => {
    const engine = makeFakeEngine();
    const { result, exploreGameRef } = renderAnalysis(engine.create);

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();
    exploreGameRef.current?.move('e4');
    void act(() => { result.current.handleExploreMove(); });

    expect(result.current.exploring).toBe(true);
  });

  it('backToGame resets exploration to idle and reloads the real fen', async () => {
    const engine = makeFakeEngine();
    const { result, exploreGameRef } = renderAnalysis(engine.create);

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();
    void act(() => { result.current.playLine(['e2e4']); });
    expect(result.current.exploring).toBe(true);

    void act(() => { result.current.backToGame(); });

    expect(result.current.exploring).toBe(false);
    expect(result.current.fen).toBe(START_FEN);
    expect(exploreGameRef.current?.fen()).toBe(START_FEN);
  });

  it('persists multipv and toggle preferences to localStorage', () => {
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);

    void act(() => { result.current.setMultiPv(4); });
    void act(() => { result.current.onToggleArrows(); });
    void act(() => { result.current.onToggleThreats(); });

    expect(localStorage.getItem(STORAGE_KEYS.reviewMultiPv)).toBe('4');
    expect(localStorage.getItem(STORAGE_KEYS.reviewShowArrows)).toBe('false');
    expect(localStorage.getItem(STORAGE_KEYS.reviewShowThreats)).toBe('true');
  });

  it('restores persisted preferences on mount', () => {
    localStorage.setItem(STORAGE_KEYS.reviewMultiPv, '3');
    localStorage.setItem(STORAGE_KEYS.reviewShowArrows, 'false');
    localStorage.setItem(STORAGE_KEYS.reviewShowThreats, 'true');
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);

    expect(result.current.multipv).toBe(3);
    expect(result.current.showArrows).toBe(false);
    expect(result.current.showThreats).toBe(true);
  });

  it('defaults maxDepth to 20 when unset', () => {
    localStorage.removeItem(STORAGE_KEYS.reviewMaxDepth);
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);
    expect(result.current.maxDepth).toBe(20);
  });

  it('loads and clamps maxDepth from storage (5–30)', () => {
    localStorage.setItem(STORAGE_KEYS.reviewMaxDepth, '99');
    const { result } = renderAnalysis(makeFakeEngine().create);
    expect(result.current.maxDepth).toBe(30);
    localStorage.setItem(STORAGE_KEYS.reviewMaxDepth, '1');
    const { result: r2 } = renderAnalysis(makeFakeEngine().create);
    expect(r2.current.maxDepth).toBe(5);
  });

  it('persists maxDepth on setMaxDepth', () => {
    localStorage.removeItem(STORAGE_KEYS.reviewMaxDepth);
    const { result } = renderAnalysis(makeFakeEngine().create);
    void act(() => { result.current.setMaxDepth(15); });
    expect(result.current.maxDepth).toBe(15);
    expect(localStorage.getItem(STORAGE_KEYS.reviewMaxDepth)).toBe('15');
  });

  it('reports the feature as disabled when the flag is off', async () => {
    window.__features = { 'review.engine': false };
    const engine = makeFakeEngine();
    const { result } = renderAnalysis(engine.create);

    void act(() => { result.current.onToggleAnalysis(); });
    await flush();

    expect(result.current.enabled).toBe(false);
    expect(engine.raw.init).not.toHaveBeenCalled();
  });
});
