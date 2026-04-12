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
}
