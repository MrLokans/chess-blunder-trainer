const MAX_CP = 500;

function clampEval(cp) {
  return Math.max(-MAX_CP, Math.min(MAX_CP, cp));
}

export function evalFromWhite(move) {
  return move.player === 'black' ? -move.eval_after : move.eval_after;
}

function cpToY(cp, height) {
  const clamped = clampEval(cp);
  return height / 2 - (clamped / MAX_CP) * (height / 2);
}

export class EvalChart {
  constructor(canvasEl) {
    this._canvas = canvasEl;
    this._ctx = canvasEl.getContext('2d');
    this._moves = [];
    this._activePly = -1;
    this._onClick = null;

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

  render(moves) {
    this._moves = moves;
    this._draw();
  }

  setActivePly(index) {
    this._activePly = index;
    this._draw();
  }

  onClick(callback) {
    this._onClick = callback;
  }

  _draw() {
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

    const step = w / Math.max(moves.length - 1, 1);
    const zeroY = h / 2;

    // Fill regions above/below zero
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    for (let i = 0; i < moves.length; i++) {
      const x = i * step;
      const y = cpToY(evalFromWhite(moves[i]), h);
      ctx.lineTo(x, Math.min(y, zeroY));
    }
    ctx.lineTo((moves.length - 1) * step, zeroY);
    ctx.closePath();
    ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    for (let i = 0; i < moves.length; i++) {
      const x = i * step;
      const y = cpToY(evalFromWhite(moves[i]), h);
      ctx.lineTo(x, Math.max(y, zeroY));
    }
    ctx.lineTo((moves.length - 1) * step, zeroY);
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    ctx.fill();

    // Zero line
    ctx.beginPath();
    ctx.moveTo(0, zeroY);
    ctx.lineTo(w, zeroY);
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.2)';
    ctx.lineWidth = 1;
    ctx.stroke();

    // Eval line
    ctx.beginPath();
    for (let i = 0; i < moves.length; i++) {
      const x = i * step;
      const y = cpToY(evalFromWhite(moves[i]), h);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.6)';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Blunder/mistake dots
    for (let i = 0; i < moves.length; i++) {
      const cls = moves[i].classification;
      if (cls !== 'blunder' && cls !== 'mistake') continue;
      const x = i * step;
      const y = cpToY(evalFromWhite(moves[i]), h);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fillStyle = cls === 'blunder' ? '#D32F2F' : '#F57C00';
      ctx.fill();
    }

    // Active ply indicator
    if (this._activePly >= 0 && this._activePly < moves.length) {
      const x = this._activePly * step;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.strokeStyle = 'rgba(33, 150, 243, 0.7)';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }
}
