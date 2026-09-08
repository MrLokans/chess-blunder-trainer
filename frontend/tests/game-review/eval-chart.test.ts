import { afterEach, describe, expect, test, vi } from 'vitest';
import { EvalChart } from '../../src/game-review/eval-chart';

const MOVES = [
  { player: 'white', eval_after: 20 },
  { player: 'black', eval_after: -300, classification: 'blunder' },
];

function stubContext(): void {
  const ctx = new Proxy({}, { get: () => vi.fn() });
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(ctx as CanvasRenderingContext2D);
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('EvalChart', () => {
  test('stops reporting clicks after destroy', () => {
    stubContext();
    const canvas = document.createElement('canvas');
    vi.spyOn(canvas, 'getBoundingClientRect').mockReturnValue({ left: 0, width: 100 } as DOMRect);
    const chart = new EvalChart(canvas);
    chart.render(MOVES);
    const onSelect = vi.fn();
    chart.onClick(onSelect);

    canvas.dispatchEvent(new MouseEvent('click', { clientX: 0 }));
    expect(onSelect).toHaveBeenCalledTimes(1);

    chart.destroy();
    canvas.dispatchEvent(new MouseEvent('click', { clientX: 0 }));
    expect(onSelect).toHaveBeenCalledTimes(1);
  });
});
