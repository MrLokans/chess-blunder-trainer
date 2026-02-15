import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { Chess } from './helpers/chess.js';

globalThis.Chess = Chess;

const { buildThreatHighlights } = await import('../blunder_tutor/web/static/js/trainer/threats.js');

describe('buildThreatHighlights', () => {
  it('returns empty map when showThreats is false', () => {
    const game = new Chess();
    assert.equal(buildThreatHighlights(game, false).size, 0);
  });

  it('returns empty map when game is null', () => {
    assert.equal(buildThreatHighlights(null, true).size, 0);
  });

  it('returns empty map for starting position (no hanging pieces)', () => {
    const game = new Chess();
    const result = buildThreatHighlights(game, true);
    assert.equal(result.size, 0);
  });

  it('detects a hanging piece', () => {
    // White knight on f3, black pawn on e5 attacks it, but knight is defended
    // Instead: put a piece that is attacked but undefended
    // Nb1 moved to c3. Black pawn on d4 attacks c3. c3 knight defended by b1? No, b1 is empty.
    // Simpler: white knight alone on d4, black pawn on e5 — but starting pos makes this hard.
    // Use a custom FEN: white knight on e5, attacked by black pawn on d6, no defenders
    const game = new Chess('rnbqkb1r/ppp2ppp/3p4/4N3/8/8/PPPPPPPP/RNBQKB1R b KQkq - 0 3');
    const result = buildThreatHighlights(game, true);
    // The knight on e5 is attacked by the pawn on d6, check if it has defenders
    // e5 knight is white, attacked by black pawn d6. Is it defended by any white piece?
    // From this FEN the knight has no white piece defending it => hanging
    assert.ok(result.has('e5'), 'Knight on e5 should be flagged as hanging');
    assert.equal(result.get('e5'), 'highlight-hanging');
  });

  it('does not flag defended pieces as hanging', () => {
    // Standard Italian game position: e4 e5 Nf3 — knight on f3 defended by multiple pieces
    const game = new Chess('rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2');
    const result = buildThreatHighlights(game, true);
    // Nf3 is attacked by e5-pawn? No, e5 pawn doesn't attack f3.
    // e4 pawn attacked by e5? pawns don't attack straight ahead.
    // Actually e4 and e5 pawns face each other but neither attacks the other.
    // No hanging pieces in this position
    assert.ok(!result.has('f3'), 'Defended knight should not be flagged');
  });

  it('detects king in check', () => {
    // Re1 attacks e8 (same file, nothing between). Black to move, king in check.
    const game = new Chess('4k3/8/8/8/8/8/8/4RK2 b - - 0 1');
    const result = buildThreatHighlights(game, true);
    assert.ok(result.has('e8'), 'King in check should be highlighted');
    assert.equal(result.get('e8'), 'highlight-king-danger');
  });

  it('detects checkable king (a check is available)', () => {
    // White to move, can give check with a piece
    // White queen on d1, can move to d8 giving check? Or simpler:
    // White rook on a1, black king on a8, white to move — Rook can check on a8? That's capture.
    // White knight on f5, black king on g7? Nf5 to e7 or h6 checks? Not necessarily.
    // Simplest: White queen on h5, black king on e8, Qh5-e8 is check (capture)
    // Let's use: white bishop on c4, can give check on f7 area
    // Actually let's use a trivial case: rook on a2, king on h8, Ra2-a8 checks
    const game = new Chess('7k/8/8/8/8/8/R7/4K3 w - - 0 1');
    // White rook on a2 can play Ra8+ checking the black king on h8
    const result = buildThreatHighlights(game, true);
    assert.ok(result.has('h8'), 'Checkable king should be highlighted');
    assert.equal(result.get('h8'), 'highlight-checking');
  });

  it('does not double-highlight king in check as checkable', () => {
    // King is already in check — should show king-danger, not also checking
    const game = new Chess('4k3/8/8/8/8/8/8/4RK2 b - - 0 1');
    const result = buildThreatHighlights(game, true);
    assert.equal(result.get('e8'), 'highlight-king-danger');
    // Should not have both highlight-king-danger and highlight-checking on e8
    const classes = result.get('e8');
    assert.ok(!classes.includes('highlight-checking'));
  });
});
