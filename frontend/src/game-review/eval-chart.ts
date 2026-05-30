const MAX_CP = 500;

interface ReviewMove {
  player: string;
  eval_after: number;
  classification?: string;
}

function clampEval(cp: number): number {
  return Math.max(-MAX_CP, Math.min(MAX_CP, cp));
}

export function evalFromWhite(move: ReviewMove): number {
  return move.player === 'black' ? -move.eval_after : move.eval_after;
}

function cpToY(cp: number, height: number): number {
  const clamped = clampEval(cp);
  return height / 2 - (clamped / MAX_CP) * (height / 2);
}

export class EvalChart {
  private _canvas: HTMLCanvasElement;
  private _ctx: CanvasRenderingContext2D;
  private _moves: ReviewMove[] = [];
  private _activePly = -1;
  private _onClick: ((index: number) => void) | null = null;

  constructor(canvasEl: HTMLCanvasElement) {
    this._canvas = canvasEl;
    this._ctx = canvasEl.getContext('2d') ?? (() => { throw new Error('2d context unavailable'); })();

    this._canvas.addEventListener('click', (e) => {
      if (!this._onClick || this._moves.length === 0) return;
      const rect = this._canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const scaleX = this._canvas.width / rect.width;
      const px = x * scaleX;
      const step = this._canvas.width / Math.max(this._moves.length - 1, 1);
      const index = Math.round(px / step);
      const clamped = Math.max(0, Math.min(this._moves.length - 1, index));
      this._onClick(clamped);
    });
  }

  render(moves: ReviewMove[]): void {
    this._moves = moves;
    this._draw();
  }

  setActivePly(index: number): void {
    this._activePly = index;
    this._draw();
  }

  onClick(callback: (index: number) => void): void {
    this._onClick = callback;
  }

  private _palette(): { line: string; midline: string; active: string; blunder: string; mistake: string } {
    const style = getComputedStyle(document.documentElement);
    const read = (name: string, fallback: string): string => style.getPropertyValue(name).trim() || fallback;
    return {
      line: read('--black', '#1A1A1A'),
      midline: read('--mid-gray-light', '#B8B4AB'),
      active: read('--blue', '#1A3A8F'),
      blunder: read('--red', '#D42828'),
      mistake: read('--yellow', '#F2C12E'),
    };
  }

  private _draw(): void {
    const canvas = this._canvas;
    const ctx = this._ctx;
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const w = rect.width;
    const h = rect.height;
    const moves = this._moves;

    ctx.clearRect(0, 0, w, h);

    if (moves.length === 0) return;

    const colors = this._palette();
    const step = w / Math.max(moves.length - 1, 1);
    const zeroY = h / 2;
    const yAt = (i: number): number => cpToY(evalFromWhite(moves[i] ?? { player: 'white', eval_after: 0 }), h);

    // White-advantage area (above the midline)
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    for (let i = 0; i < moves.length; i++) ctx.lineTo(i * step, Math.min(yAt(i), zeroY));
    ctx.lineTo((moves.length - 1) * step, zeroY);
    ctx.closePath();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.55)';
    ctx.fill();

    // Black-advantage area (below the midline)
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    for (let i = 0; i < moves.length; i++) ctx.lineTo(i * step, Math.max(yAt(i), zeroY));
    ctx.lineTo((moves.length - 1) * step, zeroY);
    ctx.closePath();
    ctx.fillStyle = 'rgba(26, 26, 26, 0.10)';
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(w, zeroY);
    ctx.strokeStyle = colors.midline;
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.beginPath();
    for (let i = 0; i < moves.length; i++) {
      const x = i * step;
      const y = yAt(i);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = colors.line;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.stroke();

    if (this._activePly >= 0 && this._activePly < moves.length) {
      const x = this._activePly * step;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.strokeStyle = colors.active;
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    const markerSize = 7;
    for (let i = 0; i < moves.length; i++) {
      const move = moves[i];
      if (!move) continue;
      const cls = move.classification;
      if (cls !== 'blunder' && cls !== 'mistake') continue;
      const x = i * step;
      const y = yAt(i);
      ctx.fillStyle = cls === 'blunder' ? colors.blunder : colors.mistake;
      ctx.fillRect(x - markerSize / 2, y - markerSize / 2, markerSize, markerSize);
      ctx.strokeStyle = colors.line;
      ctx.lineWidth = 1;
      ctx.strokeRect(x - markerSize / 2, y - markerSize / 2, markerSize, markerSize);
    }
  }
}
