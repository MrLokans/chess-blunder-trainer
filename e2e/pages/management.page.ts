import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class ManagementPage extends BasePage {
  readonly root: Locator;

  constructor(page: Page) {
    super(page);
    this.root = page.locator('#management-root');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/management');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.root).toBeVisible();
  }
}
