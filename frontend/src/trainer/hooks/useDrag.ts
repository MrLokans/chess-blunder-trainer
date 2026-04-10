import { useRef, useCallback, useEffect } from 'preact/hooks';

const DRAG_STORAGE_KEY = 'blunder-tutor-result-card-pos';

export function useDrag(cardRef: preact.RefObject<HTMLDivElement | null>): {
  handleRef: (el: HTMLDivElement | null) => void;
  restorePosition: () => void;
} {
  const handleElRef = useRef<HTMLDivElement | null>(null);
  const draggingRef = useRef(false);
  const startRef = useRef({ x: 0, y: 0, left: 0, top: 0 });

  const restorePosition = useCallback(() => {
    const card = cardRef.current;
    if (!card) return;
    const parent = card.parentElement;
    if (!parent) return;
    const stored = localStorage.getItem(DRAG_STORAGE_KEY);
    if (!stored) return;

    try {
      const pos = JSON.parse(stored) as { leftPct: number; topPct: number };
      const parentRect = parent.getBoundingClientRect();
      let left = pos.leftPct * parentRect.width;
      let top = pos.topPct * parentRect.height;
      left = Math.max(0, Math.min(left, parentRect.width - card.offsetWidth));
      top = Math.max(0, Math.min(top, parentRect.height - card.offsetHeight));
      card.style.left = `${left}px`;
      card.style.top = `${top}px`;
      card.style.right = 'auto';
      card.style.bottom = 'auto';
    } catch { /* ignore corrupt data */ }
  }, [cardRef]);

  const savePosition = useCallback(() => {
    const card = cardRef.current;
    if (!card) return;
    const parent = card.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();
    const cardRect = card.getBoundingClientRect();
    const pos = {
      leftPct: (cardRect.left - parentRect.left) / parentRect.width,
      topPct: (cardRect.top - parentRect.top) / parentRect.height,
    };
    localStorage.setItem(DRAG_STORAGE_KEY, JSON.stringify(pos));
  }, [cardRef]);

  const onPointerDown = useCallback((e: PointerEvent) => {
    e.preventDefault();
    const card = cardRef.current;
    const handle = handleElRef.current;
    if (!card || !handle) return;

    draggingRef.current = true;
    card.classList.add('dragging');
    const rect = card.getBoundingClientRect();
    startRef.current = { x: e.clientX, y: e.clientY, left: rect.left, top: rect.top };
    handle.setPointerCapture(e.pointerId);
  }, [cardRef]);

  const onPointerMove = useCallback((e: PointerEvent) => {
    if (!draggingRef.current) return;
    const card = cardRef.current;
    if (!card) return;
    const parent = card.parentElement;
    if (!parent) return;
    const parentRect = parent.getBoundingClientRect();
    const s = startRef.current;
    let newLeft = s.left + (e.clientX - s.x) - parentRect.left;
    let newTop = s.top + (e.clientY - s.y) - parentRect.top;
    newLeft = Math.max(0, Math.min(newLeft, parentRect.width - card.offsetWidth));
    newTop = Math.max(0, Math.min(newTop, parentRect.height - card.offsetHeight));
    card.style.left = `${newLeft}px`;
    card.style.top = `${newTop}px`;
    card.style.right = 'auto';
    card.style.bottom = 'auto';
  }, [cardRef]);

  const onPointerUp = useCallback((e: PointerEvent) => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    cardRef.current?.classList.remove('dragging');
    handleElRef.current?.releasePointerCapture(e.pointerId);
    savePosition();
  }, [cardRef, savePosition]);

  const handleRef = useCallback((el: HTMLDivElement | null) => {
    const prev = handleElRef.current;
    if (prev) {
      prev.removeEventListener('pointerdown', onPointerDown);
      prev.removeEventListener('pointermove', onPointerMove);
      prev.removeEventListener('pointerup', onPointerUp);
    }
    handleElRef.current = el;
    if (el) {
      el.addEventListener('pointerdown', onPointerDown);
      el.addEventListener('pointermove', onPointerMove);
      el.addEventListener('pointerup', onPointerUp);
    }
  }, [onPointerDown, onPointerMove, onPointerUp]);

  useEffect(() => {
    return () => {
      const el = handleElRef.current;
      if (el) {
        el.removeEventListener('pointerdown', onPointerDown);
        el.removeEventListener('pointermove', onPointerMove);
        el.removeEventListener('pointerup', onPointerUp);
      }
    };
  }, [onPointerDown, onPointerMove, onPointerUp]);

  return { handleRef, restorePosition };
}
