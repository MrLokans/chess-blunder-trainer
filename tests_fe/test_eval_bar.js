import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { updateEvalBar } from '../blunder_tutor/web/static/js/trainer/eval-bar.js';

function makeMockEl() {
  return { style: { width: '' }, textContent: '', className: '' };
}

describe('updateEvalBar', () => {
  it('shows +0.0 at equal position', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(0, 'white', fill, value);
    assert.equal(value.textContent, '+0.0');
    assert.equal(fill.style.width, '50%');
    assert.equal(value.className, 'eval-value positive');
  });

  it('shows positive eval for white advantage as white', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(200, 'white', fill, value);
    assert.equal(value.textContent, '+2.0');
    assert(parseFloat(fill.style.width) > 50);
    assert.equal(value.className, 'eval-value positive');
  });

  it('flips perspective for black player', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(200, 'black', fill, value);
    // White is +2.0, but from black's perspective the bar should be < 50%
    assert(parseFloat(fill.style.width) < 50);
    assert.equal(value.className, 'eval-value negative');
  });

  it('clamps extreme values', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(9999, 'white', fill, value);
    assert.equal(fill.style.width, '100%');
  });

  it('displays mate symbol for very large values', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(10001, 'white', fill, value);
    assert.equal(value.textContent, '+M');
  });

  it('displays negative mate symbol', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(-10001, 'white', fill, value);
    assert.equal(value.textContent, '-M');
  });

  it('handles negative eval', () => {
    const fill = makeMockEl();
    const value = makeMockEl();
    updateEvalBar(-150, 'white', fill, value);
    assert.equal(value.textContent, '-1.5');
    assert(parseFloat(fill.style.width) < 50);
    assert.equal(value.className, 'eval-value negative');
  });
});
