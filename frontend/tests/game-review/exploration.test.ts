import { describe, it, expect } from 'vitest';
import { IDLE, begin, push, pop, type ExplorationState } from '../../src/game-review/exploration';

describe('exploration reducer', () => {
  it('begins from a base fen', () => {
    const s = begin('FEN0');
    expect(s).toEqual({ active: true, baseFen: 'FEN0', fen: 'FEN0', sans: [] });
  });

  it('pushes explored moves', () => {
    let s = begin('FEN0');
    s = push(s, 'FEN1', 'e4');
    s = push(s, 'FEN2', 'e5');
    expect(s.fen).toBe('FEN2');
    expect(s.sans).toEqual(['e4', 'e5']);
  });

  it('pops the last move, staying active at the base when emptied', () => {
    let s = begin('FEN0');
    s = push(s, 'FEN1', 'e4');
    s = pop(s, 'FEN0');
    expect(s).toEqual({ active: true, baseFen: 'FEN0', fen: 'FEN0', sans: [] });
  });

  it('pop on an empty line is a no-op', () => {
    const s: ExplorationState = begin('FEN0');
    expect(pop(s, 'FEN0')).toEqual(s);
  });

  it('IDLE is inactive', () => {
    expect(IDLE.active).toBe(false);
  });

  it('preserves baseFen across multiple pushes', () => {
    let s = begin('FEN0');
    s = push(s, 'FEN1', 'e4');
    s = push(s, 'FEN2', 'e5');
    expect(s.baseFen).toBe('FEN0');
  });
});
