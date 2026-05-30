import { describe, it, expect, vi } from 'vitest';
import { StockfishEngine, type WorkerLike, type EngineUpdate } from '../../../src/shared/engine/stockfish';

function fakeWorker() {
  const posted: string[] = [];
  const terminate = vi.fn();
  const w: WorkerLike = {
    postMessage: (m: string) => { posted.push(m); },
    onmessage: null,
    onerror: null,
    terminate,
  };
  const emit = (data: string) => { w.onmessage?.({ data }); };
  const emitError = (message: string) => { w.onerror?.({ message }); };
  return { w, posted, emit, emitError, terminate };
}

describe('StockfishEngine', () => {
  it('handshakes on init (uci -> uciok -> isready -> readyok)', async () => {
    const { w, posted, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const ready = eng.init();
    expect(posted).toContain('uci');
    emit('uciok');
    emit('readyok');
    await ready;
    expect(posted).toContain('isready');
  });

  it('sets multipv, position and go infinite on analyze', () => {
    const { w, posted, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    emit('uciok'); emit('readyok');
    eng.setMultiPV(3);
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    expect(posted).toContain('setoption name MultiPV value 3');
    expect(posted).toContain('position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    expect(posted).toContain('go infinite');
  });

  it('emits folded lines to subscribers on info', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: unknown[] = [];
    eng.subscribe(u => updates.push(u));
    emit('info depth 12 multipv 1 score cp 30 pv e2e4 e7e5');
    expect(updates.at(-1)).toEqual({
      depth: 12,
      lines: [{ multipv: 1, scoreCp: 30, mate: null, pv: ['e2e4', 'e7e5'] }],
    });
  });

  it('stop sends stop; dispose terminates', () => {
    const { w, posted, terminate } = fakeWorker();
    const eng = new StockfishEngine(w);
    eng.stop();
    expect(posted).toContain('stop');
    eng.dispose();
    expect(terminate).toHaveBeenCalled();
  });

  it('unsubscribe stops further delivery', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    const unsub = eng.subscribe(u => updates.push(u));
    emit('info depth 10 multipv 1 score cp 5 pv e2e4');
    unsub();
    emit('info depth 11 multipv 1 score cp 6 pv e2e4');
    expect(updates).toHaveLength(1);
  });

  it('folds multiple multipv lines sorted by index regardless of emission order', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    emit('info depth 10 multipv 2 score cp 3 pv d2d4');
    emit('info depth 10 multipv 1 score cp 8 pv e2e4');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines.map(l => l.multipv)).toEqual([1, 2]);
    expect(last.lines).toHaveLength(2);
  });

  it('clears stale lines when analyze starts a new position', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    emit('info depth 10 multipv 1 score cp 5 pv e2e4');
    emit('info depth 10 multipv 2 score cp 3 pv d2d4');
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 8 multipv 1 score cp -20 pv a2a3');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines).toEqual([{ multipv: 1, scoreCp: -20, mate: null, pv: ['a2a3'] }]);
  });

  it('init rejects if the worker errors before readyok', async () => {
    const { w, emitError } = fakeWorker();
    const eng = new StockfishEngine(w);
    const ready = eng.init();
    emitError('failed to load engine');
    await expect(ready).rejects.toThrow('failed to load engine');
  });

  it('normalizes black-to-move scores to White POV', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1');
    emit('info depth 12 multipv 1 score cp 40 pv e7e5');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines[0]?.scoreCp).toBe(-40);
  });

  it('normalizes black-to-move mate scores to White POV', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1');
    emit('info depth 20 multipv 1 score mate 2 pv e7e5');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines[0]?.mate).toBe(-2);
  });

  it('does not flip scores for white-to-move positions', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w);
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 12 multipv 1 score cp 25 pv e2e4');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines[0]?.scoreCp).toBe(25);
  });
});
