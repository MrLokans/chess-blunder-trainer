// frontend/src/shared/engine/uci.test.ts
import { describe, it, expect } from 'vitest';
import { parseInfoLine, foldLines, uciToArrow, type EngineLine } from '../../../src/shared/engine/uci';

describe('parseInfoLine', () => {
  it('parses a cp multipv info line', () => {
    const r = parseInfoLine(
      'info depth 18 multipv 2 score cp -45 pv e2e4 e7e5 g1f3',
    );
    expect(r).toEqual({ depth: 18, multipv: 2, scoreCp: -45, mate: null, pv: ['e2e4', 'e7e5', 'g1f3'] });
  });

  it('parses a mate score', () => {
    const r = parseInfoLine('info depth 20 multipv 1 score mate 3 pv d1h5 g7g6 h5e5');
    expect(r?.mate).toBe(3);
    expect(r?.scoreCp).toBeNull();
  });

  it('returns null for non-info or pv-less lines', () => {
    expect(parseInfoLine('bestmove e2e4')).toBeNull();
    expect(parseInfoLine('info depth 1 seldepth 2 nodes 20')).toBeNull();
  });

  it('parses a verbose line with extra tokens before pv', () => {
    const r = parseInfoLine(
      'info depth 20 seldepth 25 multipv 1 score cp 15 nodes 1234567 nps 850000 hashfull 250 tbhits 0 time 1450 pv e2e4 e7e5',
    );
    expect(r).toEqual({ depth: 20, multipv: 1, scoreCp: 15, mate: null, pv: ['e2e4', 'e7e5'] });
  });

  it('ignores a lowerbound/upperbound modifier after the score', () => {
    const r = parseInfoLine('info depth 22 multipv 1 score cp -300 upperbound pv e2e4');
    expect(r?.scoreCp).toBe(-300);
    expect(r?.pv).toEqual(['e2e4']);
  });
});

describe('foldLines', () => {
  it('keeps the latest line per multipv index, sorted by multipv', () => {
    const a = parseInfoLine('info depth 10 multipv 1 score cp 10 pv e2e4');
    const b = parseInfoLine('info depth 10 multipv 2 score cp 5 pv d2d4');
    const a2 = parseInfoLine('info depth 12 multipv 1 score cp 20 pv e2e4 e7e5');
    if (!a || !b || !a2) throw new Error('parseInfoLine returned null unexpectedly');
    const lines = foldLines([a, b, a2]);
    expect(lines.map((l: EngineLine) => l.multipv)).toEqual([1, 2]);
    const first = lines[0];
    expect(first?.scoreCp).toBe(20);
    expect(first?.pv).toEqual(['e2e4', 'e7e5']);
  });
});

describe('uciToArrow', () => {
  it('splits a uci move into from/to with a brush color', () => {
    expect(uciToArrow('g1f3', 'green')).toEqual({ from: 'g1', to: 'f3', color: 'green' });
  });
  it('handles promotion suffix', () => {
    expect(uciToArrow('e7e8q', 'green')).toEqual({ from: 'e7', to: 'e8', color: 'green' });
  });
});
