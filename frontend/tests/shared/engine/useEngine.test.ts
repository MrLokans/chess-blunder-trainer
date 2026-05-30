import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useEngine } from '../../../src/shared/engine/useEngine';
import type { StockfishEngine, EngineUpdate } from '../../../src/shared/engine/stockfish';

function makeFakeEngine(initImpl: () => Promise<void>) {
  let sub: ((u: EngineUpdate) => void) | null = null;
  const fake = {
    init: vi.fn(initImpl),
    setMultiPV: vi.fn(),
    analyze: vi.fn(),
    stop: vi.fn(),
    dispose: vi.fn(),
    subscribe: vi.fn((cb: (u: EngineUpdate) => void) => {
      sub = cb;
      return () => { sub = null; };
    }),
  };
  const emit = (u: EngineUpdate) => { sub?.(u); };
  return { fake: fake as unknown as StockfishEngine, fakeRaw: fake, emit };
}

const TEST_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';

describe('useEngine', () => {
  it('calls setMultiPV and analyze after init resolves, status becomes ready', async () => {
    const { fake, fakeRaw } = makeFakeEngine(() => Promise.resolve());
    const { result } = renderHook(() =>
      useEngine({ fen: TEST_FEN, multipv: 3, enabled: true, createEngine: () => fake }),
    );

    await act(async () => {});

    expect(fakeRaw.setMultiPV).toHaveBeenCalledWith(3);
    expect(fakeRaw.analyze).toHaveBeenCalledWith(TEST_FEN);
    expect(result.current.status).toBe('ready');
  });

  it('status becomes error when init rejects', async () => {
    const { fake } = makeFakeEngine(() => Promise.reject(new Error('failed to load engine')));
    const { result } = renderHook(() =>
      useEngine({ fen: TEST_FEN, multipv: 1, enabled: true, createEngine: () => fake }),
    );

    await act(async () => {});

    expect(result.current.status).toBe('error');
  });

  it('calls dispose on unmount', async () => {
    const { fake, fakeRaw } = makeFakeEngine(() => Promise.resolve());
    const { unmount } = renderHook(() =>
      useEngine({ fen: TEST_FEN, multipv: 1, enabled: true, createEngine: () => fake }),
    );

    await act(async () => {});
    unmount();

    expect(fakeRaw.dispose).toHaveBeenCalled();
  });

  it('re-analyzes when the fen changes', async () => {
    const { fake, fakeRaw } = makeFakeEngine(() => Promise.resolve());
    const create = () => fake as unknown as StockfishEngine;
    const initialProps = { fen: 'fen1', multipv: 2, enabled: true, createEngine: create };
    const { rerender } = renderHook((p: typeof initialProps) => useEngine(p), { initialProps });
    await act(async () => { await Promise.resolve(); });
    expect(fakeRaw.analyze).toHaveBeenLastCalledWith('fen1');
    rerender({ ...initialProps, fen: 'fen2' });
    await act(async () => { await Promise.resolve(); });
    expect(fakeRaw.analyze).toHaveBeenLastCalledWith('fen2');
  });

  it('exposes subscriber updates as lines and depth', async () => {
    const { fake, emit } = makeFakeEngine(() => Promise.resolve());
    const { result } = renderHook(() =>
      useEngine({ fen: 'f', multipv: 1, enabled: true, createEngine: () => fake as unknown as StockfishEngine }),
    );
    await act(async () => { await Promise.resolve(); });
    void act(() => { emit({ depth: 15, lines: [{ multipv: 1, scoreCp: 42, mate: null, pv: ['e2e4'] }] }); });
    expect(result.current.depth).toBe(15);
    expect(result.current.lines).toHaveLength(1);
  });
});
