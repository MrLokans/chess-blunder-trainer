// Vendored library type declarations.
// These cover the API surface actually used by this project.
// Expanded incrementally as modules are converted.

// chessground (v10.0.2) — vendored ES module
declare module '@vendor/chessground' {
  export function Chessground(element: HTMLElement, config?: Record<string, unknown>): ChessgroundApi;
  interface ChessgroundApi {
    set(config: Record<string, unknown>): void;
    setAutoShapes(shapes: unknown[]): void;
    destroy(): void;
  }
}

// chess.js (v0.10.3) — loaded globally via <script> in base.html
interface ChessMove {
  san: string;
  from: string;
  to: string;
  promotion?: string;
  color: 'w' | 'b';
  flags: string;
  piece: string;
  captured?: string;
}

interface ChessInstance {
  load(fen: string): boolean;
  fen(): string;
  turn(): 'w' | 'b';
  move(move: string, options?: { sloppy?: boolean }): ChessMove | null;
  move(move: { from: string; to: string; promotion?: string }): ChessMove | null;
  undo(): ChessMove | null;
  moves(options: { square?: string; verbose: true }): ChessMove[];
  moves(options?: { square?: string; verbose?: false }): string[];
  game_over(): boolean;
  in_check(): boolean;
  pgn(): string;
  load_pgn(pgn: string): boolean;
  history(options: { verbose: true }): ChessMove[];
  history(options?: { verbose?: false }): string[];
  board(): Array<Array<{ type: string; color: 'w' | 'b' } | null>>;
  get(square: string): { type: string; color: 'w' | 'b' } | null;
  put(piece: { type: string; color: 'w' | 'b' }, square: string): boolean;
  remove(square: string): { type: string; color: 'w' | 'b' } | null;
}

interface ChessStatic {
  new(fen?: string): ChessInstance;
  (fen?: string): ChessInstance;
}

declare const Chess: ChessStatic;

// htmx (v1.9.10) — loaded globally via <script> in base.html
interface HtmxStatic {
  process(elt: Element): void;
  trigger(elt: Element, event: string, detail?: unknown): void;
  ajax(verb: string, path: string, context?: unknown): Promise<void>;
  on(event: string, handler: (evt: Event) => void): void;
  off(event: string, handler: (evt: Event) => void): void;
}

declare const htmx: HtmxStatic;

// Chart.js (v4.4.1) — loaded globally via <script> in base.html
interface ChartConfiguration {
  type: string;
  data: {
    labels?: unknown[];
    datasets: Array<{
      label?: string;
      data: unknown[];
      [key: string]: unknown;
    }>;
  };
  options?: Record<string, unknown>;
}

interface ChartInstance {
  destroy(): void;
  update(): void;
  data: ChartConfiguration['data'];
  options: Record<string, unknown>;
}

interface ChartStatic {
  new(ctx: CanvasRenderingContext2D | HTMLCanvasElement, config: ChartConfiguration): ChartInstance;
  defaults: Record<string, unknown>;
}

declare const Chart: ChartStatic;

// i18n globals (injected by i18n.js in base.html)
declare function t(key: string, params?: Record<string, unknown>): string;
declare function formatNumber(n: number, opts?: Intl.NumberFormatOptions): string;
declare function formatDate(d: Date | string | number, style?: Intl.DateTimeFormatOptions): string;
declare function trackEvent(name: string, props?: Record<string, unknown>): void;

// Feature flags (injected by base.html inline script)
interface Window {
  __features: Record<string, boolean>;
  __i18n__: Record<string, string>;
  __locale__: string;
  __settingsInit?: import('./settings/types').SettingsInit;
  adjustColor?: (hex: string, lightness: number, saturation?: number) => string;
}
