import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class DashboardPage extends BasePage {
  readonly trendSpine: Locator;
  readonly libraryStatus: Locator;
  readonly moreInsights: Locator;
  readonly management: Locator;

  constructor(page: Page) {
    super(page);
    this.trendSpine = page.locator('.trend-spine');
    this.libraryStatus = page.getByTestId('library-status');
    this.moreInsights = page.locator('.dashboard-more-insights');
    this.management = page.locator('.dashboard-management');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/dashboard');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.trendSpine).toBeVisible();
  }
}
