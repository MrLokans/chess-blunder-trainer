import { parseInfoLine, foldLines, type ParsedInfo, type EngineLine } from './uci';

export interface WorkerLike {
  postMessage(msg: string): void;
  onmessage: ((e: { data: string }) => void) | null;
  onerror: ((e: { message: string }) => void) | null;
  terminate(): void;
}

export interface EngineUpdate {
  depth: number;
  lines: EngineLine[];
}

// Defers a flush; called at most once per pending batch. Default batches to the
// next animation frame so an `info`-line burst collapses into a single render.
export type FlushScheduler = (flush: () => void) => void;

const ENGINE_URL = '/static/vendor/stockfish/stockfish-18-lite-single.js';

const rafScheduler: FlushScheduler = (flush) => {
  if (typeof requestAnimationFrame === 'function') requestAnimationFrame(flush);
  else setTimeout(flush, 16);
};

// Bridges the loosely-typed browser Worker to our narrow WorkerLike contract.
class WorkerBridge implements WorkerLike {
  private _inner: Worker;
  onmessage: ((e: { data: string }) => void) | null = null;
  onerror: ((e: { message: string }) => void) | null = null;

  constructor(inner: Worker) {
    this._inner = inner;
    this._inner.onmessage = (ev: MessageEvent<string>) => {
      this.onmessage?.({ data: ev.data });
    };
    this._inner.onerror = (ev: ErrorEvent) => { this.onerror?.({ message: ev.message }); };
  }

  postMessage(msg: string): void {
    this._inner.postMessage(msg);
  }

  terminate(): void {
    this._inner.terminate();
  }
}

export function spawnStockfishWorker(): WorkerLike {
  return new WorkerBridge(new Worker(ENGINE_URL));
}

type Subscriber = (u: EngineUpdate) => void;

export class StockfishEngine {
  private _worker: WorkerLike;
  private _subs = new Set<Subscriber>();
  private _infos = new Map<number, ParsedInfo>();
  private _depth = 0;
  private _blackToMove = false;
  private _multipv = 1;
  private _searching = false;
  private _pendingFen: string | null = null;
  // True between sending `stop` and receiving `bestmove`: any `info` lines
  // emitted during this window belong to the previous (now-aborted) search
  // and must not be folded into the new search's results.
  private _discardInfo = false;
  private _resolveReady: (() => void) | null = null;
  private _rejectReady: ((reason: Error) => void) | null = null;
  private _schedule: FlushScheduler;
  private _flushQueued = false;
  private _disposed = false;

  constructor(worker: WorkerLike, opts: { schedule?: FlushScheduler } = {}) {
    this._worker = worker;
    this._schedule = opts.schedule ?? rafScheduler;
    this._worker.onmessage = (e) => { this._onMessage(e.data); };
    this._worker.onerror = (e) => { this._onError(e.message); };
  }

  init(): Promise<void> {
    return new Promise((resolve, reject) => {
      this._resolveReady = resolve;
      this._rejectReady = reject;
      this._worker.postMessage('uci');
    });
  }

  setMultiPV(n: number): void {
    this._multipv = n;
  }

  // Sending `position` / `go` while the engine is still searching the previous
  // position races the worker and traps the WASM build with
  // `RuntimeError: unreachable` / `function signature mismatch`. UCI requires
  // waiting for `bestmove` after `stop` before starting a new search — so we
  // queue the request and drain on `bestmove`.
  analyze(fen: string): void {
    this._infos.clear();
    this._depth = 0;
    this._blackToMove = fen.split(' ')[1] === 'b';
    this._pendingFen = fen;
    this._notify();
    if (this._searching) {
      if (!this._discardInfo) {
        this._discardInfo = true;
        this._worker.postMessage('stop');
      }
      return;
    }
    this._beginPendingSearch();
  }

  stop(): void {
    this._worker.postMessage('stop');
  }

  subscribe(cb: Subscriber): () => void {
    this._subs.add(cb);
    return () => this._subs.delete(cb);
  }

  dispose(): void {
    this._disposed = true;
    this._subs.clear();
    this._worker.terminate();
  }

  private _beginPendingSearch(): void {
    if (this._pendingFen === null) return;
    const fen = this._pendingFen;
    this._pendingFen = null;
    this._searching = true;
    this._discardInfo = false;
    this._worker.postMessage(`setoption name MultiPV value ${String(this._multipv)}`);
    this._worker.postMessage(`position fen ${fen}`);
    this._worker.postMessage('go infinite');
  }

  private _onMessage(data: string): void {
    if (data === 'uciok') { this._worker.postMessage('isready'); return; }
    if (data === 'readyok') {
      this._resolveReady?.();
      this._resolveReady = null;
      this._rejectReady = null;
      return;
    }
    if (data.startsWith('bestmove')) {
      this._searching = false;
      this._beginPendingSearch();
      return;
    }
    if (this._discardInfo) return;
    const info = parseInfoLine(data);
    if (!info) return;
    this._depth = info.depth;
    this._infos.set(info.multipv, info);
    this._notify();
  }

  // The worker streams `info` lines hundreds of times a second; notifying
  // subscribers (and thus re-rendering) on each one floods the main thread and
  // starves the compositor. Coalesce to one flush per scheduled frame, reading
  // the latest accumulated state when it runs.
  private _notify(): void {
    if (this._flushQueued || this._disposed) return;
    this._flushQueued = true;
    this._schedule(() => { this._flush(); });
  }

  private _flush(): void {
    this._flushQueued = false;
    if (this._disposed) return;
    const rawLines = foldLines(Array.from(this._infos.values()));
    // UCI scores are side-to-move-relative; normalize to White POV.
    const lines = this._blackToMove
      ? rawLines.map(l => ({
          ...l,
          scoreCp: l.scoreCp === null ? null : -l.scoreCp,
          mate: l.mate === null ? null : -l.mate,
        }))
      : rawLines;
    const update: EngineUpdate = { depth: this._depth, lines };
    for (const sub of this._subs) sub(update);
  }

  private _onError(message: string): void {
    // After readyok, _rejectReady is null; a runtime worker error is currently a no-op (not surfaced).
    this._rejectReady?.(new Error(message));
    this._resolveReady = null;
    this._rejectReady = null;
  }
}
