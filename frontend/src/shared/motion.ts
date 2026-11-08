export function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === 'function'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

// Pieces jump instead of sliding when reduced motion is on; last-move highlights still mark what changed.
export function boardAnimation(duration: number): { enabled: boolean; duration: number } {
  return { enabled: !prefersReducedMotion(), duration };
}

export function scrollBehavior(): ScrollBehavior {
  return prefersReducedMotion() ? 'auto' : 'smooth';
}
