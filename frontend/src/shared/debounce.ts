export function debounce<T extends (...args: never[]) => void>(
  fn: T,
  delayMs: number,
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null;
  return function (this: unknown, ...args: Parameters<T>) {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      fn.apply(this, args);
    }, delayMs);
  };
}

export function throttle<T extends (...args: never[]) => void>(
  fn: T,
  intervalMs: number,
): (...args: Parameters<T>) => void {
  let lastRun = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  return function (this: unknown, ...args: Parameters<T>) {
    const now = Date.now();
    const remaining = intervalMs - (now - lastRun);
    if (remaining <= 0) {
      if (timer) { clearTimeout(timer); timer = null; }
      lastRun = now;
      fn.apply(this, args);
    } else if (!timer) {
      timer = setTimeout(() => {
        lastRun = Date.now();
        timer = null;
        fn.apply(this, args);
      }, remaining);
    }
  };
}
