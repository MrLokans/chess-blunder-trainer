import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createElement, resetDOM, setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

const { JobCard } = await import('../blunder_tutor/web/static/js/job-card.js');

describe('JobCard', () => {
  let messages;

  beforeEach(() => {
    resetDOM();
    messages = [];
    createElement('progress');
    createElement('fill');
    createElement('text');
    createElement('startBtn');
    createElement('stopBtn');
    createElement('pending');
  });

  function makeCard(overrides = {}) {
    return new JobCard({
      progressContainerId: 'progress',
      fillId: 'fill',
      textId: 'text',
      startBtnId: 'startBtn',
      stopBtnId: 'stopBtn',
      messageId: 'msg',
      showMessage: (id, type, txt) => messages.push({ id, type, txt }),
      fetchStatus: async () => ({ status: 'idle' }),
      startJob: async () => ({ job_id: 'job-1' }),
      startedMessage: 'Started!',
      completedMessage: 'Done!',
      failedPrefix: 'Failed: ',
      ...overrides,
    });
  }

  it('start() sets jobId and shows success message', async () => {
    const card = makeCard();
    await card.start();
    assert.equal(card.jobId, 'job-1');
    assert.equal(messages[0].type, 'success');
    assert.equal(messages[0].txt, 'Started!');
  });

  it('start() shows error on failure', async () => {
    const card = makeCard({
      startJob: async () => { throw new Error('engine down'); },
    });
    await card.start();
    assert.equal(card.jobId, null);
    assert.equal(messages[0].type, 'error');
    assert(messages[0].txt.includes('engine down'));
  });

  it('handleProgress returns false for unknown job', async () => {
    const card = makeCard();
    await card.start();
    assert.equal(card.handleProgress({ job_id: 'other', current: 1, total: 10, percent: 10 }), false);
  });

  it('handleProgress returns true and updates for matching job', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleProgress({ job_id: 'job-1', current: 5, total: 10, percent: 50 });
    assert.equal(result, true);
  });

  it('handleStatusChange completed resets jobId', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleStatusChange({ job_id: 'job-1', status: 'completed' });
    assert.equal(result, true);
    assert.equal(card.jobId, null);
    assert.equal(messages[1].type, 'success');
    assert.equal(messages[1].txt, 'Done!');
  });

  it('handleStatusChange failed shows error', async () => {
    const card = makeCard();
    await card.start();
    card.handleStatusChange({ job_id: 'job-1', status: 'failed', error_message: 'timeout' });
    assert.equal(card.jobId, null);
    assert.equal(messages[1].type, 'error');
    assert(messages[1].txt.includes('timeout'));
  });

  it('handleStatusChange ignores unknown job', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleStatusChange({ job_id: 'other', status: 'completed' });
    assert.equal(result, false);
    assert.equal(card.jobId, 'job-1');
  });

  it('onComplete callback fires on completion', async () => {
    let completed = false;
    const card = makeCard({ onComplete: () => { completed = true; } });
    await card.start();
    card.handleStatusChange({ job_id: 'job-1', status: 'completed' });
    assert.equal(completed, true);
  });

  it('loadStatus shows progress for running job', async () => {
    const card = makeCard({
      fetchStatus: async () => ({
        status: 'running',
        job_id: 'job-2',
        progress_current: 3,
        progress_total: 10,
      }),
    });
    await card.loadStatus();
    assert.equal(card.jobId, 'job-2');
  });

  it('loadStatus loads pending count', async () => {
    const card = makeCard({
      pendingCountId: 'pending',
      fetchPending: async () => ({ pending_count: 42 }),
    });
    await card.loadStatus();
    assert.equal(document.getElementById('pending').textContent, 42);
  });

  it('stop() clears jobId', async () => {
    let stopped = false;
    const card = makeCard({
      stopJob: async () => { stopped = true; },
    });
    await card.start();
    await card.stop();
    assert.equal(stopped, true);
    assert.equal(card.jobId, null);
  });

  it('stop() is no-op without jobId', async () => {
    let stopped = false;
    const card = makeCard({
      stopJob: async () => { stopped = true; },
    });
    await card.stop();
    assert.equal(stopped, false);
  });
});
