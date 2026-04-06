export interface FilterPersistenceOptions {
  storageKey: string;
  checkboxSelector: string;
  defaultValues?: string[];
}

export class FilterPersistence {
  private storageKey: string;
  private checkboxSelector: string;
  private defaultValues: string[];

  constructor({ storageKey, checkboxSelector, defaultValues = [] }: FilterPersistenceOptions) {
    this.storageKey = storageKey;
    this.checkboxSelector = checkboxSelector;
    this.defaultValues = defaultValues;
  }

  private _getCheckboxes(): NodeListOf<HTMLInputElement> {
    return document.querySelectorAll<HTMLInputElement>(this.checkboxSelector);
  }

  load(): string[] {
    const stored = localStorage.getItem(this.storageKey);
    let values: string[];

    if (stored) {
      try {
        const parsed: unknown = JSON.parse(stored);
        values = Array.isArray(parsed) ? parsed as string[] : this.defaultValues;
      } catch {
        console.warn(`Failed to parse stored filter "${this.storageKey}"`);
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

  save(): string[] {
    const values = this.getValues();
    localStorage.setItem(this.storageKey, JSON.stringify(values));
    return values;
  }

  getValues(): string[] {
    const values: string[] = [];
    this._getCheckboxes().forEach(checkbox => {
      if (checkbox.checked) values.push(checkbox.value);
    });
    return values;
  }

  reset(values: string[]): string[] {
    localStorage.setItem(this.storageKey, JSON.stringify(values));
    this._getCheckboxes().forEach(checkbox => {
      checkbox.checked = values.includes(checkbox.value);
    });
    return values;
  }
}
