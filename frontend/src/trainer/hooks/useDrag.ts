import { useRef, useCallback, useEffect, useMemo } from 'preact/hooks';
import { STORAGE_KEYS } from '../../shared/storage-keys';

const DRAG_STORAGE_KEY = STORAGE_KEYS.trainerResultCardPos;

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
      card.style.left = `${String(left)}px`;
      card.style.top = `${String(top)}px`;
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
    if (!e.isPrimary) return;
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
    card.style.left = `${String(newLeft)}px`;
    card.style.top = `${String(newTop)}px`;
    card.style.right = 'auto';
    card.style.bottom = 'auto';
  }, [cardRef]);

  // Also bound to pointercancel and lostpointercapture so an interrupted touch never leaves the drag stuck.
  const onPointerEnd = useCallback((e: PointerEvent) => {
    if (!draggingRef.current) return;
    draggingRef.current = false;
    cardRef.current?.classList.remove('dragging');
    const handle = handleElRef.current;
    if (handle?.hasPointerCapture(e.pointerId)) handle.releasePointerCapture(e.pointerId);
    savePosition();
  }, [cardRef, savePosition]);

  const listeners = useMemo((): Array<[string, (e: PointerEvent) => void]> => [
    ['pointerdown', onPointerDown],
    ['pointermove', onPointerMove],
    ['pointerup', onPointerEnd],
    ['pointercancel', onPointerEnd],
    ['lostpointercapture', onPointerEnd],
  ], [onPointerDown, onPointerMove, onPointerEnd]);

  const handleRef = useCallback((el: HTMLDivElement | null) => {
    const prev = handleElRef.current;
    if (prev) for (const [type, fn] of listeners) prev.removeEventListener(type, fn as EventListener);
    handleElRef.current = el;
    if (el) for (const [type, fn] of listeners) el.addEventListener(type, fn as EventListener);
  }, [listeners]);

  useEffect(() => {
    return () => {
      const el = handleElRef.current;
      if (el) for (const [type, fn] of listeners) el.removeEventListener(type, fn as EventListener);
    };
  }, [listeners]);

  return { handleRef, restorePosition };
}
