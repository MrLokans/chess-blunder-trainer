export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(url, options = {}) {
  const resp = await fetch(url, options);
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new ApiError(resp.status, data.detail || data.error || 'Request failed');
  }
  return resp.json();
}

function post(url, body) {
  return request(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
}

function del(url) {
  return request(url, { method: 'DELETE' });
}

function withQuery(url, params) {
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
    overview: () => request('/api/stats'),
    gameBreakdown: () => request('/api/stats/games'),
    gamesByDate: (params) => request(withQuery('/api/stats/games/by-date', params)),
    gamesByHour: (params) => request(withQuery('/api/stats/games/by-hour', params)),
    activityHeatmap: (days = 365) => request(`/api/stats/activity-heatmap?days=${days}`),
    blundersByPhase: (params) => request(withQuery('/api/stats/blunders/by-phase', params)),
    blundersByColor: (params) => request(withQuery('/api/stats/blunders/by-color', params)),
    blundersByGameType: (params) => request(withQuery('/api/stats/blunders/by-game-type', params)),
    blundersByEco: (params) => request(withQuery('/api/stats/blunders/by-eco', params)),
    blundersByTacticalPattern: (params) => request(withQuery('/api/stats/blunders/by-tactical-pattern', params)),
  },

  analysis: {
    status: () => request('/api/analysis/status'),
    start: () => post('/api/analysis/start', {}),
    stop: (jobId) => post(`/api/analysis/stop/${jobId}`, {}),
  },

  jobs: {
    startImport: (source, username, maxGames) =>
      post('/api/import/start', { source, username, max_games: maxGames }),
    startSync: () => post('/api/sync/start', {}),
  },

  backfill: {
    phasesPending: () => request('/api/backfill-phases/pending'),
    phasesStatus: () => request('/api/backfill-phases/status'),
    startPhases: () => post('/api/backfill-phases/start', {}),
    ecoPending: () => request('/api/backfill-eco/pending'),
    ecoStatus: () => request('/api/backfill-eco/status'),
    startEco: () => post('/api/backfill-eco/start', {}),
  },

  data: {
    deleteAll: () => del('/api/data/all'),
    deleteStatus: () => request('/api/data/delete-status'),
  },

  settings: {
    get: () => request('/api/settings'),
    save: (data) => post('/api/settings', data),
    getUsernames: () => request('/api/settings/usernames'),
    getTheme: () => request('/api/settings/theme'),
    getThemePresets: () => request('/api/settings/theme/presets'),
    getBoard: () => request('/api/settings/board'),
    saveBoard: (data) => post('/api/settings/board', data),
    getPieceSets: () => request('/api/settings/board/piece-sets'),
    getBoardColorPresets: () => request('/api/settings/board/color-presets'),
  },

  trainer: {
    getPuzzle: (params) => request(withQuery('/api/puzzle', params)),
    submitMove: (payload) => post('/api/submit', payload),
  },

  setup: {
    complete: (data) => post('/api/setup', data),
  },
};
