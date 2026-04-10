import { Chessground } from '@vendor/chessground';

interface ChessgroundApi {
  set(config: Record<string, unknown>): void;
  setAutoShapes(shapes: unknown[]): void;
  destroy(): void;
}

interface MoveResult {
  from: string;
  to: string;
}

interface StepResult {
  fen: string;
  lastMove: MoveResult | null;
}

interface PositionInfo {
  index: number;
  fen: string;
  lastMove: MoveResult | null;
  isAtEnd: boolean;
}

export class MoveSequence {
  private _startFen: string | undefined;
  private _moves: string[] = [];
  private _index = -1;
  private _game!: ChessInstance;

  constructor(moves: string[], { startFen = 'start' }: { startFen?: string } = {}) {
    this._startFen = startFen === 'start' ? undefined : startFen;
    this.reset(moves);
  }

  get currentIndex(): number { return this._index; }
  get length(): number { return this._moves.length; }
  get fen(): string { return this._game.fen(); }
  get turn(): string { return this._game.turn(); }
  get isAtStart(): boolean { return this._index < 0; }
  get isAtEnd(): boolean { return this._index >= this._moves.length - 1; }

  get lastMove(): MoveResult | null {
    const hist = this._game.history({ verbose: true });
    if (hist.length === 0) return null;
    const last = hist[hist.length - 1];
    if (!last) return null;
    return { from: last.from, to: last.to };
  }

  stepForward(): StepResult | null {
    if (this.isAtEnd) return null;
    this._index++;
    const moveSan = this._moves[this._index];
    if (!moveSan) return null;
    const move = this._game.move(moveSan);
    if (!move) return null;
    return { fen: this.fen, lastMove: { from: move.from, to: move.to } };
  }

  stepBack(): StepResult | null {
    if (this.isAtStart) return null;
    this._game.undo();
    this._index--;
    return { fen: this.fen, lastMove: this.lastMove };
  }

  goTo(index: number): void {
    if (index < -1 || index >= this._moves.length) return;
    this._rebuildTo(index);
  }

  goToStart(): void { this._rebuildTo(-1); }

  goToEnd(): void { this._rebuildTo(this._moves.length - 1); }

  reset(moves?: string[], { startFen }: { startFen?: string } = {}): void {
    if (startFen !== undefined) {
      this._startFen = startFen === 'start' ? undefined : startFen;
    }
    this._moves = moves || [];
    this._rebuildTo(-1);
  }

  private _rebuildTo(targetIndex: number): void {
    this._game = this._startFen ? new Chess(this._startFen) : new Chess();
    this._index = -1;
    for (let i = 0; i <= targetIndex && i < this._moves.length; i++) {
      const moveSan = this._moves[i];
      if (!moveSan) break;
      const move = this._game.move(moveSan);
      if (!move) break;
      this._index = i;
    }
  }
}

function buildBoardSvg(light: string, dark: string): string {
  const squares = Array.from({ length: 64 }, (_, i) => {
    const x = i % 8, y = Math.floor(i / 8);
    return (x + y) % 2 === 1 ? `<rect x="${String(x)}" y="${String(y)}" width="1" height="1" fill="${dark}"/>` : '';
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">` +
    `<rect width="8" height="8" fill="${light}"/>${squares}</svg>`;
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

export class ReadOnlyBoard {
  private _el: HTMLElement;
  private _cg: ChessgroundApi | null;
  private _observer: MutationObserver | null = null;
  private _boardBgUrl = '';

  constructor(containerEl: HTMLElement, { orientation = 'white', fen = 'start' }: { orientation?: string; fen?: string } = {}) {
    this._el = containerEl;
    const startFen = fen === 'start' ? undefined : fen;
    this._cg = Chessground(this._el, {
      fen: startFen,
      orientation,
      coordinates: false,
      animation: { enabled: true, duration: 150 },
      movable: { free: false, color: undefined },
      draggable: { enabled: false },
      highlight: { lastMove: true, check: true },
      premovable: { enabled: false },
      drawable: { enabled: false },
    });
    this._applyBoardBackground();
    this._observeBoardChanges();
  }

  private _applyBoardBackground(): void {
    const style = getComputedStyle(document.documentElement);
    const light = style.getPropertyValue('--board-light').trim() || '#E0E0E0';
    const dark = style.getPropertyValue('--board-dark').trim() || '#A0A0A0';
    this._boardBgUrl = `url("${buildBoardSvg(light, dark)}")`;
    this._el.style.setProperty('--board-bg', this._boardBgUrl);
    this._setBoardInline();
  }

  private _setBoardInline(): void {
    const board = this._el.querySelector('cg-board');
    if (board instanceof HTMLElement) board.style.backgroundImage = this._boardBgUrl;
  }

  private _observeBoardChanges(): void {
    this._observer = new MutationObserver(() => { this._setBoardInline(); });
    this._observer.observe(this._el, { childList: true });
  }

  setPosition(fen: string, lastMove: MoveResult | null): void {
    this._cg?.set({
      fen,
      lastMove: lastMove ? [lastMove.from, lastMove.to] : undefined,
    });
  }

  setOrientation(color: string): void {
    this._cg?.set({ orientation: color });
  }

  setShapes(shapes: unknown[]): void {
    this._cg?.setAutoShapes(shapes);
  }

  destroy(): void {
    if (this._observer) {
      this._observer.disconnect();
      this._observer = null;
    }
    if (this._cg) {
      this._cg.destroy();
      this._cg = null;
    }
  }
}

export class PlaybackController {
  private _speed: number;
  private _onTick: (() => void) | undefined;
  private _intervalId: ReturnType<typeof setInterval> | null = null;

  constructor({ speed = 1000, onTick }: { speed?: number; onTick?: () => void } = {}) {
    this._speed = speed;
    this._onTick = onTick;
  }

  get isPlaying(): boolean { return this._intervalId !== null; }

  play(): void {
    if (this._intervalId) return;
    this._intervalId = setInterval(() => {
      if (this._onTick) this._onTick();
    }, this._speed);
  }

  pause(): void {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  toggle(): void {
    if (this.isPlaying) { this.pause(); } else { this.play(); }
  }

  setSpeed(ms: number): void {
    this._speed = ms;
    if (this.isPlaying) {
      this.pause();
      this.play();
    }
  }

  destroy(): void {
    this.pause();
  }
}

export interface SequencePlayerOptions {
  orientation?: string;
  speed?: number;
  startFen?: string;
  showControls?: boolean;
  onPositionChange?: ((info: PositionInfo) => void) | null;
}

export default class SequencePlayer {
  private _containerEl: HTMLElement;
  private _boardEl!: HTMLElement;
  private _sequence: MoveSequence;
  private _board: ReadOnlyBoard;
  private _playback: PlaybackController;
  private _onPositionChange: ((info: PositionInfo) => void) | null;
  private _orientation: string;

  private _btnStart?: HTMLButtonElement;
  private _btnBack?: HTMLButtonElement;
  private _btnPlay?: HTMLButtonElement;
  private _btnForward?: HTMLButtonElement;
  private _btnEnd?: HTMLButtonElement;
  private _statusEl?: HTMLElement;

  constructor(containerEl: HTMLElement, moves: string[], options: SequencePlayerOptions = {}) {
    const {
      orientation = 'white',
      speed = 1000,
      startFen = 'start',
      showControls = true,
      onPositionChange = null,
    } = options;

    this._containerEl = containerEl;
    this._onPositionChange = onPositionChange;
    this._orientation = orientation;

    this._containerEl.innerHTML = '';
    this._containerEl.classList.add('sequence-player');

    this._boardEl = document.createElement('div');
    this._boardEl.className = 'sequence-player-board';
    this._containerEl.appendChild(this._boardEl);

    this._sequence = new MoveSequence(moves, { startFen });
    this._board = new ReadOnlyBoard(this._boardEl, {
      orientation,
      fen: this._sequence.fen,
    });

    this._playback = new PlaybackController({
      speed,
      onTick: () => { this._onTick(); },
    });

    if (showControls) {
      this._buildControls();
      this._buildStatus();
      this._updateControls();
    }
  }

  setMoves(moves: string[], { orientation, startFen }: { orientation?: string; startFen?: string } = {}): void {
    this._playback.pause();
    if (orientation) {
      this._orientation = orientation;
      this._board.setOrientation(orientation);
    }
    this._sequence.reset(moves, { startFen });
    this._board.setPosition(this._sequence.fen, null);
    this._updateControls();
    this._firePositionChange();
  }

  destroy(): void {
    this._playback.destroy();
    this._board.destroy();
    this._containerEl.innerHTML = '';
    this._containerEl.classList.remove('sequence-player');
  }

  private _buildControls(): void {
    const bar = document.createElement('div');
    bar.className = 'sequence-player-controls';

    const btn = (labelKey: string, icon: string, handler: () => void): HTMLButtonElement => {
      const b = document.createElement('button');
      b.type = 'button';
      b.title = t(labelKey);
      b.textContent = icon;
      b.addEventListener('click', handler);
      return b;
    };

    this._btnStart = btn('traps.player.go_start', '\u23EE', () => { this._goToStart(); });
    this._btnBack = btn('traps.player.step_back', '\u25C0', () => { this._stepBack(); });
    this._btnPlay = btn('traps.player.play', '\u25B6', () => { this._togglePlay(); });
    this._btnForward = btn('traps.player.step_forward', '\u25B6', () => { this._stepForward(); });
    this._btnEnd = btn('traps.player.go_end', '\u23ED', () => { this._goToEnd(); });

    bar.append(this._btnStart, this._btnBack, this._btnPlay, this._btnForward, this._btnEnd);
    this._containerEl.appendChild(bar);
  }

  private _buildStatus(): void {
    this._statusEl = document.createElement('div');
    this._statusEl.className = 'sequence-player-status';
    this._containerEl.appendChild(this._statusEl);
  }

  private _onTick(): void {
    if (this._sequence.isAtEnd) {
      this._playback.pause();
      this._updateControls();
      return;
    }
    this._stepForward();
  }

  private _stepForward(): void {
    const result = this._sequence.stepForward();
    if (!result) return;
    this._board.setPosition(result.fen, result.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  private _stepBack(): void {
    this._playback.pause();
    const result = this._sequence.stepBack();
    if (!result) return;
    this._board.setPosition(this._sequence.fen, result.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  private _goToStart(): void {
    this._playback.pause();
    this._sequence.goToStart();
    this._board.setPosition(this._sequence.fen, null);
    this._updateControls();
    this._firePositionChange();
  }

  private _goToEnd(): void {
    this._playback.pause();
    this._sequence.goToEnd();
    this._board.setPosition(this._sequence.fen, this._sequence.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  private _togglePlay(): void {
    if (this._sequence.isAtEnd) {
      this._sequence.goToStart();
      this._board.setPosition(this._sequence.fen, null);
    }
    this._playback.toggle();
    this._updateControls();
  }

  private _updateControls(): void {
    if (!this._btnPlay) return;

    const atStart = this._sequence.isAtStart;
    const atEnd = this._sequence.isAtEnd;
    const playing = this._playback.isPlaying;

    if (this._btnStart) this._btnStart.disabled = atStart;
    if (this._btnBack) this._btnBack.disabled = atStart;
    if (this._btnForward) this._btnForward.disabled = atEnd;
    if (this._btnEnd) this._btnEnd.disabled = atEnd;

    this._btnPlay.textContent = playing ? '\u23F8' : '\u25B6';
    this._btnPlay.title = playing ? t('traps.player.pause') : t('traps.player.play');

    if (this._statusEl) {
      const current = this._sequence.currentIndex + 1;
      const total = this._sequence.length;
      this._statusEl.textContent = total > 0
        ? t('traps.player.move_counter').replace('{current}', String(current)).replace('{total}', String(total))
        : '';
    }
  }

  private _firePositionChange(): void {
    if (!this._onPositionChange) return;
    this._onPositionChange({
      index: this._sequence.currentIndex,
      fen: this._sequence.fen,
      lastMove: this._sequence.lastMove,
      isAtEnd: this._sequence.isAtEnd,
    });
  }
}
