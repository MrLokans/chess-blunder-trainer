import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class DashboardPage extends BasePage {
  readonly statsGrid: Locator;
  readonly statCards: Locator;

  constructor(page: Page) {
    super(page);
    this.statsGrid = page.locator('.stats-grid');
    this.statCards = page.locator('.stat-card');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/dashboard');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.statsGrid).toBeVisible();
  }

  async getStatCardCount(): Promise<number> {
    return await this.statCards.count();
  }

  async getStatValue(label: string): Promise<string> {
    const card = this.statCards.filter({ hasText: label });
    const value = card.locator('.stat-value');
    return (await value.textContent()) ?? '';
  }
}
