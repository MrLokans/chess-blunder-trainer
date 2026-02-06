export class FilterPersistence {
  constructor({ storageKey, checkboxSelector, defaultValues = [] }) {
    this.storageKey = storageKey;
    this.checkboxSelector = checkboxSelector;
    this.defaultValues = defaultValues;
  }

  _getCheckboxes() {
    return document.querySelectorAll(this.checkboxSelector);
  }

  load() {
    const stored = localStorage.getItem(this.storageKey);
    let values;

    if (stored) {
      try {
        const parsed = JSON.parse(stored);
        values = Array.isArray(parsed) ? parsed : this.defaultValues;
      } catch (e) {
        console.warn(`Failed to parse stored filter "${this.storageKey}":`, e);
        values = this.defaultValues;
      }
    } else {
      values = this.defaultValues;
    }

    this._getCheckboxes().forEach(checkbox => {
      checkbox.checked = values.includes(checkbox.value);
    });

    return values;
  }

  save() {
    const values = this.getValues();
    localStorage.setItem(this.storageKey, JSON.stringify(values));
    return values;
  }

  getValues() {
    const values = [];
    this._getCheckboxes().forEach(checkbox => {
      if (checkbox.checked) values.push(checkbox.value);
    });
    return values;
  }

  reset(values) {
    localStorage.setItem(this.storageKey, JSON.stringify(values));
    this._getCheckboxes().forEach(checkbox => {
      checkbox.checked = values.includes(checkbox.value);
    });
    return values;
  }
}
