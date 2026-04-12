import { describe, it, expect } from 'vitest';
import { debounce, throttle } from '../src/shared/debounce';

function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

describe('debounce', () => {
  it('delays execution until after the quiet period', async () => {
    let callCount = 0;
    const fn = debounce(() => { callCount++; }, 50);
    fn(); fn(); fn();
    expect(callCount).toBe(0);
    await delay(80);
    expect(callCount).toBe(1);
  });

  it('resets timer on each call', async () => {
    let callCount = 0;
    const fn = debounce(() => { callCount++; }, 50);
    fn();
    await delay(30);
    fn();
    await delay(30);
    expect(callCount).toBe(0);
    await delay(40);
    expect(callCount).toBe(1);
  });

  it('passes arguments to the wrapped function', async () => {
    let received: unknown[] | null = null;
    const fn = debounce((a: string, b: string) => { received = [a, b]; }, 20);
    fn('x', 'y');
    await delay(40);
    expect(received).toEqual(['x', 'y']);
  });

  it('uses the last call arguments', async () => {
    let received: string | null = null;
    const fn = debounce((v: string) => { received = v; }, 20);
    fn('first'); fn('second'); fn('third');
    await delay(40);
    expect(received).toBe('third');
  });
});

describe('throttle', () => {
  it('fires immediately on first call', () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 50);
    fn();
    expect(callCount).toBe(1);
  });

  it('suppresses rapid subsequent calls', async () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 50);
    fn(); fn(); fn();
    expect(callCount).toBe(1);
    await delay(80);
    expect(callCount).toBe(2);
  });

  it('allows calls after the interval passes', async () => {
    let callCount = 0;
    const fn = throttle(() => { callCount++; }, 30);
    fn();
    expect(callCount).toBe(1);
    await delay(50);
    fn();
    expect(callCount).toBe(2);
  });
});
