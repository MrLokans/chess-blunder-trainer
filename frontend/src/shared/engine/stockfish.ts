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

const ENGINE_URL = '/static/vendor/stockfish/stockfish-18-lite-single.js';

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
  private _resolveReady: (() => void) | null = null;
  private _rejectReady: ((reason: Error) => void) | null = null;

  constructor(worker: WorkerLike) {
    this._worker = worker;
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
    this._worker.postMessage(`setoption name MultiPV value ${String(n)}`);
  }

  analyze(fen: string): void {
    this._worker.postMessage('stop');
    this._infos.clear();
    this._depth = 0;
    // UCI scores are side-to-move-relative; normalize to White POV on ingestion.
    this._blackToMove = fen.split(' ')[1] === 'b';
    this._worker.postMessage(`position fen ${fen}`);
    this._worker.postMessage('go infinite');
  }

  stop(): void {
    this._worker.postMessage('stop');
  }

  subscribe(cb: Subscriber): () => void {
    this._subs.add(cb);
    return () => this._subs.delete(cb);
  }

  dispose(): void {
    this._subs.clear();
    this._worker.terminate();
  }

  private _onMessage(data: string): void {
    if (data === 'uciok') { this._worker.postMessage('isready'); return; }
    if (data === 'readyok') {
      this._resolveReady?.();
      this._resolveReady = null;
      this._rejectReady = null;
      return;
    }

    const info = parseInfoLine(data);
    if (!info) return;
    this._depth = info.depth;
    this._infos.set(info.multipv, info);
    const rawLines = foldLines(Array.from(this._infos.values()));
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
