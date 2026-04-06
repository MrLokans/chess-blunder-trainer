import { describe, it, expect, beforeEach } from 'vitest';
import { JobCard } from '../src/shared/job-card';
import type { JobCardOptions } from '../src/shared/job-card';

function addElement(id: string, tag = 'div'): HTMLElement {
  const el = document.createElement(tag);
  el.id = id;
  document.body.appendChild(el);
  return el;
}

describe('JobCard', () => {
  let messages: Array<{ id: string; type: string; txt: string }>;

  beforeEach(() => {
    document.body.innerHTML = '';
    messages = [];
    addElement('progress');
    addElement('fill');
    addElement('text');
    addElement('startBtn');
    addElement('stopBtn');
    addElement('pending');
  });

  function makeCard(overrides: Partial<JobCardOptions> = {}) {
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
    expect(card.jobId).toBe('job-1');
    expect(messages[0]!.type).toBe('success');
    expect(messages[0]!.txt).toBe('Started!');
  });

  it('start() shows error on failure', async () => {
    const card = makeCard({
      startJob: async () => { throw new Error('engine down'); },
    });
    await card.start();
    expect(card.jobId).toBeNull();
    expect(messages[0]!.type).toBe('error');
    expect(messages[0]!.txt).toContain('engine down');
  });

  it('handleProgress returns false for unknown job', async () => {
    const card = makeCard();
    await card.start();
    expect(card.handleProgress({ job_id: 'other', current: 1, total: 10, percent: 10 })).toBe(false);
  });

  it('handleProgress returns true and updates for matching job', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleProgress({ job_id: 'job-1', current: 5, total: 10, percent: 50 });
    expect(result).toBe(true);
  });

  it('handleStatusChange completed resets jobId', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleStatusChange({ job_id: 'job-1', status: 'completed' });
    expect(result).toBe(true);
    expect(card.jobId).toBeNull();
    expect(messages[1]!.type).toBe('success');
    expect(messages[1]!.txt).toBe('Done!');
  });

  it('handleStatusChange failed shows error', async () => {
    const card = makeCard();
    await card.start();
    card.handleStatusChange({ job_id: 'job-1', status: 'failed', error_message: 'timeout' });
    expect(card.jobId).toBeNull();
    expect(messages[1]!.type).toBe('error');
    expect(messages[1]!.txt).toContain('timeout');
  });

  it('handleStatusChange ignores unknown job', async () => {
    const card = makeCard();
    await card.start();
    const result = card.handleStatusChange({ job_id: 'other', status: 'completed' });
    expect(result).toBe(false);
    expect(card.jobId).toBe('job-1');
  });

  it('onComplete callback fires on completion', async () => {
    let completed = false;
    const card = makeCard({ onComplete: () => { completed = true; } });
    await card.start();
    card.handleStatusChange({ job_id: 'job-1', status: 'completed' });
    expect(completed).toBe(true);
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
    expect(card.jobId).toBe('job-2');
  });

  it('loadStatus loads pending count', async () => {
    const card = makeCard({
      pendingCountId: 'pending',
      fetchPending: async () => ({ pending_count: 42 }),
    });
    await card.loadStatus();
    expect(document.getElementById('pending')!.textContent).toBe('42');
  });

  it('stop() clears jobId', async () => {
    let stopped = false;
    const card = makeCard({
      stopJob: async () => { stopped = true; },
    });
    await card.start();
    await card.stop();
    expect(stopped).toBe(true);
    expect(card.jobId).toBeNull();
  });

  it('stop() is no-op without jobId', async () => {
    let stopped = false;
    const card = makeCard({
      stopJob: async () => { stopped = true; },
    });
    await card.stop();
    expect(stopped).toBe(false);
  });
});
