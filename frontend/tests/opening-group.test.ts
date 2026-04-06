import { describe, it, expect } from 'vitest';
import { groupOpeningsByBase, openingNameSlug } from '../src/shared/opening-group';

describe('openingNameSlug', () => {
  it('converts opening name to URL slug', () => {
    expect(openingNameSlug('Sicilian Defense')).toBe('Sicilian-Defense');
  });

  it('handles colons and special characters', () => {
    expect(
      openingNameSlug('Sicilian Defense: Najdorf Variation, English Attack'),
    ).toBe('Sicilian-Defense-Najdorf-Variation-English-Attack');
  });

  it('strips trailing hyphens', () => {
    expect(openingNameSlug('Test!')).toBe('Test');
  });
});

describe('groupOpeningsByBase', () => {
  const makeItem = (eco_code: string, eco_name: string, count: number, avg_cp_loss: number, game_count: number) => ({
    eco_code, eco_name, count, percentage: 0, avg_cp_loss, game_count,
  });

  it('groups variations under the same base opening', () => {
    const items = [
      makeItem('B90', 'Sicilian Defense: Najdorf Variation', 5, 300, 10),
      makeItem('B70', 'Sicilian Defense: Dragon Variation', 3, 200, 8),
      makeItem('C50', 'Italian Game', 2, 250, 5),
    ];

    const groups = groupOpeningsByBase(items);
    expect(groups.length).toBe(2);

    const sicilian = groups.find(g => g.baseName === 'Sicilian Defense');
    expect(sicilian).toBeDefined();
    expect(sicilian!.variations.length).toBe(2);
    expect(sicilian!.totalCount).toBe(8);
    expect(sicilian!.totalGames).toBe(18);

    const italian = groups.find(g => g.baseName === 'Italian Game');
    expect(italian).toBeDefined();
    expect(italian!.variations.length).toBe(1);
    expect(italian!.totalCount).toBe(2);
  });

  it('sorts groups by total blunder count descending', () => {
    const items = [
      makeItem('C50', 'Italian Game', 10, 200, 20),
      makeItem('B90', 'Sicilian Defense: Najdorf', 3, 300, 5),
      makeItem('B70', 'Sicilian Defense: Dragon', 2, 200, 4),
    ];

    const groups = groupOpeningsByBase(items);
    expect(groups[0]!.baseName).toBe('Italian Game');
    expect(groups[1]!.baseName).toBe('Sicilian Defense');
  });

  it('computes weighted average cp loss', () => {
    const items = [
      makeItem('B90', 'Sicilian Defense: Najdorf', 2, 400, 5),
      makeItem('B70', 'Sicilian Defense: Dragon', 3, 200, 8),
    ];

    const groups = groupOpeningsByBase(items);
    const sicilian = groups[0]!;
    // (2*400 + 3*200) / 5 = 1400 / 5 = 280
    expect(sicilian.avgCpLoss).toBe(280);
  });

  it('handles openings without variations (no colon)', () => {
    const items = [
      makeItem('A00', 'Van Geet Opening', 1, 150, 2),
    ];

    const groups = groupOpeningsByBase(items);
    expect(groups.length).toBe(1);
    expect(groups[0]!.baseName).toBe('Van Geet Opening');
    expect(groups[0]!.variations.length).toBe(1);
  });

  it('returns empty array for empty input', () => {
    expect(groupOpeningsByBase([])).toEqual([]);
  });
});
