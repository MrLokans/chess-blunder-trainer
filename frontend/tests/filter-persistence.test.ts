import { describe, it, expect, beforeEach } from 'vitest';
import { FilterPersistence } from '../src/shared/filter-persistence';

interface MockCheckbox {
  value: string;
  checked: boolean;
}

function makeCheckboxes(values: string[], checkedValues: string[] = []): MockCheckbox[] {
  const checkboxes: MockCheckbox[] = values.map(v => ({
    value: v,
    checked: checkedValues.includes(v),
  }));
  document.querySelectorAll = ((selector: string) => {
    if (selector === '.test-filter') return checkboxes;
    return [];
  }) as unknown as typeof document.querySelectorAll;
  return checkboxes;
}

describe('FilterPersistence', () => {
  beforeEach(() => {
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
    expect(vals).toEqual(['a', 'c']);
  });

  it('loads stored values from localStorage', () => {
    const checkboxes = makeCheckboxes(['a', 'b', 'c']);
    localStorage.setItem('test', JSON.stringify(['b']));
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    fp.load();
    expect(checkboxes[0]!.checked).toBe(false);
    expect(checkboxes[1]!.checked).toBe(true);
    expect(checkboxes[2]!.checked).toBe(false);
  });

  it('saves checked values to localStorage', () => {
    makeCheckboxes(['a', 'b', 'c'], ['a', 'c']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    const vals = fp.save();
    expect(vals).toEqual(['a', 'c']);
    expect(JSON.parse(localStorage.getItem('test')!)).toEqual(['a', 'c']);
  });

  it('getValues returns currently checked values', () => {
    makeCheckboxes(['x', 'y', 'z'], ['y']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    expect(fp.getValues()).toEqual(['y']);
  });

  it('reset sets specific values', () => {
    const checkboxes = makeCheckboxes(['a', 'b', 'c']);
    const fp = new FilterPersistence({
      storageKey: 'test',
      checkboxSelector: '.test-filter',
    });
    fp.reset(['b', 'c']);
    expect(checkboxes[0]!.checked).toBe(false);
    expect(checkboxes[1]!.checked).toBe(true);
    expect(checkboxes[2]!.checked).toBe(true);
    expect(JSON.parse(localStorage.getItem('test')!)).toEqual(['b', 'c']);
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
    expect(vals).toEqual(['a']);
  });
});
