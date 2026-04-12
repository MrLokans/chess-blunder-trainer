import { type Page, type Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class SetupPage extends BasePage {
  readonly form: Locator;
  readonly lichessInput: Locator;
  readonly chesscomInput: Locator;
  readonly submitBtn: Locator;
  readonly progress: Locator;

  constructor(page: Page) {
    super(page);
    this.form = page.locator('#setupForm');
    this.lichessInput = page.locator('#lichess');
    this.chesscomInput = page.locator('#chesscom');
    this.submitBtn = page.locator('#submitBtn');
    this.progress = page.locator('#setupProgress');
  }

  async goto(): Promise<void> {
    await this.navigateTo('/setup');
  }

  async expectLoaded(): Promise<void> {
    await expect(this.form).toBeVisible();
  }

  async fillLichessUsername(username: string): Promise<void> {
    await this.lichessInput.fill(username);
  }

  async fillChesscomUsername(username: string): Promise<void> {
    await this.chesscomInput.fill(username);
  }

  async submit(): Promise<void> {
    await this.submitBtn.click();
  }
}
