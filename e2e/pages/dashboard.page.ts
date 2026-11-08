import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class DashboardPage extends BasePage {
  readonly trendSpine: Locator;
  readonly libraryStatus: Locator;
  readonly sectionHeadings: Locator;

  constructor(page: Page) {
    super(page);
    this.trendSpine = page.locator('.trend-spine');
    this.libraryStatus = page.getByTestId('library-status');
    this.sectionHeadings = page.locator('.dashboard-section > h2');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/dashboard');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.trendSpine).toBeVisible();
  }
}
