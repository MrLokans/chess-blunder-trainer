import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class GameReviewPage extends BasePage {
  readonly root: Locator;

  constructor(page: Page) {
    super(page);
    this.root = page.locator('#game-review-root');
  }

  async goto(gameId: string): Promise<void> {
    await this.navigateTo(`/game/${gameId}`);
  }

  async expectLoaded(): Promise<void> {
    await expect(this.root).toBeVisible();
  }

  async enableAnalysis(): Promise<void> {
    // The analysis control is a <Toggle> (role="switch"), not a checkbox, so check()
    // doesn't apply — click it only if it isn't already on.
    const toggle = this.page.getByRole('switch', { name: /engine analysis/i });
    if ((await toggle.getAttribute('aria-checked')) !== 'true') {
      await toggle.click();
    }
  }
}
