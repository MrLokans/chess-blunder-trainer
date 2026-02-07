import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { groupOpeningsByBase, openingNameSlug } from '../blunder_tutor/web/static/js/opening-group.js';

describe('openingNameSlug', () => {
  it('converts opening name to URL slug', () => {
    assert.equal(openingNameSlug('Sicilian Defense'), 'Sicilian-Defense');
  });

  it('handles colons and special characters', () => {
    assert.equal(
      openingNameSlug("Sicilian Defense: Najdorf Variation, English Attack"),
      'Sicilian-Defense-Najdorf-Variation-English-Attack'
    );
  });

  it('strips trailing hyphens', () => {
    assert.equal(openingNameSlug('Test!'), 'Test');
  });
});

describe('groupOpeningsByBase', () => {
  const makeItem = (eco_code, eco_name, count, avg_cp_loss, game_count) => ({
    eco_code, eco_name, count, percentage: 0, avg_cp_loss, game_count,
  });

  it('groups variations under the same base opening', () => {
    const items = [
      makeItem('B90', 'Sicilian Defense: Najdorf Variation', 5, 300, 10),
      makeItem('B70', 'Sicilian Defense: Dragon Variation', 3, 200, 8),
      makeItem('C50', 'Italian Game', 2, 250, 5),
    ];

    const groups = groupOpeningsByBase(items);
    assert.equal(groups.length, 2);

    const sicilian = groups.find(g => g.baseName === 'Sicilian Defense');
    assert.ok(sicilian);
    assert.equal(sicilian.variations.length, 2);
    assert.equal(sicilian.totalCount, 8);
    assert.equal(sicilian.totalGames, 18);

    const italian = groups.find(g => g.baseName === 'Italian Game');
    assert.ok(italian);
    assert.equal(italian.variations.length, 1);
    assert.equal(italian.totalCount, 2);
  });

  it('sorts groups by total blunder count descending', () => {
    const items = [
      makeItem('C50', 'Italian Game', 10, 200, 20),
      makeItem('B90', 'Sicilian Defense: Najdorf', 3, 300, 5),
      makeItem('B70', 'Sicilian Defense: Dragon', 2, 200, 4),
    ];

    const groups = groupOpeningsByBase(items);
    assert.equal(groups[0].baseName, 'Italian Game');
    assert.equal(groups[1].baseName, 'Sicilian Defense');
  });

  it('computes weighted average cp loss', () => {
    const items = [
      makeItem('B90', 'Sicilian Defense: Najdorf', 2, 400, 5),
      makeItem('B70', 'Sicilian Defense: Dragon', 3, 200, 8),
    ];

    const groups = groupOpeningsByBase(items);
    const sicilian = groups[0];
    // (2*400 + 3*200) / 5 = 1400 / 5 = 280
    assert.equal(sicilian.avgCpLoss, 280);
  });

  it('handles openings without variations (no colon)', () => {
    const items = [
      makeItem('A00', 'Van Geet Opening', 1, 150, 2),
    ];

    const groups = groupOpeningsByBase(items);
    assert.equal(groups.length, 1);
    assert.equal(groups[0].baseName, 'Van Geet Opening');
    assert.equal(groups[0].variations.length, 1);
  });

  it('returns empty array for empty input', () => {
    assert.deepEqual(groupOpeningsByBase([]), []);
  });
});
