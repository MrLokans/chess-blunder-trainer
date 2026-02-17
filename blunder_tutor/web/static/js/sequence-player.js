import { Chessground } from '../vendor/chessground-10.0.2.min.js';

class MoveSequence {
  constructor(moves, { startFen = 'start' } = {}) {
    this._startFen = startFen === 'start' ? undefined : startFen;
    this.reset(moves);
  }

  get currentIndex() { return this._index; }
  get length() { return this._moves.length; }
  get fen() { return this._game.fen(); }
  get turn() { return this._game.turn(); }
  get isAtStart() { return this._index < 0; }
  get isAtEnd() { return this._index >= this._moves.length - 1; }

  get lastMove() {
    const hist = this._game.history({ verbose: true });
    if (hist.length === 0) return null;
    const last = hist[hist.length - 1];
    return { from: last.from, to: last.to };
  }

  stepForward() {
    if (this.isAtEnd) return null;
    this._index++;
    const move = this._game.move(this._moves[this._index]);
    if (!move) return null;
    return { fen: this.fen, lastMove: { from: move.from, to: move.to } };
  }

  stepBack() {
    if (this.isAtStart) return null;
    this._game.undo();
    this._index--;
    return { fen: this.fen, lastMove: this.lastMove };
  }

  goTo(index) {
    if (index < -1 || index >= this._moves.length) return;
    this._rebuildTo(index);
  }

  goToStart() { this._rebuildTo(-1); }

  goToEnd() { this._rebuildTo(this._moves.length - 1); }

  reset(moves, { startFen } = {}) {
    if (startFen !== undefined) {
      this._startFen = startFen === 'start' ? undefined : startFen;
    }
    this._moves = moves || [];
    this._rebuildTo(-1);
  }

  _rebuildTo(targetIndex) {
    this._game = this._startFen ? new Chess(this._startFen) : new Chess();
    this._index = -1;
    for (let i = 0; i <= targetIndex && i < this._moves.length; i++) {
      const move = this._game.move(this._moves[i]);
      if (!move) break;
      this._index = i;
    }
  }
}

function buildBoardSvg(light, dark) {
  const squares = Array.from({ length: 64 }, (_, i) => {
    const x = i % 8, y = Math.floor(i / 8);
    return (x + y) % 2 === 1 ? `<rect x="${x}" y="${y}" width="1" height="1" fill="${dark}"/>` : '';
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">` +
    `<rect width="8" height="8" fill="${light}"/>${squares}</svg>`;
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

class ReadOnlyBoard {
  constructor(containerEl, { orientation = 'white', fen = 'start' } = {}) {
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
  }

  _applyBoardBackground() {
    const style = getComputedStyle(document.documentElement);
    const light = style.getPropertyValue('--board-light').trim() || '#E0E0E0';
    const dark = style.getPropertyValue('--board-dark').trim() || '#A0A0A0';
    const board = this._el.querySelector('cg-board');
    if (board) {
      board.style.backgroundImage = `url("${buildBoardSvg(light, dark)}")`;
    }
  }

  setPosition(fen, lastMove) {
    this._cg.set({
      fen,
      lastMove: lastMove ? [lastMove.from, lastMove.to] : undefined,
    });
  }

  setOrientation(color) {
    this._cg.set({ orientation: color });
  }

  setShapes(shapes) {
    this._cg.setAutoShapes(shapes);
  }

  destroy() {
    if (this._cg) {
      this._cg.destroy();
      this._cg = null;
    }
  }
}

class PlaybackController {
  constructor({ speed = 1000, onTick } = {}) {
    this._speed = speed;
    this._onTick = onTick;
    this._intervalId = null;
  }

  get isPlaying() { return this._intervalId !== null; }

  play() {
    if (this._intervalId) return;
    this._intervalId = setInterval(() => {
      if (this._onTick) this._onTick();
    }, this._speed);
  }

  pause() {
    if (this._intervalId) {
      clearInterval(this._intervalId);
      this._intervalId = null;
    }
  }

  toggle() {
    this.isPlaying ? this.pause() : this.play();
  }

  setSpeed(ms) {
    this._speed = ms;
    if (this.isPlaying) {
      this.pause();
      this.play();
    }
  }

  destroy() {
    this.pause();
  }
}

export default class SequencePlayer {
  constructor(containerEl, moves, options = {}) {
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
      onTick: () => this._onTick(),
    });

    if (showControls) {
      this._buildControls();
      this._buildStatus();
      this._updateControls();
    }
  }

  setMoves(moves, { orientation, startFen } = {}) {
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

  destroy() {
    this._playback.destroy();
    this._board.destroy();
    this._containerEl.innerHTML = '';
    this._containerEl.classList.remove('sequence-player');
  }

  _buildControls() {
    const bar = document.createElement('div');
    bar.className = 'sequence-player-controls';

    const btn = (label, icon, handler) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.title = t(label);
      b.textContent = icon;
      b.addEventListener('click', handler);
      return b;
    };

    this._btnStart = btn('traps.player.go_start', '⏮', () => this._goToStart());
    this._btnBack = btn('traps.player.step_back', '◀', () => this._stepBack());
    this._btnPlay = btn('traps.player.play', '▶', () => this._togglePlay());
    this._btnForward = btn('traps.player.step_forward', '▶', () => this._stepForward());
    this._btnEnd = btn('traps.player.go_end', '⏭', () => this._goToEnd());

    bar.append(this._btnStart, this._btnBack, this._btnPlay, this._btnForward, this._btnEnd);
    this._containerEl.appendChild(bar);
  }

  _buildStatus() {
    this._statusEl = document.createElement('div');
    this._statusEl.className = 'sequence-player-status';
    this._containerEl.appendChild(this._statusEl);
  }

  _onTick() {
    if (this._sequence.isAtEnd) {
      this._playback.pause();
      this._updateControls();
      return;
    }
    this._stepForward();
  }

  _stepForward() {
    const result = this._sequence.stepForward();
    if (!result) return;
    this._board.setPosition(result.fen, result.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  _stepBack() {
    this._playback.pause();
    const result = this._sequence.stepBack();
    if (!result) return;
    this._board.setPosition(this._sequence.fen, result.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  _goToStart() {
    this._playback.pause();
    this._sequence.goToStart();
    this._board.setPosition(this._sequence.fen, null);
    this._updateControls();
    this._firePositionChange();
  }

  _goToEnd() {
    this._playback.pause();
    this._sequence.goToEnd();
    this._board.setPosition(this._sequence.fen, this._sequence.lastMove);
    this._updateControls();
    this._firePositionChange();
  }

  _togglePlay() {
    if (this._sequence.isAtEnd) {
      this._sequence.goToStart();
      this._board.setPosition(this._sequence.fen, null);
    }
    this._playback.toggle();
    this._updateControls();
  }

  _updateControls() {
    if (!this._btnPlay) return;

    const atStart = this._sequence.isAtStart;
    const atEnd = this._sequence.isAtEnd;
    const playing = this._playback.isPlaying;

    this._btnStart.disabled = atStart;
    this._btnBack.disabled = atStart;
    this._btnForward.disabled = atEnd;
    this._btnEnd.disabled = atEnd;

    this._btnPlay.textContent = playing ? '⏸' : '▶';
    this._btnPlay.title = playing ? t('traps.player.pause') : t('traps.player.play');

    if (this._statusEl) {
      const current = this._sequence.currentIndex + 1;
      const total = this._sequence.length;
      this._statusEl.textContent = total > 0
        ? t('traps.player.move_counter').replace('{current}', current).replace('{total}', total)
        : '';
    }
  }

  _firePositionChange() {
    if (!this._onPositionChange) return;
    this._onPositionChange({
      index: this._sequence.currentIndex,
      fen: this._sequence.fen,
      lastMove: this._sequence.lastMove,
      isAtEnd: this._sequence.isAtEnd,
    });
  }
}

export { MoveSequence, ReadOnlyBoard, PlaybackController };
