import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class SettingsPage extends BasePage {
  readonly root: Locator;

  constructor(page: Page) {
    super(page);
    this.root = page.locator('#settings-root');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/settings');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.root).toBeVisible();
  }

  async changeLocale(locale: string): Promise<void> {
    const select = this.page.getByRole('combobox').first();
    await select.selectOption(locale);
  }
}
