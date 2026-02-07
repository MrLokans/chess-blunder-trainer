export function groupOpeningsByBase(openings) {
  const groups = new Map();
  for (const item of openings) {
    const colonIdx = item.eco_name.indexOf(': ');
    const baseName = colonIdx > -1 ? item.eco_name.substring(0, colonIdx) : item.eco_name;
    if (!groups.has(baseName)) {
      groups.set(baseName, { baseName, variations: [], totalCount: 0, totalGames: 0, totalCpLossWeighted: 0 });
    }
    const group = groups.get(baseName);
    group.variations.push(item);
    group.totalCount += item.count;
    group.totalGames += item.game_count;
    group.totalCpLossWeighted += item.avg_cp_loss * item.count;
  }
  return Array.from(groups.values())
    .map(g => ({ ...g, avgCpLoss: g.totalCount > 0 ? g.totalCpLossWeighted / g.totalCount : 0 }))
    .sort((a, b) => b.totalCount - a.totalCount);
}

export function openingNameSlug(name) {
  return name.replace(/[^a-zA-Z0-9]+/g, '-').replace(/-+$/, '');
}
