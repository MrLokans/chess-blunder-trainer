import type {
  ApiErrorResponse, ImportStartResponse, JobStatusResponse, JobStatus,
  PuzzleData, SubmitMovePayload, SubmitMoveResponse,
  ReviewData, StarredItem,
  TrapCatalogEntry, TrapStatsResponse, TrapDetailData,
  SetupPayload,
} from '../types/api';
import type {
  ProfilesListResponse,
  ProfileValidateRequest,
  ProfileValidateResponse,
  ProfileCreateRequest,
  ProfileUpdateRequest,
  ProfileSyncDispatchResponse,
  ProfileStatsRefreshResponse,
  Profile,
} from '../types/profiles';
import type {
  OverviewData,
  AnalysisStatus,
  PhaseData,
  ColorData,
  GameTypeData,
  EcoData,
  TacticalData,
  DifficultyData,
  CollapsePointData,
  ConversionResilienceData,
  GameBreakdownItem,
  DateChartItem,
  HourChartItem,
  GrowthData,
  HeatmapData,
} from '../types/dashboard';
import type {
  SyncSettings,
  ThemeColors,
  ThemePreset,
  PieceSet,
  BoardColorPreset,
  BoardSettings,
  FeatureGroup,
} from '../types/settings';

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
  // 204 No Content and same-class responses have empty bodies; calling
  // .json() on them throws SyntaxError. Return `undefined` cast to T so
  // callers that expect void (logout, delete_account) don't blow up.
  if (resp.status === 204) return undefined as T;
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

function post<T = unknown>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  return request<T>(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  });
}

function put<T = unknown>(url: string, body?: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

export function isAbortError(err: unknown): boolean {
  return err instanceof DOMException && err.name === 'AbortError';
}

function del<T = unknown>(url: string): Promise<T> {
  return request<T>(url, { method: 'DELETE' });
}

function patch<T = unknown>(url: string, body: unknown): Promise<T> {
  return request<T>(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

function withQuery(url: string, params?: QueryParams): string {
  if (!params) return url;
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === null || value === undefined) continue;
    if (Array.isArray(value)) {
      value.forEach(v => { searchParams.append(key, v); });
    } else {
      searchParams.set(key, String(value));
    }
  }
  const qs = searchParams.toString();
  return qs ? `${url}?${qs}` : url;
}

export function requestWithSignal<T = unknown>(url: string, signal: AbortSignal): Promise<T> {
  return request<T>(url, { signal });
}

interface JobStarted {
  job_id: string;
}

interface UsernameValidation {
  valid: boolean;
}

export const client = {
  system: {
    engineStatus: () => request<{ available: boolean; name?: string; path?: string }>('/api/system/engine'),
  },

  stats: {
    overview: (params?: QueryParams) => request<OverviewData>(withQuery('/api/stats', params)),
    gameBreakdown: () => request<{ items: GameBreakdownItem[] }>('/api/stats/games'),
    gamesByDate: (params?: QueryParams) => request<{ items: DateChartItem[] }>(withQuery('/api/stats/games/by-date', params)),
    gamesByHour: (params?: QueryParams) => request<{ items: HourChartItem[] }>(withQuery('/api/stats/games/by-hour', params)),
    activityHeatmap: (days = 365) => request<HeatmapData>(`/api/stats/activity-heatmap?days=${String(days)}`),
    blundersByPhase: (params?: QueryParams) => request<PhaseData>(withQuery('/api/stats/blunders/by-phase', params)),
    blundersByColor: (params?: QueryParams) => request<ColorData>(withQuery('/api/stats/blunders/by-color', params)),
    blundersByGameType: (params?: QueryParams) => request<GameTypeData>(withQuery('/api/stats/blunders/by-game-type', params)),
    blundersByEco: (params?: QueryParams) => request<EcoData>(withQuery('/api/stats/blunders/by-eco', params)),
    blundersByTacticalPattern: (params?: QueryParams) => request<TacticalData>(withQuery('/api/stats/blunders/by-tactical-pattern', params)),
    blundersByDifficulty: (params?: QueryParams) => request<DifficultyData>(withQuery('/api/stats/blunders/by-difficulty', params)),
    collapsePoint: (params?: QueryParams) => request<CollapsePointData>(withQuery('/api/stats/collapse-point', params)),
    conversionResilience: (params?: QueryParams) => request<ConversionResilienceData>(withQuery('/api/stats/conversion-resilience', params)),
    growth: (params?: QueryParams) => request<GrowthData>(withQuery('/api/stats/growth', params)),
  },

  analysis: {
    status: () => request<AnalysisStatus>('/api/analysis/status'),
    start: () => post<JobStarted>('/api/analysis/start', {}),
    stop: (jobId: string) => post(`/api/analysis/stop/${jobId}`, {}),
  },

  jobs: {
    startImport: (source: string, username: string, maxGames: number) =>
      post<JobStarted>('/api/import/start', { source, username, max_games: maxGames }),
    startSync: () => post('/api/sync/start', {}),
    list: (params?: QueryParams) => request(withQuery('/api/jobs', params)),
    getImportStatus: (jobId: string) => request<JobStatusResponse>(`/api/import/status/${jobId}`),
  },

  importPgn: (pgn: string) => post<ImportStartResponse>('/api/import/pgn', { pgn }),

  backfill: {
    phasesPending: () => request('/api/backfill-phases/pending'),
    phasesStatus: () => request<JobStatus>('/api/backfill-phases/status'),
    startPhases: () => post<JobStarted>('/api/backfill-phases/start', {}),
    ecoPending: () => request('/api/backfill-eco/pending'),
    ecoStatus: () => request<JobStatus>('/api/backfill-eco/status'),
    startEco: () => post<JobStarted>('/api/backfill-eco/start', {}),
    startEcoForce: () => post<JobStarted>('/api/backfill-eco/start?force=true', {}),
    trapsStatus: () => request<JobStatus>('/api/backfill-traps/status'),
    startTraps: () => post<JobStarted>('/api/backfill-traps/start', {}),
  },

  data: {
    deleteAll: () => del<JobStarted>('/api/data/all'),
    deleteStatus: () => request<JobStatus>('/api/data/delete-status'),
  },

  settings: {
    get: () => request<SyncSettings>('/api/settings'),
    save: (data: SyncSettings & { theme: ThemeColors }) => post('/api/settings', data),
    getUsernames: () => request<{ lichess_username?: string; chesscom_username?: string }>('/api/settings/usernames'),
    getTheme: () => request<ThemeColors>('/api/settings/theme'),
    getThemePresets: () => request<{ presets: ThemePreset[] }>('/api/settings/theme/presets'),
    getBoard: () => request<BoardSettings>('/api/settings/board'),
    saveBoard: (data: BoardSettings) => post('/api/settings/board', data),
    getPieceSets: () => request<{ piece_sets: PieceSet[] }>('/api/settings/board/piece-sets'),
    getBoardColorPresets: () => request<{ presets: BoardColorPreset[] }>('/api/settings/board/color-presets'),
    setLocale: (locale: string) => post('/api/settings/locale', { locale }),
    getFeatures: () => request<{ groups: FeatureGroup[] }>('/api/settings/features'),
    saveFeatures: (features: Record<string, boolean>) => post('/api/settings/features', { features }),
  },

  traps: {
    catalog: () => request<TrapCatalogEntry[]>('/api/traps/catalog'),
    stats: () => request<TrapStatsResponse>('/api/traps/stats'),
    detail: (trapId: string) => request<TrapDetailData>(`/api/traps/${trapId}`),
  },

  trainer: {
    getPuzzle: (params?: QueryParams) => request<PuzzleData>(withQuery('/api/puzzle', params)),
    getSpecificPuzzle: (gameId: string, ply: number) =>
      request<PuzzleData>(withQuery('/api/puzzle/specific', { game_id: gameId, ply })),
    submitMove: (payload: SubmitMovePayload) => post<SubmitMoveResponse>('/api/submit', payload),
  },

  starred: {
    star: (gameId: string, ply: number, note?: string) =>
      put(`/api/starred/${encodeURIComponent(gameId)}/${String(ply)}`, note ? { note } : {}),
    unstar: (gameId: string, ply: number) =>
      del(`/api/starred/${encodeURIComponent(gameId)}/${String(ply)}`),
    isStarred: (gameId: string, ply: number) =>
      request(`/api/starred/${encodeURIComponent(gameId)}/${String(ply)}`),
    list: (params?: QueryParams) => request<{ items: StarredItem[] }>(withQuery('/api/starred', params)),
  },

  gameReview: {
    getReview: (gameId: string) => request<ReviewData>(`/api/games/${encodeURIComponent(gameId)}/review`),
  },

  debug: {
    gameInfo: (gameId: string, params?: QueryParams) =>
      requestText(withQuery(`/api/games/${encodeURIComponent(gameId)}/debug`, params)),
  },

  setup: {
    complete: (data: SetupPayload) => post<{ import_job_ids?: string[] }>('/api/setup', data),
    validateUsername: (platform: string, username: string) =>
      post<UsernameValidation>('/api/validate-username', { platform, username }),
  },

  auth: {
    login: (username: string, password: string) =>
      post<MeResponse>('/api/auth/login', { username, password }),
    signup: (data: SignupPayload) => post<MeResponse>('/api/auth/signup', data),
    logout: (): Promise<void> => post('/api/auth/logout', {}),
    me: () => request<MeResponse>('/api/auth/me'),
  },

  profiles: {
    list: () => request<ProfilesListResponse>('/api/profiles'),
    create: (data: ProfileCreateRequest) => post<Profile>('/api/profiles', data),
    update: (id: number, data: ProfileUpdateRequest) =>
      patch<Profile>(`/api/profiles/${String(id)}`, data),
    delete: (id: number, detachGames: boolean): Promise<void> =>
      del(`/api/profiles/${String(id)}?detach_games=${String(detachGames)}`),
    validate: (data: ProfileValidateRequest) =>
      post<ProfileValidateResponse>('/api/profiles/validate', data),
    sync: (id: number) =>
      post<ProfileSyncDispatchResponse>(`/api/profiles/${String(id)}/sync`, {}),
    refreshStats: (id: number) =>
      post<ProfileStatsRefreshResponse>(`/api/profiles/${String(id)}/stats/refresh`, {}),
  },
};

export interface MeResponse {
  id: string;
  username: string;
  email?: string | null;
}

export interface SignupPayload {
  username: string;
  password: string;
  email?: string;
  invite_code?: string;
}
