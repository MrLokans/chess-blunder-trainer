import { useEffect, useRef, useState } from 'preact/hooks';
import { StockfishEngine, spawnStockfishWorker, type EngineUpdate } from './stockfish';
import type { EngineLine } from './uci';

export type EngineStatus = 'loading' | 'ready' | 'error';

export interface UseEngineProps {
  fen: string;
  multipv: number;
  enabled: boolean;
  createEngine?: () => StockfishEngine;
}

export interface UseEngineResult {
  lines: EngineLine[];
  depth: number;
  status: EngineStatus;
}

function defaultEngine(): StockfishEngine {
  return new StockfishEngine(spawnStockfishWorker());
}

export function useEngine({ fen, multipv, enabled, createEngine }: UseEngineProps): UseEngineResult {
  const engineRef = useRef<StockfishEngine | null>(null);
  // Keep a stable ref to the factory so changing the prop doesn't restart the engine
  // on every render. The factory is only read when enabled transitions true.
  const createEngineRef = useRef(createEngine);
  createEngineRef.current = createEngine;

  const [status, setStatus] = useState<EngineStatus>('loading');
  const [update, setUpdate] = useState<EngineUpdate>({ depth: 0, lines: [] });

  useEffect(() => {
    if (!enabled) return;
    setStatus('loading');
    setUpdate({ depth: 0, lines: [] });
    const engine = (createEngineRef.current ?? defaultEngine)();
    engineRef.current = engine;
    const unsub = engine.subscribe(setUpdate);
    let cancelled = false;
    void engine.init().then(
      () => { if (!cancelled) setStatus('ready'); },
      () => { if (!cancelled) setStatus('error'); },
    );
    return () => {
      cancelled = true;
      unsub();
      engine.dispose();
      engineRef.current = null;
    };
  }, [enabled]);

  useEffect(() => {
    const engine = engineRef.current;
    if (!engine || status !== 'ready') return;
    engine.setMultiPV(multipv);
    engine.analyze(fen);
  }, [fen, multipv, status]);

  return { lines: update.lines, depth: update.depth, status };
}
