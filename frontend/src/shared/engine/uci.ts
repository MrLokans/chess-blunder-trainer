// frontend/src/shared/engine/uci.ts

export interface ParsedInfo {
  depth: number;
  multipv: number;
  scoreCp: number | null;
  mate: number | null;
  pv: string[];
}

export interface EngineLine {
  multipv: number;
  scoreCp: number | null;
  mate: number | null;
  pv: string[];
}

export interface Arrow {
  from: string;
  to: string;
  color: string;
}

function token(parts: string[], key: string): string | undefined {
  const i = parts.indexOf(key);
  return i >= 0 ? parts[i + 1] : undefined;
}

export function parseInfoLine(line: string): ParsedInfo | null {
  if (!line.startsWith('info ') || !line.includes(' pv ')) return null;
  const parts = line.split(/\s+/);

  const depthStr = token(parts, 'depth');
  if (depthStr === undefined) return null;
  const depth = Number(depthStr);
  if (Number.isNaN(depth)) return null;

  const multipv = Number(token(parts, 'multipv') ?? '1');
  const scoreIdx = parts.indexOf('score');
  if (scoreIdx < 0) return null;

  const scoreKind = parts[scoreIdx + 1];
  const scoreVal = Number(parts[scoreIdx + 2]);
  const scoreCp = scoreKind === 'cp' ? scoreVal : null;
  const mate = scoreKind === 'mate' ? scoreVal : null;

  const pvIdx = parts.indexOf('pv');
  const pv = parts.slice(pvIdx + 1).filter(Boolean);
  if (pv.length === 0) return null;

  return { depth, multipv, scoreCp, mate, pv };
}

export function foldLines(infos: ParsedInfo[]): EngineLine[] {
  const byPv = new Map<number, EngineLine>();
  for (const info of infos) {
    byPv.set(info.multipv, {
      multipv: info.multipv,
      scoreCp: info.scoreCp,
      mate: info.mate,
      pv: info.pv,
    });
  }
  return Array.from(byPv.values()).sort((a, b) => a.multipv - b.multipv);
}

export function uciToArrow(uci: string, color: string): Arrow {
  return { from: uci.slice(0, 2), to: uci.slice(2, 4), color };
}
