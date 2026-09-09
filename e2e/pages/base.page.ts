import { type Page, type Locator, expect } from '@playwright/test';

export abstract class BasePage {
  readonly nav: Locator;

  constructor(readonly page: Page) {
    this.nav = page.locator('#mainNav');
  }

  async navigateTo(path: string): Promise<void> {
    await this.page.goto(path);
    await this.page.waitForLoadState('networkidle');
  }

  async clickNavLink(name: string): Promise<void> {
    await expect(this.nav).toBeVisible();
    const link = this.nav.getByRole('link', { name });
    await expect(link).toBeVisible();
    await link.click();
    await this.page.waitForLoadState('networkidle');
  }

  async expectNavVisible(): Promise<void> {
    await expect(this.nav).toBeVisible();
  }

  abstract expectLoaded(): Promise<void>;
}
