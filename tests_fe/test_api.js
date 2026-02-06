import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

// Mock fetch before importing api.js
let fetchCalls = [];
let fetchResponse = { ok: true, status: 200, json: async () => ({}) };

globalThis.fetch = async (url, options) => {
  fetchCalls.push({ url, options });
  return typeof fetchResponse === 'function' ? fetchResponse(url, options) : fetchResponse;
};

const { ApiError, client } = await import('../blunder_tutor/web/static/js/api.js');

describe('ApiError', () => {
  it('carries status and message', () => {
    const err = new ApiError(404, 'Not found');
    assert.equal(err.status, 404);
    assert.equal(err.message, 'Not found');
    assert(err instanceof Error);
  });
});

describe('withQuery (via client calls)', () => {
  beforeEach(() => {
    fetchCalls = [];
    fetchResponse = { ok: true, status: 200, json: async () => ({}) };
  });

  it('appends query params to URL', async () => {
    await client.stats.gamesByDate({ source: 'lichess', username: 'bob' });
    assert.equal(fetchCalls.length, 1);
    const url = fetchCalls[0].url;
    assert(url.includes('source=lichess'));
    assert(url.includes('username=bob'));
  });

  it('handles array params', async () => {
    await client.stats.blundersByPhase({ game_types: ['bullet', 'blitz'] });
    const url = fetchCalls[0].url;
    assert(url.includes('game_types=bullet'));
    assert(url.includes('game_types=blitz'));
  });

  it('skips null/undefined params', async () => {
    await client.stats.gamesByDate({ source: null, username: undefined, days: '30' });
    const url = fetchCalls[0].url;
    assert(!url.includes('source'));
    assert(!url.includes('username'));
    assert(url.includes('days=30'));
  });

  it('works with no params', async () => {
    await client.stats.overview();
    assert.equal(fetchCalls[0].url, '/api/stats');
  });
});

describe('request error handling', () => {
  beforeEach(() => {
    fetchCalls = [];
  });

  it('throws ApiError on non-ok response with detail', async () => {
    fetchResponse = {
      ok: false,
      status: 400,
      json: async () => ({ detail: 'Bad input' }),
    };

    await assert.rejects(
      () => client.stats.overview(),
      (err) => {
        assert(err instanceof ApiError);
        assert.equal(err.status, 400);
        assert.equal(err.message, 'Bad input');
        return true;
      }
    );
  });

  it('throws ApiError with error field', async () => {
    fetchResponse = {
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server broke' }),
    };

    await assert.rejects(
      () => client.stats.overview(),
      (err) => {
        assert.equal(err.message, 'Server broke');
        return true;
      }
    );
  });

  it('handles non-JSON error responses', async () => {
    fetchResponse = {
      ok: false,
      status: 502,
      json: async () => { throw new Error('not json'); },
    };

    await assert.rejects(
      () => client.stats.overview(),
      (err) => {
        assert.equal(err.status, 502);
        assert.equal(err.message, 'Request failed');
        return true;
      }
    );
  });
});

describe('client.jobs.startImport', () => {
  beforeEach(() => {
    fetchCalls = [];
    fetchResponse = { ok: true, status: 200, json: async () => ({ job_id: '123' }) };
  });

  it('sends POST with correct body', async () => {
    const result = await client.jobs.startImport('lichess', 'bob', 100);
    assert.equal(result.job_id, '123');
    const call = fetchCalls[0];
    assert.equal(call.options.method, 'POST');
    const body = JSON.parse(call.options.body);
    assert.deepEqual(body, { source: 'lichess', username: 'bob', max_games: 100 });
  });
});
