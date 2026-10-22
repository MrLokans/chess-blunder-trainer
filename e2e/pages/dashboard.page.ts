import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class DashboardPage extends BasePage {
  readonly statsGrid: Locator;
  readonly kpis: Locator;
  readonly moreInsights: Locator;
  readonly management: Locator;

  constructor(page: Page) {
    super(page);
    this.statsGrid = page.locator('.stats-grid');
    this.kpis = page.locator('.dashboard-kpi');
    this.moreInsights = page.locator('.dashboard-more-insights');
    this.management = page.locator('.dashboard-management');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/dashboard');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.statsGrid).toBeVisible();
  }
}
