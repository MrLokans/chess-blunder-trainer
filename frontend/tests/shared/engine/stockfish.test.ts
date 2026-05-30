import { describe, it, expect, vi } from 'vitest';
import { StockfishEngine, type WorkerLike, type EngineUpdate, type FlushScheduler } from '../../../src/shared/engine/stockfish';

// Run the flush synchronously so these tests can assert update delivery inline.
// Production uses the default rAF scheduler; coalescing timing is covered by its
// own test below with a manual scheduler.
const immediate: FlushScheduler = (flush) => { flush(); };

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
    const eng = new StockfishEngine(w, { schedule: immediate });
    const ready = eng.init();
    expect(posted).toContain('uci');
    emit('uciok');
    emit('readyok');
    await ready;
    expect(posted).toContain('isready');
  });

  it('sets multipv, position and go infinite on analyze', () => {
    const { w, posted, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
    emit('uciok'); emit('readyok');
    eng.setMultiPV(3);
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    expect(posted).toContain('setoption name MultiPV value 3');
    expect(posted).toContain('position fen rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    expect(posted).toContain('go infinite');
  });

  it('emits folded lines to subscribers on info', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
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
    const eng = new StockfishEngine(w, { schedule: immediate });
    eng.stop();
    expect(posted).toContain('stop');
    eng.dispose();
    expect(terminate).toHaveBeenCalled();
  });

  it('unsubscribe stops further delivery', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
    const updates: EngineUpdate[] = [];
    const unsub = eng.subscribe(u => updates.push(u));
    emit('info depth 10 multipv 1 score cp 5 pv e2e4');
    unsub();
    emit('info depth 11 multipv 1 score cp 6 pv e2e4');
    expect(updates).toHaveLength(1);
  });

  it('folds multiple multipv lines sorted by index regardless of emission order', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
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
    const eng = new StockfishEngine(w, { schedule: immediate });
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
    const eng = new StockfishEngine(w, { schedule: immediate });
    const ready = eng.init();
    emitError('failed to load engine');
    await expect(ready).rejects.toThrow('failed to load engine');
  });

  it('normalizes black-to-move scores to White POV', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
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
    const eng = new StockfishEngine(w, { schedule: immediate });
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1');
    emit('info depth 20 multipv 1 score mate 2 pv e7e5');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines[0]?.mate).toBe(-2);
  });

  it('defers a second analyze() until bestmove drains the previous search', () => {
    const { w, posted, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
    emit('uciok'); emit('readyok');

    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    const goCountAfterFirst = posted.filter(m => m.startsWith('go')).length;
    expect(goCountAfterFirst).toBe(1);

    // Second analyze while the first is still in flight: must NOT send a new
    // position/go (would race the worker and trap WASM). Should send `stop`
    // and wait.
    eng.analyze('8/8/8/8/8/8/8/8 w - - 0 1');
    expect(posted).toContain('stop');
    expect(posted).not.toContain('position fen 8/8/8/8/8/8/8/8 w - - 0 1');
    expect(posted.filter(m => m.startsWith('go')).length).toBe(1);

    // Engine acknowledges stop — the deferred search begins now.
    emit('bestmove e2e4');
    expect(posted).toContain('position fen 8/8/8/8/8/8/8/8 w - - 0 1');
    expect(posted.filter(m => m.startsWith('go')).length).toBe(2);
  });

  it('discards info lines that arrive between stop and bestmove', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
    emit('uciok'); emit('readyok');
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));

    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 10 multipv 1 score cp 5 pv e2e4');

    // Switch positions; the following info is from the now-aborted search
    // and must be ignored. The cleared state from analyze() is the last
    // legitimate update until the engine catches up.
    eng.analyze('8/8/8/8/8/8/8/8 w - - 0 1');
    const updatesBeforeStaleInfo = updates.length;
    emit('info depth 11 multipv 1 score cp 99 pv h2h4');
    expect(updates).toHaveLength(updatesBeforeStaleInfo);

    // After bestmove, the new search starts; subsequent info is folded in.
    emit('bestmove e2e4');
    emit('info depth 5 multipv 1 score cp -20 pv c2c4');
    const last = updates.at(-1);
    expect(last?.lines).toEqual([
      { multipv: 1, scoreCp: -20, mate: null, pv: ['c2c4'] },
    ]);
  });

  it('does not flip scores for white-to-move positions', () => {
    const { w, emit } = fakeWorker();
    const eng = new StockfishEngine(w, { schedule: immediate });
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));
    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 12 multipv 1 score cp 25 pv e2e4');
    const last = updates.at(-1);
    if (!last) throw new Error('expected an update');
    expect(last.lines[0]?.scoreCp).toBe(25);
  });

  it('coalesces a burst of info lines into a single flush per scheduled frame', () => {
    const { w, emit } = fakeWorker();
    let pending: (() => void) | null = null;
    const schedule: FlushScheduler = (flush) => { pending = flush; };
    const eng = new StockfishEngine(w, { schedule });
    emit('uciok'); emit('readyok');
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));

    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 1 multipv 1 score cp 10 pv e2e4');
    emit('info depth 2 multipv 1 score cp 20 pv e2e4');
    emit('info depth 3 multipv 1 score cp 30 pv e2e4');

    // Nothing is delivered until the scheduled frame runs.
    expect(updates).toHaveLength(0);

    pending?.();

    // The whole burst collapses into one flush carrying the latest state.
    expect(updates).toHaveLength(1);
    expect(updates[0]?.depth).toBe(3);
    expect(updates[0]?.lines[0]?.scoreCp).toBe(30);
  });

  it('does not flush after dispose', () => {
    const { w, emit, terminate } = fakeWorker();
    let pending: (() => void) | null = null;
    const schedule: FlushScheduler = (flush) => { pending = flush; };
    const eng = new StockfishEngine(w, { schedule });
    emit('uciok'); emit('readyok');
    const updates: EngineUpdate[] = [];
    eng.subscribe(u => updates.push(u));

    eng.analyze('rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1');
    emit('info depth 5 multipv 1 score cp 10 pv e2e4');
    eng.dispose();
    pending?.();

    expect(terminate).toHaveBeenCalled();
    expect(updates).toHaveLength(0);
  });
});
