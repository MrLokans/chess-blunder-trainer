import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createElement, resetDOM, setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

const { ProgressTracker } = await import('../blunder_tutor/web/static/js/progress-tracker.js');

describe('ProgressTracker', () => {
  let container, fill, text, startBtn, stopBtn;
  let messages;

  beforeEach(() => {
    resetDOM();
    messages = [];
    container = createElement('progress');
    fill = createElement('fill');
    text = createElement('text');
    startBtn = createElement('startBtn');
    stopBtn = createElement('stopBtn');
  });

  function makeTracker(opts = {}) {
    return new ProgressTracker({
      progressContainerId: 'progress',
      fillId: 'fill',
      textId: 'text',
      startBtnId: 'startBtn',
      stopBtnId: 'stopBtn',
      messageId: 'msg',
      showMessage: (id, type, txt) => messages.push({ id, type, txt }),
      ...opts,
    });
  }

  it('show() displays progress and hides start button', () => {
    const tracker = makeTracker();
    tracker.show({ progress_current: 5, progress_total: 10 });
    assert.equal(container.style.display, 'block');
    assert.equal(startBtn.style.display, 'none');
    assert.equal(stopBtn.style.display, 'inline-block');
    assert.equal(text.textContent, '5/10 (50%)');
    assert.equal(fill.style.width, '50%');
  });

  it('show() with null job still displays container', () => {
    const tracker = makeTracker();
    tracker.show(null);
    assert.equal(container.style.display, 'block');
    assert.equal(startBtn.style.display, 'none');
  });

  it('hide() hides progress and shows start button', () => {
    const tracker = makeTracker();
    tracker.show({ progress_current: 0, progress_total: 0 });
    tracker.hide();
    assert.equal(container.style.display, 'none');
    assert.equal(startBtn.style.display, 'inline-block');
    assert.equal(stopBtn.style.display, 'none');
  });

  it('updateProgress() updates fill and text', () => {
    const tracker = makeTracker();
    tracker.updateProgress(7, 20, 35);
    assert.equal(fill.style.width, '35%');
    assert.equal(text.textContent, '7/20 (35%)');
  });

  it('custom textFormat is used', () => {
    const tracker = makeTracker({
      textFormat: (c, t, p) => `${c} of ${t} done (${p}%)`,
    });
    tracker.updateProgress(3, 10, 30);
    assert.equal(text.textContent, '3 of 10 done (30%)');
  });

  it('works without stop button', () => {
    resetDOM();
    createElement('progress');
    createElement('fill');
    createElement('text');
    createElement('startBtn');

    const tracker = new ProgressTracker({
      progressContainerId: 'progress',
      fillId: 'fill',
      textId: 'text',
      startBtnId: 'startBtn',
      messageId: 'msg',
      showMessage: () => {},
    });
    assert.doesNotThrow(() => {
      tracker.show(null);
      tracker.hide();
    });
  });
});
