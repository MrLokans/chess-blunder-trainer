import { describe, it, expect, afterEach } from 'vitest';
import { mountIsland } from '../../src/shared/mount-island';

afterEach(() => { document.body.innerHTML = ''; });

describe('mountIsland', () => {
  it('renders the node into the element with the given id', () => {
    const el = document.createElement('div');
    el.id = 'auth-root';
    document.body.appendChild(el);
    mountIsland('auth-root', <p>hello island</p>);
    expect(el.textContent).toContain('hello island');
  });

  it('is a no-op (no throw) when the root id is absent', () => {
    expect(() => { mountIsland('missing-root', <p>x</p>); }).not.toThrow();
  });
});
