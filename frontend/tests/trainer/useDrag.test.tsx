import { describe, expect, it } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { useRef } from 'preact/hooks';
import { useDrag } from '../../src/trainer/hooks/useDrag';

function DragCard() {
  const cardRef = useRef<HTMLDivElement>(null);
  const { handleRef } = useDrag(cardRef);
  return (
    <div>
      <div ref={cardRef} data-testid="card">
        <div ref={handleRef} data-testid="handle" />
      </div>
    </div>
  );
}

describe('useDrag', () => {
  it.each(['pointerUp', 'pointerCancel', 'lostPointerCapture'] as const)('ends the drag on %s', (event) => {
    const { getByTestId } = render(<DragCard />);
    const card = getByTestId('card');
    const handle = getByTestId('handle');
    handle.setPointerCapture = () => {};
    handle.hasPointerCapture = () => false;

    fireEvent.pointerDown(handle, { pointerId: 1, isPrimary: true, clientX: 10, clientY: 10 });
    expect(card.classList.contains('dragging')).toBe(true);

    fireEvent[event](handle, { pointerId: 1 });
    expect(card.classList.contains('dragging')).toBe(false);

    fireEvent.pointerMove(handle, { pointerId: 1, clientX: 80, clientY: 80 });
    expect(card.style.left).toBe('');
  });

  it('ignores a second finger', () => {
    const { getByTestId } = render(<DragCard />);
    const handle = getByTestId('handle');
    handle.setPointerCapture = () => {};

    fireEvent.pointerDown(handle, { pointerId: 2, isPrimary: false, clientX: 10, clientY: 10 });
    expect(getByTestId('card').classList.contains('dragging')).toBe(false);
  });
});
