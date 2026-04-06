import { describe, it, expect, beforeEach } from 'vitest';
import { ProgressTracker } from '../src/shared/progress-tracker';

function addElement(id: string, tag = 'div'): HTMLElement {
  const el = document.createElement(tag);
  el.id = id;
  document.body.appendChild(el);
  return el;
}

describe('ProgressTracker', () => {
  let messages: Array<{ id: string; type: string; txt: string }>;

  beforeEach(() => {
    document.body.innerHTML = '';
    messages = [];
    addElement('progress');
    addElement('fill');
    addElement('text');
    addElement('startBtn');
    addElement('stopBtn');
  });

  function makeTracker(opts: Record<string, unknown> = {}) {
    return new ProgressTracker({
      progressContainerId: 'progress',
      fillId: 'fill',
      textId: 'text',
      startBtnId: 'startBtn',
      stopBtnId: 'stopBtn',
      messageId: 'msg',
      showMessage: (id: string, type: string, txt: string) => messages.push({ id, type, txt }),
      ...opts,
    });
  }

  it('show() displays progress and hides start button', () => {
    const tracker = makeTracker();
    tracker.show({ progress_current: 5, progress_total: 10 });
    expect(tracker.progressContainer!.classList.contains('hidden')).toBe(false);
    expect(tracker.startBtn!.classList.contains('hidden')).toBe(true);
    expect(tracker.stopBtn!.classList.contains('hidden')).toBe(false);
    expect(tracker.text!.textContent).toBe('5/10 (50%)');
    expect(tracker.fill!.style.width).toBe('50%');
  });

  it('show() with null job still displays container', () => {
    const tracker = makeTracker();
    tracker.show(null);
    expect(tracker.progressContainer!.classList.contains('hidden')).toBe(false);
    expect(tracker.startBtn!.classList.contains('hidden')).toBe(true);
  });

  it('hide() hides progress and shows start button', () => {
    const tracker = makeTracker();
    tracker.show({ progress_current: 0, progress_total: 0 });
    tracker.hide();
    expect(tracker.progressContainer!.classList.contains('hidden')).toBe(true);
    expect(tracker.startBtn!.classList.contains('hidden')).toBe(false);
    expect(tracker.stopBtn!.classList.contains('hidden')).toBe(true);
  });

  it('updateProgress() updates fill and text', () => {
    const tracker = makeTracker();
    tracker.updateProgress(7, 20, 35);
    expect(tracker.fill!.style.width).toBe('35%');
    expect(tracker.text!.textContent).toBe('7/20 (35%)');
  });

  it('custom textFormat is used', () => {
    const tracker = makeTracker({
      textFormat: (c: number, total: number, p: number) => `${c} of ${total} done (${p}%)`,
    });
    tracker.updateProgress(3, 10, 30);
    expect(tracker.text!.textContent).toBe('3 of 10 done (30%)');
  });

  it('works without stop button', () => {
    document.body.innerHTML = '';
    addElement('progress');
    addElement('fill');
    addElement('text');
    addElement('startBtn');

    const tracker = new ProgressTracker({
      progressContainerId: 'progress',
      fillId: 'fill',
      textId: 'text',
      startBtnId: 'startBtn',
      messageId: 'msg',
      showMessage: () => {},
    });
    expect(() => {
      tracker.show(null);
      tracker.hide();
    }).not.toThrow();
  });
});
