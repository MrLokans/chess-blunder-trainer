import type { ApiErrorResponse } from '../types/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

type QueryParams = Record<string, string | number | boolean | null | undefined | string[]>;

async function request<T = unknown>(url: string, options: RequestInit = {}): Promise<T> {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({})) as ApiErrorResponse;
    throw new ApiError(resp.status, data.detail ?? data.error ?? 'Request failed');
  }
  return resp.json() as Promise<T>;
}

async function requestText(url: string, options: RequestInit = {}): Promise<string> {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({})) as ApiErrorResponse;
    throw new ApiError(resp.status, data.detail ?? data.error ?? 'Request failed');
  }
  return resp.text();
}

function post<T = unknown>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function put<T = unknown>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

function del<T = unknown>(url: string): Promise<T> {
  return request<T>(url, { method: 'DELETE' });
}

function withQuery(url: string, params?: QueryParams): string {
  if (!params) return url;
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue;
    if (Array.isArray(value)) {
      value.forEach(v => searchParams.append(key, v));
    } else {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `${url}?${qs}` : url;
}

export const client = {
  system: {
    engineStatus: () => request('/api/system/engine'),
  },

  stats: {
    overview: (params?: QueryParams) => request(withQuery('/api/stats', params)),
    gameBreakdown: () => request('/api/stats/games'),
    gamesByDate: (params?: QueryParams) => request(withQuery('/api/stats/games/by-date', params)),
    gamesByHour: (params?: QueryParams) => request(withQuery('/api/stats/games/by-hour', params)),
    activityHeatmap: (days = 365) => request(`/api/stats/activity-heatmap?days=${days}`),
    blundersByPhase: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-phase', params)),
    blundersByColor: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-color', params)),
    blundersByGameType: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-game-type', params)),
    blundersByEco: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-eco', params)),
    blundersByTacticalPattern: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-tactical-pattern', params)),
    blundersByDifficulty: (params?: QueryParams) => request(withQuery('/api/stats/blunders/by-difficulty', params)),
    collapsePoint: (params?: QueryParams) => request(withQuery('/api/stats/collapse-point', params)),
    conversionResilience: (params?: QueryParams) => request(withQuery('/api/stats/conversion-resilience', params)),
    growth: (params?: QueryParams) => request(withQuery('/api/stats/growth', params)),
  },

  analysis: {
    status: () => request('/api/analysis/status'),
    start: () => post('/api/analysis/start', {}),
    stop: (jobId: string) => post(`/api/analysis/stop/${jobId}`, {}),
  },

  jobs: {
    startImport: (source: string, username: string, maxGames: number) =>
      post('/api/import/start', { source, username, max_games: maxGames }),
    startSync: () => post('/api/sync/start', {}),
    list: (params?: QueryParams) => request(withQuery('/api/jobs', params)),
    getImportStatus: (jobId: string) => request(`/api/import/status/${jobId}`),
  },

  backfill: {
    phasesPending: () => request('/api/backfill-phases/pending'),
    phasesStatus: () => request('/api/backfill-phases/status'),
    startPhases: () => post('/api/backfill-phases/start', {}),
    ecoPending: () => request('/api/backfill-eco/pending'),
    ecoStatus: () => request('/api/backfill-eco/status'),
    startEco: () => post('/api/backfill-eco/start', {}),
    trapsStatus: () => request('/api/backfill-traps/status'),
    startTraps: () => post('/api/backfill-traps/start', {}),
  },

  data: {
    deleteAll: () => del('/api/data/all'),
    deleteStatus: () => request('/api/data/delete-status'),
  },

  settings: {
    get: () => request('/api/settings'),
    save: (data: unknown) => post('/api/settings', data),
    getUsernames: () => request('/api/settings/usernames'),
    getTheme: () => request('/api/settings/theme'),
    getThemePresets: () => request('/api/settings/theme/presets'),
    getBoard: () => request('/api/settings/board'),
    saveBoard: (data: unknown) => post('/api/settings/board', data),
    getPieceSets: () => request('/api/settings/board/piece-sets'),
    getBoardColorPresets: () => request('/api/settings/board/color-presets'),
    setLocale: (locale: string) => post('/api/settings/locale', { locale }),
    getFeatures: () => request('/api/settings/features'),
    saveFeatures: (features: unknown) => post('/api/settings/features', { features }),
  },

  traps: {
    catalog: () => request('/api/traps/catalog'),
    stats: () => request('/api/traps/stats'),
    detail: (trapId: string) => request(`/api/traps/${trapId}`),
  },

  trainer: {
    getPuzzle: (params?: QueryParams) => request(withQuery('/api/puzzle', params)),
    getSpecificPuzzle: (gameId: string, ply: number) =>
      request(withQuery('/api/puzzle/specific', { game_id: gameId, ply })),
    submitMove: (payload: unknown) => post('/api/submit', payload),
  },

  starred: {
    star: (gameId: string, ply: number, note?: string) =>
      put(`/api/starred/${encodeURIComponent(gameId)}/${ply}`, note ? { note } : {}),
    unstar: (gameId: string, ply: number) =>
      del(`/api/starred/${encodeURIComponent(gameId)}/${ply}`),
    isStarred: (gameId: string, ply: number) =>
      request(`/api/starred/${encodeURIComponent(gameId)}/${ply}`),
    list: (params?: QueryParams) => request(withQuery('/api/starred', params)),
  },

  gameReview: {
    getReview: (gameId: string) => request(`/api/games/${encodeURIComponent(gameId)}/review`),
  },

  debug: {
    gameInfo: (gameId: string, params?: QueryParams) =>
      requestText(withQuery(`/api/games/${encodeURIComponent(gameId)}/debug`, params)),
  },

  setup: {
    complete: (data: unknown) => post('/api/setup', data),
    validateUsername: (platform: string, username: string) =>
      post('/api/validate-username', { platform, username }),
  },
};
