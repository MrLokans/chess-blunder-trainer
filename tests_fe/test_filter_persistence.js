import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupGlobalDOM, resetDOM } from './helpers/dom.js';

setupGlobalDOM();

function makeCheckboxes(values, checkedValues = []) {
  const checkboxes = values.map(v => ({
    value: v,
    checked: checkedValues.includes(v),
  }));
  globalThis.document.querySelectorAll = (selector) => {
    if (selector === '.test-filter') return checkboxes;
    return [];
  };
  return checkboxes;
}

const { FilterPersistence } = await import('../blunder_tutor/web/static/js/filter-persistence.js');

describe('FilterPersistence', () => {
  beforeEach(() => {
    resetDOM();
    localStorage.clear();
  });

  it('loads default values when nothing stored', () => {
    makeCheckboxes(['a', 'b', 'c']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
      defaultValues: ['a', 'c'],
    });
    const vals = fp.load();
    assert.deepEqual(vals, ['a', 'c']);
  });

  it('loads stored values from localStorage', () => {
    const checkboxes = makeCheckboxes(['a', 'b', 'c']);
    localStorage.setItem('test', JSON.stringify(['b']));
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    fp.load();
    assert.equal(checkboxes[0].checked, false);
    assert.equal(checkboxes[1].checked, true);
    assert.equal(checkboxes[2].checked, false);
  });

  it('saves checked values to localStorage', () => {
    makeCheckboxes(['a', 'b', 'c'], ['a', 'c']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    const vals = fp.save();
    assert.deepEqual(vals, ['a', 'c']);
    assert.deepEqual(JSON.parse(localStorage.getItem('test')), ['a', 'c']);
  });

  it('getValues returns currently checked values', () => {
    makeCheckboxes(['x', 'y', 'z'], ['y']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    assert.deepEqual(fp.getValues(), ['y']);
  });

  it('reset sets specific values', () => {
    const checkboxes = makeCheckboxes(['a', 'b', 'c']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    fp.reset(['b', 'c']);
    assert.equal(checkboxes[0].checked, false);
    assert.equal(checkboxes[1].checked, true);
    assert.equal(checkboxes[2].checked, true);
    assert.deepEqual(JSON.parse(localStorage.getItem('test')), ['b', 'c']);
  });

  it('handles corrupt localStorage gracefully', () => {
    makeCheckboxes(['a', 'b']);
    localStorage.setItem('test', 'not-json{{{');
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
      defaultValues: ['a'],
    });
    const vals = fp.load();
    assert.deepEqual(vals, ['a']);
  });
});
