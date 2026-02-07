import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { debounce, throttle } from '../blunder_tutor/web/static/js/debounce.js';

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

describe('debounce', () => {
  it('delays execution until after the quiet period', async () => {
    let callCount = 0;
    const fn = debounce(() => { callCount++; }, 50);

    fn();
    fn();
    fn();
    assert.equal(callCount, 0);

    await delay(80);
    assert.equal(callCount, 1);
  });

  it('resets timer on each call', async () => {
    let callCount = 0;
    const fn = debounce(() => { callCount++; }, 50);

    fn();
    await delay(30);
    fn(); // resets the timer
    await delay(30);
    assert.equal(callCount, 0); // still waiting

    await delay(40);
    assert.equal(callCount, 1);
  });

  it('passes arguments to the wrapped function', async () => {
    let received = null;
    const fn = debounce((a, b) => { received = [a, b]; }, 20);

    fn('x', 'y');
    await delay(40);
    assert.deepEqual(received, ['x', 'y']);
  });

  it('uses the last call arguments', async () => {
    let received = null;
    const fn = debounce((v) => { received = v; }, 20);

    fn('first');
    fn('second');
    fn('third');
    await delay(40);
    assert.equal(received, 'third');
  });
});

describe('throttle', () => {
  it('fires immediately on first call', async () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 50);

    fn();
    assert.equal(callCount, 1);
  });

  it('suppresses rapid subsequent calls', async () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 50);

    fn();
    fn();
    fn();
    assert.equal(callCount, 1);

    await delay(80);
    // trailing call fires
    assert.equal(callCount, 2);
  });

  it('allows calls after the interval passes', async () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 30);

    fn();
    assert.equal(callCount, 1);

    await delay(50);
    fn();
    assert.equal(callCount, 2);
  });
});
