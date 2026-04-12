import { describe, it, expect, vi, beforeEach } from 'vitest';
import { client, ApiError } from '../src/shared/api';

describe('ApiError', () => {
  it('carries status and message', () => {
    const err = new ApiError(404, 'Not found');
    expect(err.status).toBe(404);
    expect(err.message).toBe('Not found');
    expect(err).toBeInstanceOf(Error);
  });
});

describe('query params (via client calls)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('appends query params to URL', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.stats.gamesByDate({ source: 'lichess' });
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const url = (calls[0] as [string])[0];
    expect(url).toContain('source=lichess');
  });

  it('handles array params', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.stats.blundersByPhase({ game_types: ['bullet', 'blitz'] });
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const url = (calls[0] as [string])[0];
    expect(url).toContain('game_types=bullet');
    expect(url).toContain('game_types=blitz');
  });

  it('skips null/undefined params', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.stats.gamesByDate({ source: null, days: '30' });
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const url = (calls[0] as [string])[0];
    expect(url).not.toContain('source');
    expect(url).toContain('days=30');
  });

  it('works with no params', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.stats.overview();
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const url = (calls[0] as [string])[0];
    expect(url).toBe('/api/stats');
  });
});

describe('request error handling', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('throws ApiError on non-ok response with detail', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400, json: () => Promise.resolve({ detail: 'Bad input' }),
    }));
    await expect(client.stats.overview()).rejects.toThrow(ApiError);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400, json: () => Promise.resolve({ detail: 'Bad input' }),
    }));
    try {
      await client.stats.overview();
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      expect((err as ApiError).status).toBe(400);
      expect((err as ApiError).message).toBe('Bad input');
    }
  });

  it('throws ApiError with error field', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500, json: () => Promise.resolve({ error: 'Server broke' }),
    }));
    try {
      await client.stats.overview();
    } catch (err) {
      expect((err as ApiError).message).toBe('Server broke');
    }
  });

  it('handles non-JSON error responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 502, json: () => Promise.reject(new Error('not json')),
    }));
    try {
      await client.stats.overview();
    } catch (err) {
      expect((err as ApiError).status).toBe(502);
      expect((err as ApiError).message).toBe('Request failed');
    }
  });
});

describe('POST requests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends POST with JSON body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.analysis.start();
    expect(fetch).toHaveBeenCalledWith('/api/analysis/start', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }));
  });

  it('sends correct body for startImport', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({ job_id: '123' }),
    }));
    const result = await client.jobs.startImport('lichess', 'bob', 100);
    expect(result).toEqual({ job_id: '123' });
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const call = calls[0] as [string, { body: string }];
    const body: unknown = JSON.parse(call[1].body);
    expect(body).toEqual({ source: 'lichess', username: 'bob', max_games: 100 });
  });
});

describe('DELETE requests', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('sends DELETE method', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, json: () => Promise.resolve({}),
    }));
    await client.data.deleteAll();
    expect(fetch).toHaveBeenCalledWith('/api/data/all', expect.objectContaining({
      method: 'DELETE',
    }));
  });
});

describe('requestText', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('returns text response for debug endpoint', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, text: () => Promise.resolve('debug output'),
    }));
    const result = await client.debug.gameInfo('abc123');
    expect(result).toBe('debug output');
  });
});
