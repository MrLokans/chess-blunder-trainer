export interface KnownPuzzle {
  gameId: string;
  ply: number;
  blunderSan: string;
  bestMoveSan: string;
  phase: 'opening' | 'middlegame' | 'endgame';
  pattern: string;
  playerColor: 'white' | 'black';
}

export const PUZZLES = {
  forkMiddlegameWhite: {
    gameId: '851d30f9ef24e903c2582fc5ebbb3b20696d14b086f614f476e686a573964810',
    ply: 42,
    blunderSan: 'Qxg5+',
    bestMoveSan: 'Nf3+',
    phase: 'middlegame',
    pattern: 'Fork',
    playerColor: 'white',
  },
  forkMiddlegameBlack: {
    gameId: 'dc6464ff4b48ef8205ccb9c3bbc5fa19644c0aa76478576b0a13dff77bd5e576',
    ply: 51,
    blunderSan: 'Qh4',
    bestMoveSan: 'Nxd5+',
    phase: 'middlegame',
    pattern: 'Fork',
    playerColor: 'black',
  },
  hangingPieceMiddlegame: {
    gameId: 'adf8c48b28fe31229d24330ba60b6be22f5df0673810a5678e6128938f85c011',
    ply: 42,
    blunderSan: 'dxc4',
    bestMoveSan: 'a6',
    phase: 'middlegame',
    pattern: 'Hanging piece',
    playerColor: 'black',
  },
  // Same gameId as openingSimple (different ply) — two blunders from one game
  pinOpening: {
    gameId: '82c510c40d00a317f3c2a9b58323a2fadcb9d65715b58684084fc2d0df6f6fc7',
    ply: 16,
    blunderSan: 'cxd5',
    bestMoveSan: 'Nf6',
    phase: 'opening',
    pattern: 'Pin',
    playerColor: 'white',
  },
  endgameBlunder: {
    gameId: '06520f633e5dacc0dd3ac80f3fb6b87c3943b2a7faf4c043c18de38cd86b88b9',
    ply: 85,
    blunderSan: 'f5',
    bestMoveSan: 'Kh3',
    phase: 'endgame',
    pattern: 'Hanging piece',
    playerColor: 'white',
  },
  // Same gameId as pinOpening (different ply) — two blunders from one game
  openingSimple: {
    gameId: '82c510c40d00a317f3c2a9b58323a2fadcb9d65715b58684084fc2d0df6f6fc7',
    ply: 17,
    blunderSan: 'Nxd5',
    bestMoveSan: 'Bb5+',
    phase: 'opening',
    pattern: 'None',
    playerColor: 'white',
  },
} as const satisfies Record<string, KnownPuzzle>;
